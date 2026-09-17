"""
hamigenz — LLM Service via Ollama + Grounding Validator
"""
import os
import re
import json
import requests
from typing import Optional

from document_processor import DocumentProcessor


class OllamaService:
    """Interface to local Ollama LLM."""

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "qwen3:8b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._verify()

    def _verify(self):
        """Check Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            if self.model not in model_names:
                print(f"[OllamaService] Warning: model '{self.model}' not found. "
                      f"Available: {model_names}")
        except Exception as e:
            print(f"[OllamaService] Cannot reach Ollama at {self.base_url}: {e}")

    def generate(self, prompt: str, stream: bool = False,
                 options: dict | None = None, timeout: int = 120) -> str:
        """
        Generate a response from the LLM.
        Returns full response text.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }

        if stream:
            chunks = []
            with requests.post(f"{self.base_url}/api/generate",
                               json=payload, stream=True, timeout=120) as resp:
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            chunks.append(data["response"])
                        if data.get("done"):
                            break
            return "".join(chunks)
        else:
            resp = requests.post(f"{self.base_url}/api/generate",
                                 json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("response", "")

    def generate_structured(self, prompt: str) -> dict:
        """
        Generate a structured JSON response.
        Wraps prompt to request JSON output.
        """
        wrapper = f"""{prompt}

Respond ONLY with valid JSON. No other text, no markdown fences, no explanation.
The JSON must parse with json.loads().
"""
        raw = self.generate(wrapper)
        # Try to extract JSON from response
        return self._parse_json_response(raw)

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Extract JSON object from LLM response text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try to find JSON in markdown fence
        match = re.search(r'```(?:json)?\s*\{[\s\S]*?\}\s*```', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return {"error": "Could not parse JSON response", "raw": text[:500]}


class GroundingValidator:
    """
    Validate generated answers against retrieved evidence.
    Classifies claims as Supported / Partially Supported / Contradicted / Insufficient Evidence.
    """

    def __init__(self, llm: OllamaService):
        self.llm = llm

    def validate(self, question: str, answer: str,
                 evidence_chunks: list[dict]) -> dict:
        """
        Validate an answer against evidence.
        Returns grounding report.
        """
        evidence_text = self._format_evidence(evidence_chunks)

        prompt = f"""You are a grounding validator. Your job is to check whether an AI-generated answer
is supported by the provided evidence.

QUESTION: {question}

GENERATED ANSWER: {answer}

RETRIEVED EVIDENCE (with page numbers):
{evidence_text}

INSTRUCTIONS:
1. Extract the key factual claims from the GENERATED ANSWER.
2. For each claim, determine if it is:
   - SUPPORTED: directly confirmed by the evidence
   - PARTIALLY_SUPPORTED: somewhat supported but missing detail or slightly imprecise
   - CONTRADICTED: conflicts with the evidence
   - INSUFFICIENT_EVIDENCE: cannot be verified from the evidence provided

3. Pay special attention to claims about: fees, deadlines, penalties, legal requirements,
   eligibility, required documents, government procedures, dates, amounts.

4. Output your analysis as JSON with this structure:
{{
  "claims": [
    {{
      "claim": "the claim text",
      "classification": "SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | INSUFFICIENT_EVIDENCE",
      "evidence": "which evidence supports or contradicts this",
      "page_refs": [page numbers referenced]
    }}
  ],
  "overall_confidence": "HIGH | MEDIUM | LOW",
  "missing_evidence": ["list of claims that could not be verified"],
  "warning": "any warning about unsupported factual claims, or empty string"
}}

If the evidence is insufficient to verify important claims, set overall_confidence to LOW
and include a clear warning.
"""

        result = self.llm.generate_structured(prompt)
        return result

    @staticmethod
    def _format_evidence(chunks: list[dict]) -> str:
        """Format evidence chunks for the validator prompt."""
        if not chunks:
            return "NO EVIDENCE RETRIEVED."

        lines = []
        for i, chunk in enumerate(chunks):
            page = chunk.get("page_num", "?")
            text = chunk.get("text", "")[:800]  # limit length
            lines.append(f"[Page {page}] {text}")
        return "\n\n".join(lines)


class VerificationLayer:
    """
    Standalone verification layer for hamiGenZ answers.

    Runs claim extraction + contradiction check + confidence scoring.
    Can be called independently of the explanation pipeline,
    and is wired into /ask and /explain so every answer carries
    a verification report.

    STEP 3 deliverable: stronger verification than raw grounding —
    contradiction detection with re-prompt guidance, numeric confidence
    score, and an explicit recommendation for the frontend.
    """

    # Classification → numeric weight (higher = more trustworthy)
    _WEIGHTS = {
        "SUPPORTED": 1.0,
        "PARTIALLY_SUPPORTED": 0.55,
        "INSUFFICIENT_EVIDENCE": 0.15,
        "CONTRADICTED": 0.0,
    }

    def __init__(self, llm: OllamaService, validator: GroundingValidator | None = None):
        self.llm = llm
        self.validator = validator or GroundingValidator(llm)

    def verify(self, question: str, answer: str,
               evidence_chunks: list[dict]) -> dict:
        """
        Run full verification on an answer.

        Returns a dict with:
          - grounding_report: raw claim-level classification (from GroundingValidator)
          - contradiction_found: bool — any claim marked CONTRADICTED
          - contradiction_claims: list of contradicted claim texts
          - confidence_score: 0–100 numeric score derived from claim weights
          - confidence_band: "HIGH" / "MEDIUM" / "LOW" / "UNKNOWN"
          - unsupported_facts: list of claim texts that are PARTIALLY_SUPPORTED
                                 or INSUFFICIENT_EVIDENCE or CONTRADICTED
          - recommendation: short guidance for the frontend / user
        """
        report = self.validator.validate(question, answer, evidence_chunks)

        claims = report.get("claims", [])
        contradicted = [c for c in claims if c.get("classification") == "CONTRADICTED"]
        unsupported = [
            c for c in claims
            if c.get("classification") in ("PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED")
        ]

        # Numeric confidence: weighted average of claim weights, scaled to 0–100.
        # If there are no claims (empty answer / no evidence), fall back to the
        # qualitative band from the validator.
        if claims:
            total_weight = sum(self._WEIGHTS.get(c.get("classification"), 0.0) for c in claims)
            confidence_score = round((total_weight / len(claims)) * 100)
        else:
            confidence_score = None

        band = report.get("overall_confidence", "UNKNOWN")
        if confidence_score is not None:
            if confidence_score >= 75:
                band = "HIGH"
            elif confidence_score >= 45:
                band = "MEDIUM"
            else:
                band = "LOW"

        # Contradiction handling: if any claim is directly contradicted by evidence,
        # the answer should not be presented as fully reliable.
        contradiction_found = len(contradicted) > 0
        if contradiction_found:
            recommendation = (
                "Some claims in this answer conflict with the document evidence. "
                "Treat the answer with caution and check the original source."
            )
        elif band == "LOW":
            recommendation = (
                "This answer could not be fully verified from the document. "
                "Important details may be missing or imprecise — check the original source."
            )
        elif band == "MEDIUM":
            recommendation = (
                "This answer is partially supported by the document. "
                "Some details may need verification."
            )
        else:
            recommendation = (
                "This answer is supported by the document evidence."
            )

        return {
            "grounding_report": report,
            "contradiction_found": contradiction_found,
            "contradiction_claims": [c["claim"] for c in contradicted],
            "confidence_score": confidence_score,
            "confidence_band": band,
            "unsupported_facts": [c["claim"] for c in unsupported],
            "recommendation": recommendation,
        }

    def re_prompt_on_contradiction(self, question: str, answer: str,
                                   evidence_chunks: list[dict],
                                   verification: dict) -> str | None:
        """
        If the verification found contradictions, re-generate the answer
        with an explicit instruction to remove or correct contradicted claims.

        Returns a revised answer string, or None if no correction was attempted
        (e.g. no contradiction, or correction failed).
        """
        if not verification.get("contradiction_found"):
            return None

        evidence_text = self._format_evidence(evidence_chunks)
        contradicted_claims = verification.get("contradiction_claims", [])
        claims_json = json.dumps(contradicted_claims, ensure_ascii=False)

        correction_prompt = f"""You are hamiGenZ. You previously generated this answer:

PREVIOUS ANSWER:
{answer}

However, verification against the document evidence found that the following claims
conflict with the evidence and must be REMOVED or CORRECTED:

CONTRADICTED CLAIMS:
{claims_json}

RETRIEVED EVIDENCE (with page numbers):
{evidence_text}

QUESTION: {question}

INSTRUCTIONS:
1. Rewrite the answer so that NONE of the contradicted claims appear.
2. Where the evidence supports a different fact, use the evidence instead.
3. Where the evidence does not support the claim at all, remove the claim and say
   that the document does not contain that information.
4. Do NOT invent new facts to replace the removed claims.
5. Keep the rest of the answer that IS supported.
6. Respond in the same language as the previous answer.
7. Preserve page citations where they are supported by evidence.

Write the corrected answer directly.
"""
        try:
            revised = self.llm.generate(correction_prompt, timeout=120)
            return revised
        except Exception:
            return None

    @staticmethod
    def _format_evidence(chunks: list[dict]) -> str:
        if not chunks:
            return "NO EVIDENCE RETRIEVED."
        lines = []
        for chunk in chunks:
            page = chunk.get("page_num", "?")
            text = chunk.get("text", "")[:800]
            lines.append(f"[Page {page}] {text}")
        return "\n\n".join(lines)


class ExplanationEngine:
    """
    Structure answers to be user-friendly and actionable.
    """

    def __init__(self, llm: OllamaService):
        self.llm = llm

    def format_answer(self, question: str, raw_answer: str,
                      evidence_chunks: list[dict],
                      grounding_report: dict | None = None,
                      lang: str = "nepali",
                      explanation_level: str = "simple") -> dict:
        """
        Format a final user-facing answer.
        Returns structured response with sections.
        explanation_level: "original" | "simple" | "very_simple"
        """
        evidence_text = self._format_evidence(evidence_chunks)
        grounding_note = ""
        if grounding_report:
            confidence = grounding_report.get("overall_confidence", "UNKNOWN")
            warning = grounding_report.get("warning", "")
            if warning:
                grounding_note = f"⚠️ {warning}"
            elif confidence == "LOW":
                grounding_note = "⚠️ I could not fully verify this from the document. Please check the original source."
            elif confidence == "MEDIUM":
                grounding_note = "ℹ️ This answer is partially based on the document; some details may need verification."

        level_guidance = {
            "original": """
The user wants to understand the ORIGINAL meaning of the text/document.
- Preserve the original wording where it matters.
- Explain what the formal/technical language actually means without changing the facts.
- Do NOT simplify into everyday language unless explaining a specific term.
- Keep the register close to the original -- the user wants to understand the original, not get a casual rewrite.
- If the text is in legal/official language, explain what each important part means in clear terms, still faithful to the original.
- Distinguish: (a) literal meaning, (b) what it implies, (c) what the person needs to know.
""",
            "simple": """
The user wants a SIMPLE, everyday-language explanation that preserves the exact meaning.
- Rewrite the idea in clear, natural, everyday Nepali (or English, depending on lang).
- Preserve the exact meaning and intent -- do not change facts, requirements, deadlines, fees, or eligibility.
- Explain technical, legal, or official terms in plain language.
- Use normal sentence length. Avoid unnecessarily fancy words.
- The goal is: someone who can read but does not fully understand the original should come away understanding it.
- Do NOT treat this as a word-for-word translation. Focus on meaning.
""",
            "very_simple": """
The user wants a VERY SIMPLE explanation -- the easiest possible understanding without losing the facts.
- Use short, clear sentences.
- Use the simplest everyday words that still preserve the exact meaning.
- Explain every important term inline, in one short clause.
- If a concept is complicated, break it into the smallest clear steps.
- Keep all facts, requirements, deadlines, fees, eligibility, and action items accurate -- simplify the language, not the facts.
- This is for someone who struggles with formal or technical language.
- Do NOT invent or omit anything important.
""",
        }.get(explanation_level, ""
            "The user wants a SIMPLE, everyday-language explanation that preserves the exact meaning."
            "Rewrite the idea in clear, natural, everyday language."
            "Preserve the exact meaning and intent -- do not change facts."
            "Explain technical or official terms in plain language.")

        prompt = f"""You are hamiGenZ, a helpful assistant that explains documents and official information
in simple, clear language for ordinary people in Nepal.

EXPLANATION LEVEL: {explanation_level}
(level_guidance below tells you exactly how to handle this level)

QUESTION (may be in Nepali, English, or Romanized Nepali): {question}

DOCUMENT CONTENT (relevant excerpts with page numbers):
{evidence_text}

RAW ANSWER FROM AI: {raw_answer}

GROUNDING NOTE: {grounding_note}

LEVEL GUIDANCE:
{level_guidance}

INSTRUCTIONS:
1. Write a clear, helpful answer in {lang}.
2. Structure it around:
   - What is this? (brief summary of what the document/information is about)
   - What does it mean? (explain in simple terms)
   - What do I need to do? (action items, if any)
   - Important dates / fees / requirements (if extractable)
   - Who does this apply to? (if relevant)
   - Source/citation (page numbers or document reference)
3. Follow the EXPLANATION LEVEL guidance above exactly.
4. If the document is a form, and the question is about how to fill it,
   explain what goes in each field. Mark any example as "SAMPLE — FOR EXPLANATION ONLY — NOT FOR SUBMISSION".
5. If you do not have enough information to answer, say so clearly.
6. Include page citations where relevant, like (Page 3).
7. Do NOT invent fees, deadlines, penalties, or legal requirements. If not in evidence, say you could not verify.
8. Preserve the ORIGINAL MEANING at every level. Simplification changes the language, not the facts.

OUTPUT: Write the answer directly. Do not include any preamble.
"""
        answer = self.llm.generate(prompt)

        return {
            "question": question,
            "answer": answer,
            "citations": self._extract_citations(answer, evidence_chunks),
            "grounding": grounding_report,
            "grounding_note": grounding_note,
            "language": lang,
            "explanation_level": explanation_level,
            "evidence_pages": list(set(
                c.get("page_num") for c in evidence_chunks if c.get("page_num")
            )),
        }

    @staticmethod
    def _format_evidence(chunks: list[dict]) -> str:
        if not chunks:
            return "NO EVIDENCE RETRIEVED."
        lines = []
        for chunk in chunks:
            page = chunk.get("page_num", "?")
            text = chunk.get("text", "")[:600]
            lines.append(f"[Page {page}] {text}")
        return "\n\n".join(lines)

    @staticmethod
    def _extract_citations(answer: str, chunks: list[dict]) -> list[dict]:
        """Extract page references mentioned in the answer."""
        citations = []
        pages_mentioned = set()
        for chunk in chunks:
            page = chunk.get("page_num")
            if page and str(page) in answer:
                pages_mentioned.add(page)

        for page in sorted(pages_mentioned):
            # Find the chunk text for this page
            chunk_texts = [c["text"] for c in chunks if c.get("page_num") == page]
            citations.append({
                "page": page,
                "excerpt": chunk_texts[0][:200] if chunk_texts else "",
            })

        return citations


class LanguageDetector:
    """Simple language detection for Nepali / English / Romanized Nepali."""

    NEPALI_SCRIPT_RANGE = ('\u0900', '\u097F')

    @staticmethod
    def detect(text: str) -> str:
        """
        Detect language/script of input text.
        Returns: 'nepali', 'romanized_nepali', 'english', 'mixed'
        """
        if not text or not text.strip():
            return "unknown"

        has_nepali_script = any(
            LanguageDetector.NEPALI_SCRIPT_RANGE[0] <= c <= LanguageDetector.NEPALI_SCRIPT_RANGE[1]
            for c in text
        )

        # Romanized Nepali patterns
        romanized_patterns = [
            r'\b(k|k|ko|ko\s|ma|le|nu|parchu|chainxa|chainxa\s|ho|hunxa|huncha|garnu|garna '
            r'banauna|banaune|haina|hoina|ke|kahile|kasulai|kehi|yesko|yo|tyo|aru|nasitha|'
            r'bhako|bhako cha|cha|chha|huncha|huna|hos|hos)\b',
        ]

        has_romanized = any(re.search(p, text.lower()) for p in romanized_patterns)

        # Check if it's mostly Latin script with Nepali words
        latin_ratio = sum(1 for c in text if c.isascii() and c.isalpha()) / max(len(text), 1)

        if has_nepali_script:
            return "nepali"

        if has_romanized and latin_ratio > 0.7:
            return "romanized_nepali"

        # Mixed: both scripts or mixed words
        if has_romanized and not has_nepali_script:
            return "romanized_nepali"

        # Default: try English
        return "english"

    @staticmethod
    def normalize_query(text: str, detected_lang: str) -> str:
        """
        Normalize query for the LLM.
        Romanize if needed, keep Nepali script as-is.
        """
        if detected_lang == "nepali":
            # Already in Nepali script — keep as is
            return text

        if detected_lang == "romanized_nepali":
            # Keep Romanized form — the LLM should understand it
            return text

        return text  # English or mixed
