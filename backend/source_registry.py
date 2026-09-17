"""
hamigenz — Official Nepal knowledge source registry (PR-011).

A source is "official" because it is in this curated registry AND marked
verified — NOT because of its domain TLD. org.np / edu.np are open
registration TLDs in Nepal; any company, NGO, or individual can register
them, so they carry zero inherent authority here.

The registry tracks: organization, domain, title, source type, authority
level, verified status, publication/update date, retrieval date, and
current/outdated/repealed status — per the PRD.
"""
import json
import os
import re
from datetime import date, datetime
from functools import lru_cache
from urllib.parse import urlparse

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "knowledge_sources.json")


@lru_cache(maxsize=1)
def _load_registry() -> dict:
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def reload_registry() -> None:
    """Drop the cached registry (used after the JSON file is edited)."""
    _load_registry.cache_clear()


def all_sources() -> list[dict]:
    return _load_registry()["sources"]


def get_source(source_id: str) -> dict | None:
    for s in all_sources():
        if s["id"] == source_id:
            return s
    return None


def find_by_domain(domain: str) -> dict | None:
    """Look up a curated source by hostname (subdomains count)."""
    host = (domain or "").lower().strip()
    host = host.removeprefix("www.")
    for s in all_sources():
        reg = s["domain"].lower().removeprefix("www.")
        if host == reg or host.endswith("." + reg):
            return s
    return None


def classify_url(url: str) -> dict:
    """Classify a URL for display purposes.

    Returns {classification, source?} where classification is one of:
      verified_official — in the curated registry and verified=true, status current
      registered_official — in the registry but not verified / outdated / repealed
      unverified — not in the registry (even if it *looks* official, e.g. *.gov.np)
    """
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return {"classification": "unverified"}
    if parsed.scheme not in ("http", "https"):
        return {"classification": "unverified"}
    src = find_by_domain(parsed.hostname or "")
    if not src:
        # Even a *.gov.np host we have not curated is "unverified": we have
        # not checked who runs it or whether the content is current.
        return {"classification": "unverified"}
    if src.get("verified") and src.get("status") == "current":
        return {"classification": "verified_official", "source": src}
    return {"classification": "registered_official", "source": src}


def sources_for_category(category: str) -> list[dict]:
    cat = category.lower().strip()
    return [s for s in all_sources() if s.get("category") == cat]


def authority_rank(url: str) -> int:
    """Numeric authority for ranking evidence: 3 authoritative, 2 high,
    1 registered-but-not-current, 0 unverified."""
    c = classify_url(url)
    if c["classification"] == "verified_official":
        level = c["source"].get("authority_level")
        return 3 if level == "authoritative" else 2
    if c["classification"] == "registered_official":
        return 1
    return 0


def is_stale(source: dict, max_age_days: int = 365) -> bool:
    """True if the registry's verification of this source is older than
    max_age_days — a prompt to re-verify, not a claim about the content."""
    verified = source.get("verified_date")
    if not verified:
        return True
    try:
        d = datetime.strptime(verified, "%Y-%m-%d").date()
        return (date.today() - d).days > max_age_days
    except ValueError:
        return True


def public_view(source: dict) -> dict:
    """Fields safe to expose via the API (no internal notes)."""
    return {
        "id": source.get("id"),
        "organization": source.get("organization"),
        "domain": source.get("domain"),
        "url": source.get("url"),
        "title": source.get("title"),
        "category": source.get("category"),
        "source_type": source.get("source_type"),
        "authority_level": source.get("authority_level"),
        "verified": source.get("verified"),
        "status": source.get("status"),
    }
