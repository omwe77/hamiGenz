"""
hamigenz — Open Knowledge Format (OKF) v0.2 bundle loader, router, and graph.

OKF is a vendor-neutral spec (Google Cloud, July 2026) for curating
organizational knowledge as markdown files with YAML frontmatter.

An OKF bundle is a directory tree of concept files:
  - One concept per .md file
  - YAML frontmatter (only required field: `type`)
  - Standard Markdown body with [text](path.md) links between concepts
  - Lives in git, diffable, human + AI readable

For hamiGenZ, OKF replaces the chunking-based RAG approach for curated
knowledge (document type definitions, field meanings, form guidelines).
User-uploaded document search still uses VectorStore directly.

Conformance: v0.2 — see https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

# ─── Type validation ────────────────────────────────────────────────────────────
# OKF §4.1: type is the only required field. Consumers MUST tolerate unknown
# types gracefully (§11). We accept any non-empty string with a reasonable
# maximum length. Spaces and Unicode are allowed (e.g. "Attested Computation",
# "Field Definition").
#
# We do NOT reject types with spaces — the spec gives "BigQuery Table" as an
# example type value, and "Attested Computation" is a defined v0.2 concept type.



# ─── Standard Markdown link extraction ─────────────────────────────────────────

# Match [text](target.md) and [text](/bundle/relative/path.md) links.
# Excludes external http/https links and mailto:.
_LINK_RE = re.compile(
    r"\[(?P<text>[^\]]*)\]\(\s*(?P<target>[^)\s#]+\.md(?:\s*[^)]*)?)\s*\)"
)

# ─── Frontmatter split ──────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ─── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class OKFSource:
    """A single provenance source entry (§5.1)."""

    id: Optional[str] = None
    resource: Optional[str] = None  # REQUIRED per spec, but tolerate absent
    title: Optional[str] = None
    author: Optional[str] = None
    usage_count: Optional[int] = None
    last_modified: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "OKFSource":
        return cls(
            id=str(d["id"]) if d.get("id") else None,
            resource=str(d["resource"]) if d.get("resource") else None,
            title=str(d["title"]) if d.get("title") else None,
            author=str(d["author"]) if d.get("author") else None,
            usage_count=int(d["usage_count"]) if d.get("usage_count") else None,
            last_modified=str(d["last_modified"]) if d.get("last_modified") else None,
        )


@dataclass
class OKFVerificationEvent:
    """One verification event (§5.2)."""

    by: str  # actor: human:<id>, process:<id>, or agent/<version>
    at: str  # ISO 8601 datetime

    @classmethod
    def from_dict(cls, d: dict) -> "OKFVerificationEvent":
        return cls(
            by=str(d["by"]) if d.get("by") else "",
            at=str(d["at"]) if d.get("at") else "",
        )


@dataclass
class OKFConcept:
    """One OKF concept — a single markdown file with frontmatter + body.

    Supports all v0.2 frontmatter families:
      - Required: type
      - Recommended: title, description, resource, tags
      - Trust: generated, verified (list of events)
      - Lifecycle: status (draft|stable|deprecated), stale_after
      - Provenance: sources (list of OKFSource)
      - Unknown/arbitrary keys preserved in extra_metadata
    """

    concept_id: str  # e.g. "document-types/passport"
    type: str  # required frontmatter field
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    # Trust
    generated: Optional[dict] = None  # {by, at} — may be bare dict or full
    verified: list[OKFVerificationEvent] = field(default_factory=list)
    # Lifecycle
    status: Optional[str] = None  # draft | stable | deprecated; absent → stable
    stale_after: Optional[str] = None  # ISO 8601 datetime
    # Provenance
    sources: list[OKFSource] = field(default_factory=list)
    # Producer-defined metadata (preserved from frontmatter)
    owner: Optional[str] = None  # e.g. "Passport Department, Ministry of Foreign Affairs"
    usage_window: Optional[str] = None  # ISO 8601 datetime range when valid
    # Body + links
    body: str = ""
    links: list[tuple[str, str]] = field(default_factory=list)  # (text, target)
    # Extra/unknown frontmatter keys preserved for round-tripping
    extra_metadata: dict = field(default_factory=dict)

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def file_path(self) -> str:
        return self.concept_id + ".md"

    @property
    def trust_tier(self) -> str:
        """Derive trust tier from verified field (§5.3).

        Returns: "unverified" | "machine-confirmed" | "human-reviewed"
        """
        if not self.verified:
            return "unverified"
        # Check for any human:<id> verifier
        for ev in self.verified:
            if ev.by.startswith("human:"):
                return "human-reviewed"
        return "machine-confirmed"

    @property
    def is_stale(self) -> bool:
        """True if now >= stale_after (§5.5)."""
        if not self.stale_after:
            return False
        try:
            stale = datetime.fromisoformat(self.stale_after.replace("Z", "+00:00"))
            return datetime.now(stale.tzinfo or datetime.now().astimezone().tzinfo) >= stale
        except (ValueError, TypeError):
            return False

    @property
    def effective_status(self) -> str:
        """Status with default: absent → stable (§5.4)."""
        return self.status or "stable"

    def summary(self) -> dict:
        """Public view — safe to expose via API."""
        return {
            "concept_id": self.concept_id,
            "type": self.type,
            "title": self.title or "",
            "description": self.description or "",
            "tags": self.tags,
            "status": self.effective_status,
            "trust_tier": self.trust_tier,
            "is_stale": self.is_stale,
            "verified": [
                {"by": ev.by, "at": ev.at}
                for ev in self.verified
            ],
            "resource": self.resource or "",
            "generated": self.generated or {},
            "source_count": len(self.sources),
            "link_count": len(self.links),
        }


# ─── Bundle loader ──────────────────────────────────────────────────────────────

class OKFBundle:
    """Loads and indexes an OKF v0.2 bundle (directory of markdown concept files).

    Handles:
      - Standard Markdown links (not [[concept-id]] custom syntax)
      - index.md / log.md reserved-file semantics
      - Unknown frontmatter fields preserved
      - Unknown concept types tolerated
      - Broken links tolerated
      - Trust tier + staleness computation
      - Graph traversal with cycle protection
    """

    def __init__(self, bundle_dir: str | Path):
        self.bundle_dir = Path(bundle_dir)
        self.concepts: dict[str, OKFConcept] = {}  # concept_id -> concept
        self._by_type: dict[str, list[str]] = {}
        self._by_tag: dict[str, list[str]] = {}
        self._backlinks: dict[str, list[str]] = {}  # target_id -> [source_ids]
        self._loaded = False

    def load(self) -> int:
        """Load all .md files from the bundle directory. Returns concept count."""
        if self._loaded:
            return len(self.concepts)
        self.concepts.clear()
        self._by_type.clear()
        self._by_tag.clear()
        self._backlinks.clear()

        if not self.bundle_dir.is_dir():
            return 0

        for md_path in sorted(self.bundle_dir.rglob("*.md")):
            rel = md_path.relative_to(self.bundle_dir)
            concept_id = str(rel.with_suffix("")).replace(os.sep, "/")

            # Reserved files: index.md and log.md are NOT concepts (§3.1, §8, §9)
            # These are reserved at EVERY directory level, not just root.
            parts = concept_id.split("/")
            if parts[-1] in ("index", "log"):
                continue

            concept = self._parse_file(md_path, concept_id)
            if concept:
                self.concepts[concept_id] = concept
                t = concept.type
                self._by_type.setdefault(t, []).append(concept_id)
                for tag in concept.tags:
                    self._by_tag.setdefault(tag, []).append(concept_id)

        # Build backlinks index
        for cid, concept in self.concepts.items():
            for _, target in concept.links:
                target_id = self._resolve_link_target(cid, target)
                if target_id and target_id in self.concepts:
                    self._backlinks.setdefault(target_id, []).append(cid)

        self._loaded = True
        return len(self.concepts)

    def _resolve_link_target(self, source_id: str, target: str) -> Optional[str]:
        """Resolve a Markdown link target to a concept_id.

        Handles absolute (/path/to/file.md) and relative (../file.md) paths.
        Returns None for external URLs or unresolvable targets.
        """
        t = target.strip()
        # External URL — not a concept link
        if t.startswith(("http://", "https://", "mailto:")):
            return None
        # Absolute bundle-relative: /path/to/file.md → strip leading / and .md
        if t.startswith("/"):
            clean = t.lstrip("/").replace(".md", "")
            return clean if clean in self.concepts else None
        # Relative path: resolve from source directory
        source_dir = os.path.dirname(source_id)
        resolved = os.path.normpath(os.path.join(source_dir, t))
        clean = resolved.replace(os.sep, "/").replace(".md", "")
        return clean if clean in self.concepts else None

    def _parse_file(self, path: Path, concept_id: str) -> Optional[OKFConcept]:
        """Parse a single markdown file into an OKFConcept."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        frontmatter, body = self._split_frontmatter(raw)
        if frontmatter is None:
            return None

        try:
            meta = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            return None

        if not isinstance(meta, dict):
            return None

        # `type` is the only required field (§4.1, §11)
        concept_type = meta.get("type", "")
        if not concept_type or not isinstance(concept_type, str):
            return None
        concept_type = str(concept_type).strip()
        # OKF §11: consumers MUST NOT reject unknown type values.
        # Accept any non-empty string — no arbitrary length restriction.
        # A safety ceiling exists at the filesystem layer (filename length),
        # not as an OKF semantic restriction.
        if not concept_type:
            return None

        # Extract standard Markdown links from body
        links: list[tuple[str, str]] = []
        for m in _LINK_RE.finditer(body):
            text = m.group("text").strip()
            target = m.group("target").strip()
            # Skip external URLs
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            links.append((text, target))

        # Parse verified as a list of events (§5.2)
        verified_raw = meta.get("verified", None)
        verified_events: list[OKFVerificationEvent] = []
        if verified_raw is not None:
            if isinstance(verified_raw, dict):
                # Bare mapping → one-element list (§5.2 consumer rule)
                verified_events.append(OKFVerificationEvent.from_dict(verified_raw))
            elif isinstance(verified_raw, list):
                for item in verified_raw:
                    if isinstance(item, dict):
                        verified_events.append(OKFVerificationEvent.from_dict(item))

        # Parse sources (§5.1)
        sources_raw = meta.get("sources", None)
        sources: list[OKFSource] = []
        if sources_raw and isinstance(sources_raw, list):
            for item in sources_raw:
                if isinstance(item, dict):
                    sources.append(OKFSource.from_dict(item))

        # Parse generated (§5.2)
        generated_raw = meta.get("generated", None)
        generated = None
        if isinstance(generated_raw, dict):
            generated = {k: str(v) for k, v in generated_raw.items()}

        # Collect unknown keys for preservation
        known_keys = {
            "type", "title", "description", "resource", "tags",
            "generated", "verified", "sources", "status", "stale_after",
            "okf_version", "owner", "usage_window",
        }
        extra_metadata = {
            k: v for k, v in meta.items()
            if k not in known_keys
        }

        concept = OKFConcept(
            concept_id=concept_id,
            type=concept_type,
            title=str(meta["title"]) if meta.get("title") else None,
            description=str(meta["description"]) if meta.get("description") else None,
            resource=str(meta["resource"]) if meta.get("resource") else None,
            tags=[str(t) for t in (meta.get("tags") or [])],
            generated=generated,
            verified=verified_events,
            status=str(meta["status"]) if meta.get("status") else None,
            stale_after=str(meta["stale_after"]) if meta.get("stale_after") else None,
            sources=sources,
            owner=str(meta["owner"]) if meta.get("owner") else None,
            usage_window=str(meta["usage_window"]) if meta.get("usage_window") else None,
            body=body.strip(),
            links=links,
            extra_metadata=extra_metadata,
        )

        return concept

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[Optional[str], str]:
        """Split markdown into (yaml_frontmatter, body).

        Returns (None, raw) if no frontmatter found.
        """
        m = _FRONTMATTER_RE.match(raw)
        if not m:
            return None, raw
        return m.group(1), raw[m.end():]

    # ─── Query helpers ─────────────────────────────────────────────────────────

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

    def get_backlinks(self, concept_id: str) -> list[OKFConcept]:
        """Return concepts that link TO this concept (§6.1)."""
        ids = self._backlinks.get(concept_id, [])
        return [self.concepts[i] for i in ids if i in self.concepts]

    def get_related(
        self,
        concept_id: str,
        max_hops: int = 1,
        visited: Optional[set] = None,
    ) -> list[OKFConcept]:
        """Get related concepts via graph traversal with cycle protection.

        Args:
            concept_id: Starting concept.
            max_hops: Maximum expansion depth (1 = direct links only).
            visited: Internal — set of already-visited IDs.

        Returns: list of related concepts, deduplicated, excluding the start.
        """
        if visited is None:
            visited = {concept_id}
        if max_hops <= 0 or concept_id not in self.concepts:
            return []

        result: dict[str, OKFConcept] = {}
        concept = self.concepts[concept_id]

        # Outgoing links
        for _, target in concept.links:
            target_id = self._resolve_link_target(concept_id, target)
            if target_id and target_id not in visited and target_id in self.concepts:
                visited.add(target_id)
                result[target_id] = self.concepts[target_id]

        # One-hop expansion
        if max_hops > 1:
            for linked_id in list(result.keys()):
                for rel in self.get_related(linked_id, max_hops - 1, visited):
                    if rel.concept_id not in result and rel.concept_id != concept_id:
                        result[rel.concept_id] = rel

        # Add backlinks (concepts that link TO this one)
        for back_id in self._backlinks.get(concept_id, []):
            if back_id not in visited and back_id in self.concepts:
                visited.add(back_id)
                result[back_id] = self.concepts[back_id]

        return list(result.values())

    def search(
        self,
        query: str,
        top_k: int = 10,
        include_body: bool = True,
    ) -> list[OKFConcept]:
        """Find concepts relevant to a query using type/tag matching + keyword overlap.

        Key difference from naive truncation: we scan ALL sections of each
        concept's body for keyword overlap. A concept whose answer appears only
        near the end is still findable. This is what makes OKF retrieval
        fundamentally better than chunk-based RAG for structured knowledge.

        Priority:
        1. Exact type match
        2. Tag match
        3. Keyword overlap — MAX section score across all body sections
        """
        q = query.lower().strip()
        if not q:
            return []

        scored: dict[str, int] = {}

        # 1. Type match
        for type_name, ids in self._by_type.items():
            if type_name.lower() in q:
                for cid in ids:
                    scored[cid] = scored.get(cid, 0) + 100

        # 2. Tag match
        for tag, ids in self._by_tag.items():
            if tag.lower() in q:
                for cid in ids:
                    scored[cid] = scored.get(cid, 0) + 80

        # 3. Keyword overlap — scan ALL body sections, not just first N chars
        q_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", q))
        # Also extract multi-word phrases from query for phrase matching
        q_phrases = set()
        q_words_list = q.split()
        for i in range(len(q_words_list)):
            for j in range(i + 1, min(i + 5, len(q_words_list) + 1)):
                phrase = " ".join(q_words_list[i:j])
                if len(phrase) >= 4:  # ignore very short phrases
                    q_phrases.add(phrase)

        for concept in self.concepts.values():
            if concept.concept_id in scored:
                continue
            if not include_body:
                continue

            # Split body into sections by headings
            sections = self._split_sections(concept.body)
            best_section_score = 0
            best_section_keywords = []

            for heading, content in sections:
                combined = f"{heading} {content}".lower()
                text_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", combined))
                overlap = len(q_words & text_words)
                if overlap > best_section_score:
                    best_section_score = overlap
                    best_section_keywords = list(q_words & text_words)

                # Multi-word phrase match
                for phrase in q_phrases:
                    if phrase in combined:
                        best_section_score += 3

            # Also check full body for phrase matches (catch phrases across sections)
            full_lower = concept.body.lower()
            for phrase in q_phrases:
                if phrase in full_lower:
                    best_section_score += 3

            if best_section_score > 0:
                scored[concept.concept_id] = best_section_score * 2

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        result_ids = [cid for cid, _ in ranked[:top_k] if cid in self.concepts]
        return [self.concepts[cid] for cid in result_ids]

    @staticmethod
    def _split_sections(body: str) -> list[tuple[str, str]]:
        """Split markdown body into (heading, content) sections.

        Returns list of (heading_text, content_text) tuples.
        Content includes everything until the next heading.
        """
        sections: list[tuple[str, str]] = []
        current_heading = "Overview"
        current_content = []

        for line in body.split("\n"):
            if line.startswith("#"):
                if current_content:
                    sections.append((current_heading, "\n".join(current_content)))
                current_heading = line.strip()
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections.append((current_heading, "\n".join(current_content)))

        return sections

    def get_relevant_concepts(self, question: str) -> list[OKFConcept]:
        """Convenience: return concepts relevant to a natural-language question."""
        return self.search(question, top_k=5)

    def get_section_context(
        self,
        concept_id: str,
        question: str,
        max_chars: int = 6000,
    ) -> str:
        """Section-aware context extraction for LLM prompting.

        Budget strategy:
        1. Score all sections by keyword overlap
        2. Reserve space for the final section if it's relevant
        3. Include mandatory safety/exception sections regardless of query
        4. Fill remaining budget with most relevant sections
        5. Within each section, preserve head + tail (not just head truncation)

        Does NOT blindly truncate like body[:1500].
        Guarantees end-of-document information reaches the LLM when relevant.
        """
        concept = self.get(concept_id)
        if not concept:
            return ""

        body = concept.body
        if not body:
            return ""

        # If body fits in budget, return it all
        if len(body) <= max_chars:
            return body

        q_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", question.lower()))
        q_phrases = set()
        q_words_list = question.lower().split()
        for i in range(len(q_words_list)):
            for j in range(i + 1, min(i + 5, len(q_words_list) + 1)):
                phrase = " ".join(q_words_list[i:j])
                if len(phrase) >= 4:
                    q_phrases.add(phrase)

        # Split into sections by headings
        sections = self._split_sections(body)

        # Score each section
        scored_sections: list[tuple[int, str, str, bool]] = []  # (score, heading, content, is_trailing_safety)
        for idx, (heading, content) in enumerate(sections):
            combined = f"{heading} {content}".lower()
            text_words = set(re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", combined))
            score = len(q_words & text_words)

            # Multi-word phrase match
            for phrase in q_phrases:
                if phrase in combined:
                    score += 3

            # Check if this is a safety/exception section
            heading_lower = heading.lower()
            is_safety = any(
                kw in heading_lower
                for kw in [
                    "warning", "note", "disclaimer", "important", "caution",
                    "limitation", "important notes", "watch for", "consider",
                    "सत्र cautionary", "चेतावनी", "सूचना", "महत्त्वपूर्ण",
                ]
            )
            # Last section is always preserved if it's safety-related
            is_last = (idx == len(sections) - 1)
            is_trailing_safety = is_last and is_safety

            # Boost safety sections
            if is_safety:
                score += 5

            scored_sections.append((score, heading, content, is_trailing_safety))

        # Determine how much budget to reserve for trailing safety section
        trailing_reserve = 0
        for score, heading, content, is_trailing in scored_sections:
            if is_trailing and score > 0:
                trailing_reserve = min(len(heading) + len(content) + 40, max_chars // 4)
                break

        available = max_chars - trailing_reserve

        # Sort by score descending, but keep safety sections accessible
        scored_sections.sort(key=lambda x: x[0], reverse=True)

        # Build context from top sections until we hit available budget
        parts: list[str] = []
        chars_used = 0
        used_ids: set[int] = set()

        for score, heading, content, is_trailing in scored_sections:
            if score == 0 and chars_used > 0:
                continue  # skip irrelevant sections once we have relevant ones

            block = f"{heading}\n{content}"
            block_len = len(block)

            if is_trailing:
                # Reserve space for trailing safety section
                if chars_used + block_len > max_chars:
                    # Head+tail: keep first 60% and last 40% of the content
                    reserve = min(block_len, max_chars - chars_used)
                    head_len = int(reserve * 0.6)
                    tail_len = reserve - head_len - len(heading) - 4
                    if tail_len > 100:
                        truncated_content = content[:head_len] + "\n[...]\n" + content[-tail_len:]
                        block = f"{heading}\n{truncated_content}"
                if chars_used + len(block) <= max_chars:
                    parts.append(block)
                    chars_used += len(block)
                    used_ids.add(id(content))
                continue

            if chars_used + block_len > available and chars_used > 0:
                # Head+tail truncation for non-trailing sections
                reserve = available - chars_used
                if reserve > 200:
                    head_len = int(reserve * 0.65)
                    tail_len = reserve - head_len - len(heading) - 4
                    if tail_len > 50:
                        truncated_content = content[:head_len] + "\n[...]\n" + content[-tail_len:]
                        block = f"{heading}\n{truncated_content}"
                        parts.append(block)
                        chars_used += len(block)
                break

            parts.append(block)
            chars_used += block_len
            used_ids.add(id(content))

        # If we didn't include the trailing safety section, try to add it
        if trailing_reserve > 0:
            for score, heading, content, is_trailing in scored_sections:
                if is_trailing and id(content) not in used_ids:
                    block = f"{heading}\n{content}"
                    if chars_used + len(block) <= max_chars:
                        parts.append(block)
                        chars_used += len(block)
                    else:
                        reserve = max_chars - chars_used
                        if reserve > 200:
                            head_len = int(reserve * 0.6)
                            tail_len = reserve - head_len - len(heading) - 4
                            if tail_len > 50:
                                truncated_content = content[:head_len] + "\n[...]\n" + content[-tail_len:]
                                parts.append(f"{heading}\n{truncated_content}")
                                chars_used += len(f"{heading}\n{truncated_content}")
                    break

        return "\n\n".join(parts)

    def _expand_graph(
        self,
        seed_ids: list[str],
        question: str,
        max_hops: int = 1,
        max_added: int = 4,
    ) -> list[str]:
        """Expand seed concept IDs by one hop of graph traversal.

        Only includes linked concepts that are relevant to the query.
        Preserves seed priority — seeds always rank ahead of expansions.
        Bounded: adds at most max_added concepts.
        """
        if not seed_ids or max_hops < 1:
            return list(seed_ids)

        # Get all related concepts (one-hop, deduped, cycle-protected)
        all_related: dict[str, OKFConcept] = {}
        for seed_id in seed_ids:
            if seed_id not in self.concepts:
                continue
            for rel in self.get_related(seed_id, max_hops=max_hops):
                if rel.concept_id not in seed_ids:
                    all_related[rel.concept_id] = rel

        if not all_related:
            return list(seed_ids)

        # Score related concepts by relevance to the query
        q = question.lower().strip()
        scored: list[tuple[int, str]] = []
        for cid, concept in all_related.items():
            score = 0
            # Type match
            if concept.type and concept.type.lower() in q:
                score += 50
            # Tag match
            for tag in concept.tags:
                if tag and tag.lower() in q:
                    score += 30
                    break
            # Keyword overlap in body — check both whole words and content phrases
            body_lower = concept.body.lower()
            # Word-level overlap
            for word in re.findall(r"[\u0900-\u097F]{2,}|[a-z0-9]{2,}", q):
                if word in body_lower:
                    score += 5
            # Also check if any significant phrase from the query appears in body
            q_words_list = q.split()
            for i in range(len(q_words_list)):
                for j in range(i + 1, min(i + 4, len(q_words_list) + 1)):
                    phrase = " ".join(q_words_list[i:j])
                    if len(phrase) >= 4 and phrase in body_lower:
                        score += 3
            scored.append((score, cid))

        # Sort by relevance, then by deterministic ID order for ties
        scored.sort(key=lambda x: (-x[0], x[1]))

        # Keep only relevant expansions (score > 0) plus seeds
        added_ids = [cid for _, cid in scored if _ > 0]
        # Bound expansion
        added_ids = added_ids[:max_added]

        # Final order: seeds first (preserve original order), then expansions
        result = list(seed_ids)
        for cid in added_ids:
            if cid not in result:
                result.append(cid)
        return result

    def get_context_for_llm(
        self,
        concept_ids: list[str],
        question: str,
        max_total_chars: int = 8000,
        graph_expansion: bool = True,
        _pre_ranked: Optional[set[str]] = None,
    ) -> str:
        """Build LLM-context string from multiple concepts with section-aware selection
        and optional one-hop graph expansion.

        With graph_expansion=True (default), related concepts discovered via
        standard Markdown links are added to the context when they are relevant
        to the query — so a query about "passport field meaning" can bring
        field-definition concepts into context even when not named explicitly.

        Progressive disclosure: most relevant concept first, expand only when needed.
        No blind truncation.

        Efficiency: when _pre_ranked is provided (set of pre-scored concept IDs),
        skip the duplicate search — useful when caller already ranked via search().
        """

        if not concept_ids:
            return ""

        # Expand via graph if requested — adds relevant linked concepts
        working_ids = concept_ids
        if graph_expansion:
            working_ids = self._expand_graph(concept_ids, question, max_hops=1, max_added=4)

        # Compute ranking ONCE via search, unless caller precomputed it
        scored_set: set[str] = _pre_ranked if _pre_ranked is not None else set()
        if not scored_set:
            for c in self.search(question, top_k=max(len(working_ids), 10)):
                scored_set.add(c.concept_id)

        # Build context with progressive disclosure
        parts: list[str] = []
        chars_used = 0

        for cid in working_ids:
            if chars_used >= max_total_chars:
                break
            concept = self.get(cid)
            if not concept:
                continue

            remaining = max_total_chars - chars_used
            context = self.get_section_context(cid, question, max_chars=min(remaining, 4000))
            if context:
                # Prefer concepts that appeared in top search results
                prefix = "▶ " if cid in scored_set else "  "
                parts.append(f"{prefix}{cid} ({concept.type})\n{context}")
                chars_used += len(context) + len(cid) + 60

        return "\n\n".join(parts)

    @property
    def concept_count(self) -> int:
        return len(self.concepts)

    @property
    def types(self) -> list[str]:
        return list(self._by_type.keys())

    @property
    def tags(self) -> list[str]:
        return list(self._by_tag.keys())


# ─── Query routing ──────────────────────────────────────────────────────────────

# Deterministic source routing with clear precedence (Part 10).
# Priority:
#   A. Explicit doc_id → document retrieval
#   B. Query about user's uploaded document → document retrieval
#   C. Durable curated knowledge → OKF
#   D. Current official Nepal information → official_answer
#   E. Mixed query → controlled multi-source
#   F. Unknown → transparent insufficient-evidence

# Keywords that indicate a question about a SPECIFIC uploaded document.
# These take highest priority when there's no explicit doc_id.
_DOCUMENT_REF_KEYWORDS = [
    "my document", "मेरो कागजात", "मेरो दस्तावेज",
    "my passport", "my citizenship", "my voter id", "my nid",
    "मेरो राहदानी", "मेरो नागरिकता", "मेरो मतदान",
    "this document", "yo document", "yo kagajat",
    "uploaded", "upload garnye", "upload gardeko",
    "the document", "that document", "tyo document",
    "bittapai", "bitta", "yo file",
]

# Keywords that strongly indicate a curated-knowledge (OKF) question.
# These are for durable, structural knowledge about Nepal documents.
_OKF_INTENT_KEYWORDS = [
    # Document type identification (structural knowledge)
    "passport", "राहदानी", "rahrani", "rahadani",
    "citizenship", "नागरिकता", "nagarikta", "nagarikta pramanapatra",
    "national id", "national identity", "nid", "rashtriya parichay",
    "perichaya", "परिचयपत्र", "national identity card",
    "voter id", "voter identity", "मतदान परिचय", "matdani",
    "embassy", "permanent residence", "स्थायी बसोबास",
    "स्थायी", "basonbas",
    # Document structure / field questions
    "field", "field meaning", "field ko meaning", "field meaning ko",
    "क्षेत्र", "के हो", "yo ke ho", "what is this",
    "page", "page 1", "page 2", "page 3", "page 4",
    "structure", "format", "document type", "dasta rakam",
    "भित्र के छ", "bhitra ke cha", "ke ho",
    # Form / process questions (about HOW to do something)
    "fill", "भर्नु", "bharna", "how to fill", "कसरी भर्ने",
    "kasee bharne", "kasari bharne", "bharne ka",
    "requirement", "आवश्यक", "chahine", "chaahine",
    "process", "प्रक्रिया", "prakriya",
    "apply", "आवेदन", "application", "aavedan",
    "kaaryalaya", "कार्यालय", "department", "vibhag",
    # General document understanding
    "understand", "बुझ्न", "bujhna", "explain", "व्याख्या",
    "vyakhya", "meaning", "अर्थ", "arth",
    "form", "dastavala", "फारम",
]

# Keywords that indicate the user wants CURRENT official information
# (fees, deadlines, current procedures) — routed to official_answer.
_CURRENT_INFO_KEYWORDS = [
    "fee", "fees", "cost", "price", "कति", "शुल्क", "dastur",
    "शुल्क", "rupee", "रु", "rs.", "rs",
    "kharch", "kharcha", "lagyo", "lagne",
    "deadline", "last date", "अन्तिम मिति", "anti limiti",
    "mati", "date", "मिति",
    "current", "halaij", "वर्तमान",
    "required documents", "चाहिने कागजात", "documents needed",
    "application process", "process of applying", "how to apply for",
    "जहाँ", "where to", "कहाँ", "office location",
    "requirement", "requirements", "आवश्यक", "चाहिने",
]


def classify_query(
    question: str,
    has_doc_id: bool = False,
    doc_reference_hint: Optional[str] = None,
) -> str:
    """Classify a user question into one of five buckets:

    - 'okf':        Curated knowledge question → route to OKF bundle
    - 'document':   Question about a specific uploaded document → vector search
    - 'official':   Current official Nepal information → official_answer
    - 'mixed':      Query spanning multiple source types → multi-source response
    - 'general':    General Nepal info / chit-chat / unknown → LLM or official

    Routing precedence (highest first):
    1. Explicit doc_id → document
    2. Document reference keywords → document
    3. Mixed query detection (structural + current-info) → mixed
    4. Current-info keywords + official intent → official
    5. OKF intent keywords → okf
    6. Default → general

    Do NOT let a single word like "passport" decide the route.
    A question containing "passport" AND "fee" should go to official,
    not OKF, because fees are current dynamic information.
    """
    q = question.lower().strip()
    if not q:
        return "general"

    # A. Explicit doc_id always goes to document
    if has_doc_id:
        return "document"

    # B. Document reference — user is asking about THEIR uploaded document
    for kw in _DOCUMENT_REF_KEYWORDS:
        if kw in q:
            return "document"

    # C. Current-info detection: if the query asks about fees, deadlines,
    #    current procedures → route to official_answer (dynamic facts)
    wants_current = any(kw in q for kw in _CURRENT_INFO_KEYWORDS)

    # D. OKF intent — structural knowledge about document types, fields, forms
    has_okf_intent = any(kw in q for kw in _OKF_INTENT_KEYWORDS)

    # E. If both current-info and OKF intent, check for genuinely mixed queries
    #    that need both OKF (structural knowledge) AND official (current info).
    #    A mixed query has substantive questions in BOTH domains — not just
    #    a keyword overlap.
    if wants_current and has_okf_intent:
        # Detect mixed queries: must have both a structural-OKF question
        # AND a current-info question in the same sentence.
        # "What is the passport and what is the current application fee?"
        # -> structural ("what is passport") + current ("current fee")
        # vs.
        # "What is the passport fee?" -> just fee question (official only)
        has_structural_phrase = any(phrase in q for phrase in [
            "what is", "के हो", "yo ke ho", "describe", "explain",
            "structure", "format", "tell me about", "give me info",
        ])
        has_current_phrase = any(phrase in q for phrase in [
            "current", "वर्तमान", "halaij", "fee", "कति", "शुल्क",
            "cost", "price", "required", "चाहिने", "how to apply",
            "application process", "deadline", "मिति",
        ])
        # Also detect conjunction-based mixed queries: "X and Y" where
        # X is structural and Y is current-info
        has_conjunction = " and " in q or " र " in q or " & " in q

        # If there's a conjunction with structural + current phrases, it's mixed
        if has_conjunction and (has_structural_phrase or has_current_phrase):
            return "mixed"

        # Pure fee/cost/deadline questions (even with structural keywords)
        # should go to official, not mixed
        is_pure_fee_question = len(q.split()) <= 8 and any(kw in q for kw in [
            "fee", "cost", "price", "कति", "शुल्क", "kharch", "lagyo",
        ])
        is_pure_deadline_question = len(q.split()) <= 10 and any(kw in q for kw in [
            "deadline", "मिति", "mati", "last date", "अन्तिम मिति",
        ])

        if is_pure_fee_question or is_pure_deadline_question:
            return "official"

        if (has_structural_phrase and has_current_phrase) or has_conjunction:
            return "mixed"  # Needs both OKF + official

        # Short queries with fee/cost/deadline keywords → official only
        if len(q.split()) <= 10 and any(kw in q for kw in [
            "fee", "cost", "price", "कति", "शुल्क", "deadline", "मिति",
            "kharch", "lagyo", "lagne", "required", "requirements",
            "how to apply", "where to", "कहाँ", "जहाँ",
        ]):
            return "official"
        # Otherwise, prefer OKF for the structural part
        return "okf"

    if wants_current:
        return "official"

    if has_okf_intent:
        return "okf"

    return "general"


def is_okf_question(question: str, has_doc_id: bool = False) -> bool:
    """Shorthand: does this question belong in the OKF layer?"""
    return classify_query(question, has_doc_id=has_doc_id) in ("okf", "mixed")


def should_use_official_source(question: str) -> bool:
    """Does this question need current official information?"""
    return classify_query(question) in ("official", "mixed")


def should_use_document_search(
    question: str,
    has_doc_id: bool = False,
) -> bool:
    """Does this question need uploaded-document vector search?"""
    return classify_query(question, has_doc_id=has_doc_id) == "document"


def classify_query_detailed(question: str) -> dict:
    """Return detailed classification with source recommendations.

    Returns dict with:
        - primary: main classification bucket
        - sources: list of source types to query (okf, official, document)
        - mixed: bool indicating multi-source need
    """
    q = question.lower().strip()
    if not q:
        return {"primary": "general", "sources": [], "mixed": False}

    has_doc = False  # would be passed in real usage
    primary = classify_query(question)

    sources = []
    if primary in ("okf", "mixed", "document"):
        sources.append("okf")
    if primary in ("official", "mixed"):
        sources.append("official")
    if primary == "document":
        sources.append("document")

    return {
        "primary": primary,
        "sources": sources,
        "mixed": primary == "mixed",
    }
