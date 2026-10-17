"""Unit tests for okf_validator.py — Open Knowledge Format v0.2 validation rules."""
import os
import sys
from pathlib import Path
import pytest

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from okf_validator import (
    _split_frontmatter,
    _check_stale_after,
    validate_bundle,
    _TYPE_PAT,
)


class TestSplitFrontmatter:
    def test_extracts_frontmatter_and_body(self):
        doc = "---\ntitle: Test\ntype: Doc\n---\n# Body Content"
        fm, body = _split_frontmatter(doc)
        assert fm is not None
        assert "title: Test" in fm
        assert body.strip() == "# Body Content"

    def test_missing_frontmatter(self):
        doc = "# Just a markdown file"
        fm, body = _split_frontmatter(doc)
        assert fm is None
        assert body == doc


class TestTypePattern:
    def test_valid_types(self):
        for t in ["DocumentType", "FormGuide", "OCRRule", "passport-v1", "Field_Definition"]:
            assert _TYPE_PAT.match(t) is not None

    def test_invalid_types(self):
        for t in ["123startWithDigit", "_underscoreStart", "type with spaces"]:
            assert _TYPE_PAT.match(t) is None


class TestCheckStaleAfter:
    def test_valid_iso_date(self):
        errs = []
        _check_stale_after("2026-12-31", errs)
        assert len(errs) == 0

    def test_invalid_date_format(self):
        errs = []
        _check_stale_after("31/12/2026", errs)
        assert len(errs) > 0


class TestLiveOkfBundle:
    def test_repo_okf_bundle_conforms_to_spec(self):
        # Finds data/okf from project root
        repo_root = Path(__file__).resolve().parent.parent.parent
        okf_dir = repo_root / "data" / "okf"
        if okf_dir.exists():
            valid, errors = validate_bundle(okf_dir)
            assert valid is True, f"OKF validation errors: {errors}"
            assert len(errors) == 0