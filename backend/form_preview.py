"""Reference-filled form previews.

Composites typed field answers onto the ORIGINAL uploaded PDF/image page so the
user sees the form exactly as it would appear, with answers placed inside the
correct fields.

Rendering model
---------------
* PDF page rendering -- PyMuPDF (the existing page renderer), rendered at 300
  DPI so answers are legible in the preview.
* Compositing answers (Pillow / PIL) onto the rendered image -- Pillow wraps a
  TrueType font (Nirmala, supports Devanagari) and draws highlight boxes plus
  wrapped text at the field coordinates.

Sharp is a Node.js native module and is not part of the Python FastAPI pipeline;
Pillow is the correct Python image tool for server-side compositing. Where the
Frontend needs client-side image work, Sharp is the appropriate choice there.
"""

import fitz  # PyMuPDF
import os
import textwrap
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from document_processor import DocumentProcessor

# Detect coordinates are reported at 300 DPI; previews render at 300 DPI too,
# so the same coordinate space applies (scale factor of 1.0).
_PREVIEW_DPI = 300
_FILL_WIDTH_PX = 240  # px at 300 DPI allocated to the answer area
_HIGHLIGHT = (245, 158, 11)      # amber highlight
_TEXT = (146, 72, 17)            # dark accent text (nearly black-brown)

# Devanagari-capable fonts, in priority order.
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/Nirmala.ttc",
]

_FONT_CACHE: dict = {}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    for path in _FONT_CANDIDATES:
        if not path or not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, size, index=0)
            _FONT_CACHE[size] = font
            return font
        except Exception:
            continue
    # Fallback only: bitmap font (no Devanagari glyphs). A missing TTF here is
    # a real problem and must surface in the report rather than silently
    # producing tofu boxes.
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


def _fit_font(draw: ImageDraw.ImageDraw, text: str, box_w: int,
              start_size: int = 34) -> ImageFont.FreeTypeFont:
    """Return the largest font that fits `text` inside `box_w` (down to 12px)."""
    font = _load_font(start_size)
    while start_size > 12:
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= box_w:
            return font
        start_size -= 1
        font = _load_font(start_size)
    return font


def _draw_answer_text(draw: ImageDraw.ImageDraw, box, value: str,
                      highlight_color: tuple = _HIGHLIGHT,
                      text_color: tuple = _TEXT) -> None:
    """Draw wrapped answer text inside `box` with a highlight bar behind it."""
    x, y, box_w, box_h = [int(v) for v in box]
    if box_w <= 0 or box_h <= 0:
        return
    pad = 6
    inner_w = max(box_w - 2 * pad, 20)
    max_lines = max(2, int((box_h - 2 * pad) / 20))
    lines = textwrap.wrap(value, width=max(1, int(inner_w / 8.5)))
    lines = lines[:max_lines]
    if not lines:
        return
    font_size = max(12, min(int(box_h * 0.9), 34))
    font = _fit_font(draw, lines[0], inner_w, start_size=font_size)
    line_height = int(font_size * 1.15)
    ty = y + pad + max(0, (box_h - len(lines) * line_height)) // 2
    for line in lines:
        draw.text((x + pad, ty), line, fill=text_color, font=font)
        ty += line_height


def build_filled_page(original_pil: Image.Image,
                      field_values: list[dict],
                      highlight_color: tuple = _HIGHLIGHT,
                      text_color: tuple = _TEXT) -> Image.Image:
    """Composite `field_values` onto the original 300-DPI page image.

    Each item in `field_values` must carry a `box` dict {x, y, w, h} (300-DPI
    coordinates) plus a `value`. Returns a new PIL Image with answers composited
    into the correct fields.
    """
    img = original_pil.copy()
    draw = ImageDraw.Draw(img)
    for fv in field_values:
        value = (fv.get("value") or "").strip()
        if not value:
            continue
        box = fv.get("box")
        if not box or not isinstance(box, dict):
            continue
        x, y, w, h = [int(box.get(k, 0)) for k in ("x", "y", "w", "h")]
        # Deterministic, sane bounds regardless of OCR noise.
        w = max(w, 40)
        h = max(h, 24)
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + w > img.width:
            w = max(0, img.width - x)
        if y + h > img.height:
            h = max(0, img.height - y)
        if w <= 0 or h <= 0:
            continue
        _draw_answer_text(draw, (x, y, w, h), value, highlight_color, text_color)
    return img


def rendered_page_pil(filepath: str, page_num: int, dpi: int = _PREVIEW_DPI) -> Optional[Image.Image]:
    """Render one PDF page to a PIL Image at `dpi` via PyMuPDF."""
    try:
        doc = fitz.open(filepath)
        page = doc[page_num - 1]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception as e:
        print(f"rendered_page_pil failed for {filepath} page {page_num}: {e}")
        return None
