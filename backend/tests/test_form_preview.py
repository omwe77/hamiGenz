"""Unit tests for form_preview.py — Pillow compositing helpers.

Deliberately avoids I/O (no real PDFs, no font files required) by
stubbing PIL and fitz. Tests the pure-logic helpers cheaply.
"""
import os
import sys
import types
import pytest

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _FakeFont:
    pass


class _FakeImage:
    width = 800
    height = 600

    def copy(self):
        return _FakeImage()


class _FakeDraw:
    def __init__(self, img):
        pass

    def textbbox(self, xy, text, font=None):
        return (0, 0, len(text) * 8, 20)

    def text(self, xy, text, fill=None, font=None):
        pass


def _build_pil_stub():
    pil = types.ModuleType("PIL")

    image_mod = types.ModuleType("PIL.Image")
    image_mod.Image = _FakeImage

    draw_mod = types.ModuleType("PIL.ImageDraw")
    draw_mod.ImageDraw = _FakeDraw  # form_preview uses ImageDraw.ImageDraw as a type hint
    draw_mod.Draw = _FakeDraw

    font_mod = types.ModuleType("PIL.ImageFont")
    font_mod.FreeTypeFont = _FakeFont
    font_mod.truetype = lambda *a, **kw: (_ for _ in ()).throw(OSError("stub"))
    font_mod.load_default = lambda: _FakeFont()

    pil.Image = image_mod
    pil.ImageDraw = draw_mod
    pil.ImageFont = font_mod
    return pil, image_mod, draw_mod, font_mod


def _install_stubs():
    pil, image_mod, draw_mod, font_mod = _build_pil_stub()
    sys.modules.setdefault("PIL", pil)
    sys.modules.setdefault("PIL.Image", image_mod)
    sys.modules.setdefault("PIL.ImageDraw", draw_mod)
    sys.modules.setdefault("PIL.ImageFont", font_mod)

    fitz = types.ModuleType("fitz")
    sys.modules.setdefault("fitz", fitz)

    dp = types.ModuleType("document_processor")
    dp.DocumentProcessor = object
    sys.modules.setdefault("document_processor", dp)


_install_stubs()

import form_preview  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoadFontCache:
    def setup_method(self):
        form_preview._FONT_CACHE.clear()

    def test_cache_is_size_keyed(self):
        form_preview._load_font(12)
        form_preview._load_font(24)
        assert 12 in form_preview._FONT_CACHE
        assert 24 in form_preview._FONT_CACHE

    def test_same_size_returns_cached_object(self):
        f1 = form_preview._load_font(16)
        f2 = form_preview._load_font(16)
        assert f1 is f2

    def test_cache_populated_after_call(self):
        form_preview._load_font(18)
        assert 18 in form_preview._FONT_CACHE


class TestBuildFilledPage:
    def _img(self):
        return _FakeImage()

    def test_empty_field_values(self):
        result = form_preview.build_filled_page(self._img(), [])
        assert result is not None

    def test_skips_empty_value(self):
        fv = [{"value": "", "box": {"x": 10, "y": 10, "w": 100, "h": 30}}]
        form_preview.build_filled_page(self._img(), fv)

    def test_skips_missing_box(self):
        fv = [{"value": "Test", "box": None}]
        form_preview.build_filled_page(self._img(), fv)

    def test_clamps_negative_coordinates(self):
        fv = [{"value": "Om", "box": {"x": -50, "y": -20, "w": 80, "h": 30}}]
        form_preview.build_filled_page(self._img(), fv)

    def test_clamps_oversized_box(self):
        fv = [{"value": "Om", "box": {"x": 750, "y": 580, "w": 200, "h": 100}}]
        form_preview.build_filled_page(self._img(), fv)


class TestFitzImport:
    def test_fitz_in_module_globals(self):
        assert "fitz" in vars(form_preview), (
            "fitz is not imported in form_preview — rendered_page_pil will "
            "raise NameError at runtime"
        )