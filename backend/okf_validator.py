"""
hamigenz — OKF bundle validator.

Validates that data/okf/ concept files conform to OKF v0.2.
Run as: python -m backend.okf_validator
Or: from backend.okf_validator import validate_bundle, validate_concept
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml


# ─── OKF v0.2 field validation ───────────────────────────────────────────────────

# Reserved frontmatter keys that OKF v0.2 defines.
# Producers may add arbitrary extra keys; consumers MUST preserve them.
_RESERVED_KEYS = frozenset({
    "type", "title", "description", "resource", "tags",
    "generated", "verified", "sources", "status", "stale_after",
    "okf_version", "owner",
})

# Valid status values per OKF v0.2 §5.
_VALID_STATUSES = frozenset({"draft", "stable", "deprecated"})

# Minimum type name pattern: must start with a letter, then letters/digits/_/-
_TYPE_PAT = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

# Markdown link pattern for extracting concept references from body.
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Internal .md link pattern — links pointing to other concept files in the bundle.
_INTERNAL_MD_LINK_RE = re.compile(r"^(?:\.?/)*[^/]*\.md$", re.IGNORECASE)


def validate_concept(concept_path: Path, bundle_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate a single OKF concept file.

    Returns (ok, errors) where errors is a list of human-readable violation strings.
    """
    errors: list[str] = []

    try:
        raw = concept_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, [f"Cannot read file: {e}"]

    if not raw.startswith("---"):
        errors.append("File does not start with YAML frontmatter (---)")
        return False, errors

    frontmatter, body = _split_frontmatter(raw)
    if frontmatter is None:
        errors.append("Malformed frontmatter: could not find closing ---")
        return False, errors

    try:
        meta = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML frontmatter: {e}")
        return False, errors

    if not isinstance(meta, dict):
        errors.append("Frontmatter must be a YAML mapping (dict)")
        return False, errors

    # --- type (required) ---
    concept_type = meta.get("type")
    if not concept_type or not isinstance(concept_type, str):
        errors.append("Missing or invalid 'type' field (required, non-empty string)")
    elif not _TYPE_PAT.match(concept_type.strip()):
        errors.append(f"'type' value '{concept_type}' does not match OKF type naming pattern")

    # --- status (optional, but must be valid if present) ---
    status = meta.get("status")
    if status is not None:
        if not isinstance(status, str):
            errors.append("'status' must be a string if present")
        elif status not in _VALID_STATUSES:
            errors.append(
                f"'status' value '{status}' is not valid. "
                f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}"
            )

    # --- stale_after (optional, but must be parseable if present) ---
    stale_after = meta.get("stale_after")
    if stale_after is not None:
        if not isinstance(stale_after, str):
            errors.append("'stale_after' must be a string if present")
        else:
            _check_stale_after(stale_after, errors)

    # --- generated (optional object) ---
    generated = meta.get("generated")
    if generated is not None:
        if not isinstance(generated, dict):
            errors.append("'generated' must be a mapping if present")
        else:
            _check_generated(generated, errors)

    # --- verified (optional list) ---
    verified = meta.get("verified")
    if verified is not None:
        if not isinstance(verified, list):
            errors.append("'verified' must be a list if present")
        else:
            _check_verified(verified, errors)

    # --- sources (optional list) ---
    sources = meta.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            errors.append("'sources' must be a list if present")
        else:
            _check_sources(sources, errors)

    # --- okf_version (optional, but if present must be valid) ---
    okf_version = meta.get("okf_version")
    if okf_version is not None:
        if not isinstance(okf_version, str):
            errors.append("'okf_version' must be a string if present")
        elif okf_version not in ("0.1", "0.2"):
            errors.append(f"'okf_version' value '{okf_version}' is not a known OKF version")

    # --- Check for problematic custom syntax in body ---
    if body:
        _check_body_syntax(body, concept_path.name, errors)

    # --- Check internal markdown links ---
    if body:
        _check_internal_links(body, bundle_dir, errors)

    return (len(errors) == 0, errors)


def _check_stale_after(value: str, errors: list[str]) -> None:
    """stale_after must be an absolute ISO date (YYYY-MM-DD) per OKF v0.2."""
    m = re.match(r"^\d{4}-\d{2}-\d{2}$", value)
    if not m:
        errors.append(
            f"'stale_after' value '{value}' is not a valid absolute date (YYYY-MM-DD)"
        )
        return
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            errors.append(f"'stale_after' value '{value}' has invalid month/day")
    except ValueError:
        errors.append(f"'stale_after' value '{value}' could not be parsed")


def _check_generated(generated: dict, errors: list[str]) -> None:
    """generated must be {by, at} where at is an ISO timestamp."""
    if "by" not in generated:
        errors.append("'generated' object missing 'by' field")
    if "at" not in generated:
        errors.append("'generated' object missing 'at' field")
    else:
        at = generated["at"]
        if not isinstance(at, str):
            errors.append("'generated.at' must be a string")
        elif not re.match(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?", at):
            errors.append(f"'generated.at' value '{at}' is not a valid ISO timestamp")


def _check_verified(verified: list, errors: list[str]) -> None:
    """verified must be a list of {by, at} objects."""
    for i, entry in enumerate(verified):
        if not isinstance(entry, dict):
            errors.append(f"'verified' entry {i} must be a mapping")
            continue
        if "by" not in entry:
            errors.append(f"'verified' entry {i} missing 'by' field")


def _check_sources(sources: list, errors: list[str]) -> None:
    """sources must be a list of mappings with at least 'name' or 'id'."""
    for i, entry in enumerate(sources):
        if not isinstance(entry, dict):
            errors.append(f"'sources' entry {i} must be a mapping")
            continue
        if "name" not in entry and "id" not in entry:
            errors.append(f"'sources' entry {i} missing 'name' or 'id'")


def _check_body_syntax(body: str, filename: str, errors: list[str]) -> None:
    """Check for non-OKF custom syntax in the body."""
    # Detect custom [[...]] syntax — not part of OKF v0.2
    if re.search(r"\[\[[^\]]+\]\]", body):
        errors.append(
            f"Body contains custom [[...]] syntax which is NOT part of OKF v0.2. "
            f"Use standard Markdown links: [text](path/to/concept.md)"
        )


def _check_internal_links(body: str, bundle_dir: Path, errors: list[str]) -> None:
    """Validate that internal .md links in the body point to existing concepts."""
    links = _MARKDOWN_LINK_RE.findall(body)
    missing: list[str] = []
    for text, target in links:
        # Only check links that look like they point to .md files in the bundle
        if not _INTERNAL_MD_LINK_RE.match(target.strip()):
            continue
        # Resolve relative to the concept's directory
        concept_dir = bundle_dir
        target_path = (concept_dir / target.strip()).resolve()
        # Also try relative to the file's own directory
        file_dir = bundle_dir  # simplified: all concepts are under bundle_dir
        alt_path = (file_dir / target.strip()).resolve()
        if not target_path.exists() and not alt_path.exists():
            # Check if it matches a known concept path
            found = False
            for md_file in bundle_dir.rglob("*.md"):
                rel = md_file.relative_to(bundle_dir)
                if str(rel) == target.strip() or str(rel.with_suffix("")) ==target.strip().removesuffix(".md"):
                    found = True
                    break
            if not found:
                missing.append(target)
    if missing:
        errors.append(
            f"Internal markdown links reference non-existent files: {', '.join(missing)}"
        )


def _split_frontmatter(raw: str) -> tuple[Optional[str], str]:
    """Split markdown into (yaml_frontmatter, body)."""
    if not raw.startswith("---"):
        return None, raw
    rest = raw[3:]
    idx = rest.find("\n---")
    if idx == -1:
        return None, raw
    fm = rest[:idx]
    body = rest[idx + 4:]
    return fm, body


# ─── Bundle-level validation ──────────────────────────────────────────────────────

def validate_bundle(bundle_dir: str | Path) -> tuple[bool, list[str]]:
    """
    Validate an entire OKF bundle directory.

    Checks:
    - Bundle directory exists
    - At least one concept file present
    - index.md exists (recommended)
    - Every concept file validates
    - No duplicate concept IDs
    - All internal links resolve
    """
    bundle = Path(bundle_dir)
    errors: list[str] = []

    if not bundle.is_dir():
        return False, [f"Bundle directory does not exist: {bundle}"]

    md_files = sorted(bundle.rglob("*.md"))
    if not md_files:
        errors.append("Bundle contains no .md files")
        return (len(errors) == 0, errors)

    # Check for index.md
    index_path = bundle / "index.md"
    if not index_path.exists():
        errors.append("Recommended: bundle root 'index.md' not found")

    # Validate each concept
    concept_ids: dict[str, Path] = {}
    for md_file in md_files:
        rel = md_file.relative_to(bundle)
        concept_id = str(rel.with_suffix(""))
        if concept_id == "index":
            continue

        if concept_id in concept_ids:
            errors.append(
                f"Duplicate concept ID '{concept_id}': also at {concept_ids[concept_id]}"
            )
            continue
        concept_ids[concept_id] = md_file

        ok, file_errors = validate_concept(md_file, bundle)
        if not ok:
            for e in file_errors:
                errors.append(f"{rel}: {e}")

    # Validate index.md if present
    if index_path.exists():
        ok, index_errors = validate_concept(index_path, bundle)
        if not ok:
            for e in index_errors:
                errors.append(f"index.md: {e}")
        # Check index.md doesn't have duplicate frontmatter issues
        try:
            raw = index_path.read_text(encoding="utf-8")
            if raw.startswith("---"):
                rest = raw[3:]
                idx = rest.find("\n---")
                if idx != -1:
                    fm = rest[:idx]
                    try:
                        meta = yaml.safe_load(fm) or {}
                        if not isinstance(meta, dict):
                            errors.append("index.md frontmatter must be a YAML mapping")
                    except yaml.YAMLError:
                        pass  # already caught by validate_concept
        except Exception:
            pass

    return (len(errors) == 0, errors)


# ─── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    bundle_dir = sys.argv[1] if len(sys.argv) > 1 else "data/okf"
    ok, errors = validate_bundle(bundle_dir)
    if ok:
        print(f"OKF bundle at {bundle_dir}: VALID")
        sys.exit(0)
    else:
        print(f"OKF bundle at {bundle_dir}: {len(errors)} violation(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
