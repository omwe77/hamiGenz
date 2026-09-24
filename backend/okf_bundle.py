"""
hamigenz — Open Knowledge Format (OKF) bundle loader and router.

OKF is a vendor-neutral spec (Google Cloud, June 2026) for curating
organizational knowledge as markdown files with YAML frontmatter.

An OKF bundle is a directory tree of concept files:
  - One concept per .md file
  - YAML frontmatter (only required field: `type`)
  - Markdown body with explicit links between concepts
  - Lives in git, diffable, human + AI readable

For hamiGenZ, OKF replaces the chunking-based RAG approach for curated
knowledge (document type definitions, field meanings, form guidelines).
User-uploaded document search still uses VectorStore directly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ─── Concept dataclass ───────────────────────────────────────────────────────────

@dataclass
class OKFConcept:
    """One OKF concept — a single markdown file with frontmatter + body."""

    concept_id: str   # e.g. "document-types/passport"
    type: str         # required frontmatter field
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    status: Optional[str] = None          # current | deprecated | draft
    stale_after: Optional[str] = None     # ISO date or "2026-12-31"
    verified: bool = False
    verified_date: Optional[str] = None
    owner: Optional[str] = None
    body: str = ""                         # markdown body (strip frontmatter)
    links: list[str] = field(default_factory=list)  # outgoing [[concept_id]] links

    @property
    def file_path(self) -> str:
        return self.concept_id + ".md"

    def summary(self) -> dict:
        """Public view — safe to expose via API."""
        return {
            "concept_id": self.concept_id,
            "type": self.type,
            "title": self.title or "",
            "description": self.description or "",
            "tags": self.tags,
            "status": self.status or "current",
            "verified": self.verified,
            "resource": self.resource or "",
            "owner": self.owner or "",
        }


# ─── Bundle loader ───────────────────────────────────────────────────────────────

_MIN_TYPE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")  # [[concept-id]] cross-links


class OKFBundle:
    """Loads and indexes an OKF bundle (directory of markdown concept files)."""

    def __init__(self, bundle_dir: str | Path):
        self.bundle_dir = Path(bundle_dir)
        self.concepts: dict[str, OKFConcept] = {}  # concept_id -> concept
        self._by_type: dict[str, list[str]] = {}   # type -> [concept_ids]
        self._by_tag: dict[str, list[str]] = {}    # tag -> [concept_ids]
        self._loaded = False

    def load(self) -> int:
        """Load all .md files from the bundle directory. Returns count."""
        if self._loaded:
            return len(self.concepts)
        self.concepts.clear()
        self._by_type.clear()
        self._by_tag.clear()

        if not self.bundle_dir.is_dir():
            return 0

        for md_path in sorted(self.bundle_dir.rglob("*.md")):
            rel = md_path.relative_to(self.bundle_dir)
            # concept_id = relative path without .md extension
            # Normalize to forward slashes for cross-platform consistency
            concept_id = str(rel.with_suffix("")).replace(os.sep, "/")
            # skip index.md — it's the bundle index, not a concept
            if concept_id == "index":
                continue
            concept = self._parse_file(md_path, concept_id)
            if concept:
                self.concepts[concept_id] = concept
                # index by type
                t = concept.type
                self._by_type.setdefault(t, []).append(concept_id)
                # index by tags
                for tag in concept.tags:
                    self._by_tag.setdefault(tag, []).append(concept_id)

        self._loaded = True
        return len(self.concepts)

    def _parse_file(self, path: Path, concept_id: str) -> Optional[OKFConcept]:
        """Parse a single markdown file into an OKFConcept."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        frontmatter, body = self._split_frontmatter(raw)
        if frontmatter is None:
            return None

        # Parse YAML frontmatter
        try:
            meta = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            return None

        # `type` is the only required field
        concept_type = meta.get("type", "")
        if not concept_type or not isinstance(concept_type, str):
            return None
        concept_type = str(concept_type).strip()
        if not _MIN_TYPE_RE.match(concept_type):
            return None

        concept = OKFConcept(
            concept_id=concept_id,
            type=concept_type,
            title=str(meta.get("title", "")) if meta.get("title") else None,
            description=str(meta.get("description", "")) if meta.get("description") else None,
            resource=str(meta.get("resource", "")) if meta.get("resource") else None,
            tags=[str(t) for t in (meta.get("tags") or [])],
            status=str(meta.get("status", "")) if meta.get("status") else None,
            stale_after=str(meta.get("stale_after", "")) if meta.get("stale_after") else None,
            verified=bool(meta.get("verified", False)),
            verified_date=str(meta.get("verified_date", "")) if meta.get("verified_date") else None,
            owner=str(meta.get("owner", "")) if meta.get("owner") else None,
            body=body.strip(),
        )

        # Extract [[concept-id]] cross-links from body
        concept.links = list(set(_LINK_RE.findall(body)))

        return concept

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[Optional[str], str]:
        """Split markdown into (yaml_frontmatter, body).

        Returns (None, raw) if no frontmatter found.
        """
        if not raw.startswith("---"):
            return None, raw
        # Find the closing ---
        rest = raw[3:]  # skip opening ---
        idx = rest.find("\n---")
        if idx == -1:
            return None, raw
        fm = rest[:idx]
        body = rest[idx + 4:]  # skip \n---
        return fm, body

    # ─── Query helpers ───────────────────────────────────────────────────────────

    def get(self, concept_id: str) -> Optional[OKFConcept]:
        """Look up a concept by ID."""
        return self.concepts.get(concept_id)

    def by_type(self, type_name: str) -> list[OKFConcept]:
        """Return all concepts of a given type."""
        ids = self._by_type.get(type_name, [])
        return [self.concepts[i] for i in ids if i in self.concepts]

    def by_tag(self, tag: str) -> list[OKFConcept]:
        """Return all concepts carrying a given tag."""
        ids = self._by_tag.get(tag, [])
        return [self.concepts[i] for i in ids if i in self.concepts]

    def search(self, query: str, top_k: int = 10) -> list[OKFConcept]:
        """Find concepts relevant to a query using type/tag matching + keyword overlap.

        Priority:
        1. Exact type match (query matches a known type name)
        2. Tag match (query matches a tag)
        3. Keyword overlap in title + description + body
        """
        q = query.lower().strip()
        if not q:
            return []

        scored: list[tuple[int, str]] = []

        # 1. Type match — query contains a known type name
        for type_name, ids in self._by_type.items():
            if type_name.lower() in q:
                for cid in ids:
                    if cid in self.concepts:
                        scored.append((100, cid))

        # 2. Tag match
        for tag, ids in self._by_tag.items():
            if tag.lower() in q:
                for cid in ids:
                    if cid in self.concepts:
                        scored.append((80, cid))

        # 3. Keyword overlap in title/description/body
        q_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", q))
        for concept in self.concepts.values():
            if concept.concept_id in [cid for _, cid in scored]:
                continue  # already scored above
            body_text = " ".join([
                concept.title or "",
                concept.description or "",
                concept.body[:3000],
            ]).lower()
            text_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", body_text))
            overlap = len(q_words & text_words)
            if overlap > 0:
                scored.append((overlap * 2, concept.concept_id))
            # Also check for multi-word phrase overlap (e.g. "कसरी भर्ने" in body)
            if q and q in body_text:
                scored.append((50, concept.concept_id))

        # Deduplicate, sort by score desc
        seen: dict[str, int] = {}
        for score, cid in scored:
            if cid not in seen or score > seen[cid]:
                seen[cid] = score

        ranked = sorted(seen.items(), key=lambda x: x[1], reverse=True)
        result_ids = [cid for cid, _ in ranked[:top_k] if cid in self.concepts]
        return [self.concepts[cid] for cid in result_ids]

    def get_relevant_concepts(self, question: str) -> list[OKFConcept]:
        """Convenience: return concepts relevant to a natural-language question."""
        return self.search(question, top_k=5)

    @property
    def concept_count(self) -> int:
        return len(self.concepts)

    @property
    def types(self) -> list[str]:
        return list(self._by_type.keys())

    @property
    def tags(self) -> list[str]:
        return list(self._by_tag.keys())


# ─── Query router ────────────────────────────────────────────────────────────────

# Keywords that suggest a structured/curated-knowledge question
_OKF_INTENT_KEYWORDS = [
    # Document type identification
    "passport", "राहदानी", "citizenship", "नागरिकता", "nagarikta",
    "national id", "परिचयपत्र", "national identity", "nid",
    "voter id", "एम्बैडमेन्ट", "embassy", "जर 구운",
    "permanent residence", "स्थायी बसोबास",
    # Document structure / field questions
    "field", "field meaning", "क्षेत्र", "के हो",
    "page", "page 1", "page 2", "page 3", "page 4",
    "what is this", "यो के हो", "भित्र के छ",
    "structure", "format", "format के हो",
    "document type", "कसरी भिन्न्छ", "भेद",
    # Form / process questions
    "fill", "भर्नु", "bharna", "how to fill", "कसरी भर्ने",
    "requirement", "आवश्यक", "चाहिने",
    "process", "प्रक्रिया", "kasari", "कसरी",
    "apply", "आवेदन", "application",
    "office", "कार्यालय", "department", "विभाग",
    # General document understanding
    "understand", "बुझ्न", "explain", "व्याख्या",
    "meaning", "अर्थ",
]

# Keywords that suggest the user is asking about a SPECIFIC uploaded document
_DOCUMENT_INTENT_KEYWORDS = [
    "my document", "मेरो कागजात", "यो कागजात", "this document",
    "uploaded", "दिएर", "दिएको", "दिएको कागजात",
    "the document", "that document",
]


def classify_query(question: str) -> str:
    """Classify a user question into one of three buckets:

    - 'okf':      Curated knowledge question → route to OKF bundle
    - 'document': Question about a specific uploaded document → vector search
    - 'general':  General Nepal info / chit-chat → official_answer or LLM

    Returns the bucket name.
    """
    q = question.lower().strip()
    if not q:
        return "general"

    # If the question references a specific uploaded document, it's a document query
    for kw in _DOCUMENT_INTENT_KEYWORDS:
        if kw in q:
            return "document"

    # Check OKF intent keywords
    for kw in _OKF_INTENT_KEYWORDS:
        if kw in q:
            return "okf"

    return "general"


def is_okf_question(question: str) -> bool:
    """Shorthand: does this question belong in the OKF layer?"""
    return classify_query(question) == "okf"
