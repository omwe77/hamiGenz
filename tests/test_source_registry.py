"""
Tests for the curated official-source registry (PR-011).

Run: .venv/Scripts/python.exe -m pytest tests/test_source_registry.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from source_registry import (
    all_sources,
    classify_url,
    find_by_domain,
    authority_rank,
    is_stale,
    public_view,
    sources_for_category,
)


class TestRegistryContent:
    def test_registry_loads(self):
        sources = all_sources()
        assert len(sources) >= 8

    def test_required_fields_present(self):
        required = {"id", "organization", "domain", "title", "category",
                    "source_type", "authority_level", "verified", "status",
                    "verified_date"}
        for s in all_sources():
            missing = required - set(s.keys())
            assert not missing, f"{s.get('id')} missing {missing}"

    def test_verified_sources_have_dates(self):
        for s in all_sources():
            if s["verified"]:
                assert s.get("verified_date"), s["id"]

    def test_all_domains_official_tlds(self):
        # Curation policy: everything in the registry must be a gov.np domain
        for s in all_sources():
            assert s["domain"].endswith("gov.np"), s["id"]

    def test_category_lookup(self):
        passport = sources_for_category("passport")
        assert len(passport) == 1
        assert passport[0]["id"] == "passport-dept"


class TestDomainLookup:
    def test_exact_domain(self):
        src = find_by_domain("nepalpassport.gov.np")
        assert src and src["id"] == "passport-dept"

    def test_www_prefix(self):
        assert find_by_domain("www.nepalpassport.gov.np")

    def test_subdomain(self):
        assert find_by_domain("apply.nepalpassport.gov.np")

    def test_unknown_domain(self):
        assert find_by_domain("totally-unrelated.example") is None


class TestUrlClassification:
    def test_curated_verified_is_verified_official(self):
        c = classify_url("https://www.nepalpassport.gov.np/fees")
        assert c["classification"] == "verified_official"
        assert c["source"]["id"] == "passport-dept"

    def test_org_np_is_NEVER_inherently_official(self):
        # The core PR-011 rule: open TLDs carry no authority
        c = classify_url("https://some-ngo.org.np/notice")
        assert c["classification"] == "unverified"

    def test_uncurated_gov_np_is_unverified(self):
        # Even a gov.np host we have not curated is unverified
        c = classify_url("https://unknown-agency.gov.np/notice")
        assert c["classification"] == "unverified"

    def test_non_http_rejected(self):
        assert classify_url("ftp://nepalpassport.gov.np")["classification"] == "unverified"
        assert classify_url("javascript:alert(1)")["classification"] == "unverified"

    def test_garbage_rejected(self):
        assert classify_url("not a url")["classification"] == "unverified"


class TestAuthorityRank:
    def test_authoritative_rank(self):
        assert authority_rank("https://www.lawcommission.gov.np/act") == 3

    def test_unverified_rank(self):
        assert authority_rank("https://random-blog.com.np/post") == 0
        assert authority_rank("https://university.edu.np") == 0


class TestFreshness:
    def test_old_verification_is_stale(self):
        src = dict(all_sources()[0])
        src["verified_date"] = "2020-01-01"
        assert is_stale(src) is True

    def test_recent_verification_not_stale(self):
        src = dict(all_sources()[0])
        src["verified_date"] = "2026-09-17"
        assert is_stale(src) is False

    def test_missing_date_is_stale(self):
        assert is_stale({"id": "x"}) is True


class TestPublicView:
    def test_no_internal_notes_exposed(self):
        src = dict(all_sources()[0])
        src["notes"] = "internal note should not leak"
        view = public_view(src)
        assert "notes" not in view
        assert view["organization"] == src["organization"]
