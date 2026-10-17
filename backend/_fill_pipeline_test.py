"""Test the reference-filled form preview pipeline (synthetic + real PDF)."""
import os
import sys
import io
import shutil
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont

# ── 1. Synthetic form image with labeled blank fields ──────────────────
def make_form_image(path):
    """Render a tiny form PDF with labeled blank fields."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    labels = ["Name:", "Surname:", "Nationality:", "Date of birth:"]
    y = 60
    for lab in labels:
        page.draw_rect(fitz.Rect(30, y - 14, 220, y + 4), color=(0.85, 0.85, 0.85), fill=(0.88, 0.88, 0.9))
        page.insert_text((40, y + 2), lab, fontsize=14, fontname="helv")
        y += 80
    doc.save(path)
    doc.close()

def test_compositing():
    import fitz
    import tempfile
    from PIL import Image
    from form_preview import build_filled_page
    from document_processor import DocumentProcessor

    tmpdir = tempfile.mkdtemp(prefix="form_test_")
    tmp = os.path.join(tmpdir, "form_synth.pdf")
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    labels = ["Name:", "Surname:", "Nationality:", "Date of birth:"]
    y = 60
    for lab in labels:
        page.draw_rect(fitz.Rect(30, y - 14, 220, y + 4), color=(0.85, 0.85, 0.85), fill=(0.88, 0.88, 0.9))
        page.insert_text((40, y + 2), lab, fontsize=14, fontname="helv")
        y += 80
    doc.save(tmp)
    doc.close()

    # Render original at 300 DPI (matches detection coordinates).
    pil = DocumentProcessor(upload_dir=tmpdir)._render_page_pil(tmp, 1, dpi=300)
    assert pil is not None, "render failed"

    # Synthetic field values at 300 DPI boxes (label box + fill width).
    field_values = [
        {"label": "Name:", "value": "राम बहादुर", "box": {"x": 60, "y": 60, "w": 260, "h": 40}},
        {"label": "Surname:", "value": "तामाङ", "box": {"x": 60, "y": 140, "w": 260, "h": 40}},
    ]
    out = build_filled_page(pil, field_values, highlight_color=(245, 158, 11), text_color=(146, 72, 17))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    assert buf.tell() > 1000, "filled image too small"
    print("[ok] compositing produced a PNG of", out.size, "bytes:", buf.tell())
    shutil.rmtree(tmpdir, ignore_errors=True)
    return True

def test_detect_on_real_pdf():
    import fitz
    from form_understanding import detect_form_positions
    up = '../data/uploads'
    dp = None
    import importlib
    # use same DocumentProcessor as test_compositing would
    if 'dp' not in globals():
        from document_processor import DocumentProcessor
        dp = DocumentProcessor(upload_dir=up)
    path = os.path.join(up, '11e2e975.pdf')
    pages = dp.extract_text(path)
    p = pages[0]
    wb = dp._tesseract_word_boxes(path, p['page_num'])
    det = detect_form_positions(p['text'], wb)
    print("[ok] real-pdf detection is_form:", det['is_form'], "fields:", det['field_count'], "boxes:", len(wb))
    return True

if __name__ == '__main__':
    try:
        test_compositing()
        test_detect_on_real_pdf()
        print("PIPELINE-UNIT: OK")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
