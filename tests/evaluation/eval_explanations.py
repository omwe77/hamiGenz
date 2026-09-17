"""
hamigenz — Explanation quality evaluator (PR-014).

Answers the core product question for each gold example:
  "Did hamiGenZ make the information easier to understand
   without changing its meaning?"

Scoring is deterministic first (key-fact presence / forbidden-fact
absence via the gold dataset's own checker, plus script and level
signals), with an optional live LLM run as a secondary signal —
never the only signal.

Run:
    .venv/Scripts/python.exe -m tests.evaluation.eval_explanations [--live]
"""
import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from tests.evaluation.gold_dataset import GOLD_CASES, check_case_facts

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")


def detect_script(answer: str) -> str:
    dev = len(DEVANAGARI.findall(answer))
    lat = len(LATIN.findall(answer))
    if dev and lat:
        return "mixed"
    if dev:
        return "devanagari"
    if lat:
        return "latin"
    return "none"


def check_level(answer: str, level: str) -> dict:
    """Heuristic level-appropriateness: simpler levels → shorter sentences."""
    sentences = [s for s in re.split(r"[।!?\.]+", answer) if s.strip()]
    avg_sent_words = len(answer.split()) / max(len(sentences), 1)
    if level == "original":
        return {"avg_sentence_words": round(avg_sent_words, 1),
                "level_plausible": True}
    simple_max = 22 if level == "simple" else 14
    return {
        "avg_sentence_words": round(avg_sent_words, 1),
        "level_plausible": avg_sent_words <= simple_max,
    }


def evaluate_case(case, answer: str, model_label: str) -> dict:
    fact_result = check_case_facts(answer, case)
    script = detect_script(answer)
    level_info = check_level(answer, case.level)

    # Script appropriateness: Nepali-expected cases should produce
    # Devanagari output (romanized input may answer either way).
    if case.expected_lang == "nepali":
        script_ok = script in ("devanagari", "mixed")
    else:
        script_ok = True

    return {
        "case_id": case.case_id,
        "category": case.category,
        "level": case.level,
        "expected_lang": case.expected_lang,
        "model": model_label,
        "missing_facts": fact_result["missing_facts"],
        "forbidden_found": fact_result["forbidden_found"],
        "all_facts_present": not fact_result["missing_facts"],
        "no_forbidden": not fact_result["forbidden_found"],
        "passed": fact_result["passed"] and script_ok,
        "answer_script": script,
        "script_appropriate": script_ok,
        **level_info,
    }


def run_evaluator(llm=None, live: bool = False) -> dict:
    """
    Run explanation evaluation. Without an LLM (default) uses a
    deterministic echo mock — used by CI self-consistency tests.
    With --live, uses the real OllamaService.
    """
    if live:
        from llm_service import OllamaService
        llm = OllamaService()
        label = "qwen3:8b"
    else:
        llm = _MockLLM()
        label = "mock"

    results = []
    for case in GOLD_CASES:
        answer = llm.generate(_build_prompt(case))
        results.append(evaluate_case(case, answer, label))

    n = max(len(results), 1)
    summary = {
        "model": label,
        "n": len(results),
        "all_facts_rate": round(
            sum(1 for r in results if r["all_facts_present"]) / n, 3),
        "no_forbidden_rate": round(
            sum(1 for r in results if r["no_forbidden"]) / n, 3),
        "script_appropriate_rate": round(
            sum(1 for r in results if r["script_appropriate"]) / n, 3),
        "pass_rate": round(sum(1 for r in results if r["passed"]) / n, 3),
    }
    return {"summary": summary, "detail": results}


def _build_prompt(case) -> str:
    level_map = {
        "original": "Quote the original meaning faithfully.",
        "simple": "Explain in simple language. Keep all facts.",
        "very_simple": "Explain in very simple, short sentences. Keep all facts.",
    }
    return (
        f"{level_map[case.level]}\n\nTEXT:\n{case.input_text}\n\n"
        f"Answer language: {case.expected_lang}."
    )


class _MockLLM:
    """Deterministic mock: echoes the input — perfect fact preservation."""

    def generate(self, prompt: str) -> str:
        m = re.search(r"TEXT:\n(.+?)\n\nAnswer language:", prompt, re.S)
        return m.group(1).strip() if m else prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="run against the real Ollama qwen3:8b")
    parser.add_argument("--out", default=None,
                        help="write full JSON results to this file")
    args = parser.parse_args()
    res = run_evaluator(live=args.live)
    print(json.dumps(res["summary"], indent=2, ensure_ascii=False))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
