"""Unit tests for source_registry.py — curated official source registry & URL classification."""
import os
import sys
import pytest

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from source_registry import (
    all_sources,
    get_source,
    find_by_domain,
    classify_url,
)


class TestSourceRegistry:
    def test_loads_curated_sources(self):
        sources = all_sources()
        assert len(sources) >= 5
        for s in sources:
            assert "id" in s
            assert "organization" in s
            assert "domain" in s
            assert "verified" in s

    def test_get_source_found_and_missing(self):
        sources = all_sources()
        first_id = sources[0]["id"]
        found = get_source(first_id)
        assert found is not None
        assert found["id"] == first_id

        missing = get_source("nonexistent-source-id-xyz")
        assert missing is None

    def test_find_by_domain_handles_www_and_subdomains(self):
        sources = all_sources()
        target = sources[0]
        domain = target["domain"]

        # Exact match
        found = find_by_domain(domain)
        assert found is not None
        assert found["id"] == target["id"]

        # www prefix match
        found_www = find_by_domain(f"www.{domain}")
        assert found_www is not None
        assert found_www["id"] == target["id"]


class TestClassifyUrl:
    def test_verified_official_url(self):
        sources = all_sources()
        verified_source = next((s for s in sources if s.get("verified") and s.get("status") == "current"), None)
        assert verified_source is not None

        url = f"https://{verified_source['domain']}/services/guidelines"
        res = classify_url(url)
        assert res["classification"] == "verified_official"
        assert res["source"]["id"] == verified_source["id"]

    def test_unverified_external_url(self):
        res = classify_url("https://random-commercial-site.com/nepal-docs")
        assert res["classification"] == "unverified"

    def test_invalid_scheme(self):
        assert classify_url("javascript:alert(1)")["classification"] == "unverified"
        assert classify_url("ftp://nepalpassport.gov.np")["classification"] == "unverified"