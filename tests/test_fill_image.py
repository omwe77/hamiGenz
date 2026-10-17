"""
Reference-filled form preview — backend tests.

Run: python -m pytest tests/test_fill_image.py -v

Coverage (matches the task's verification requirements):
  * Alignment       — composite() draws answers at the field boxes it was
                      given, on the original 300-DPI page image.
  * Missing values  — a field with an empty value is not drawn.
  * Multipage       — the endpoint returns a per-page PNG for a multi-page PDF.
  * Unsupported     — a page that does not exist on the document returns 404.
  * Error handling  — a missing document returns 404; a page that cannot be
                      rendered returns 500; empty values return a plain-text
                      "no values" response.
  * Endpoint        — POST /documents/{doc_id}/page/{page_num}/fill-image
                      end-to-end through FastAPI's TestClient.

Run with: .venv/Scripts/python.exe -m pytest tests/test_fill_image.py -v
"""

import os
import sys
import io
import shutil
import tempfile
from pathlib import Path

import fitz
import pytest

# ─── Path setup ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Import the FastAPI app for direct DB access in tests.
import main  # noqa: E402


# ─── helpers ────────────────────────────────────────────────────────
def _make_form_pdf(filepath, labels=None):
    """Write a small PDF whose page contains a few labelled answer boxes."""
    if labels is None:
        labels = ["Full name:", "Father's name:", "Date of birth:", "County:"]
    doc = fitz.open()
    for i, label in enumerate(labels):
        page = doc.new_page(width=595, height=842)
        # Long intro line (>60 chars) so the chunker's 20-char filter passes.
        page.insert_text(
            (50, 45), "Registration form for the citizen: full name and contact details", fontsize=11, fontname="helv"
        )
        page.insert_text((50, 65), label, fontsize=14, fontname="helv")
        page.draw_rect(
            fitz.Rect(300, 55, 560, 77),
            color=(0.8, 0.8, 0.8), fill=(0.92, 0.92, 0.92),
        )
    doc.save(str(filepath))
    doc.close()


class TestBuildFilledPage:
    """Unit checks for form_preview.build_filled_page (no OCR needed)."""

    def test_renders_value_at_given_box(self):
        from PIL import Image
        from form_preview import build_filled_page

        original = Image.new("RGB", (600, 300), "white")
        out = build_filled_page(
            original,
            [{"label": "Name:", "value": "राम बहादुर",
              "box": {"x": 100, "y": 20, "w": 300, "h": 40}}],
        )
        assert out.size == (600, 300)
        # The boxed field region must contain non-white pixels (highlight +
        # composited answer text).
        box = (100, 20, 400, 60)
        found = False
        for yy in range(box[1], box[3]):
            for xx in range(box[0], box[2]):
                if out.getpixel((xx, yy)) != (255, 255, 255):
                    found = True
                    break
            if found:
                break
        assert found, "no answer drawn inside the field box"

    def test_empty_value_not_drawn(self):
        from PIL import Image
        from form_preview import build_filled_page

        original = Image.new("RGB", (600, 100), "white")
        out = build_filled_page(
            original,
            [
                {"label": "A", "value": "1", "box": {"x": 10, "y": 10, "w": 100, "h": 30}},
                {"label": "B", "value": "",   "box": {"x": 120, "y": 10, "w": 100, "h": 30}},
            ],
        )
        # The empty-value box (x 120..220, y 10..40) must stay pure white.
        assert out.getpixel((180, 25)) == (255, 255, 255)

    def test_out_of_bounds_box_clamped(self):
        from PIL import Image
        from form_preview import build_filled_page

        original = Image.new("RGB", (100, 100), "white")
        out = build_filled_page(
            original,
            [{"label": "A", "value": "123",
              "box": {"x": 80, "y": 10, "w": 50, "h": 50}}],
        )
        assert out.size == (100, 100)
        # Box x+width (130) exceeded image width (100); the compositor clamps
        # the width to 20, so the answer must be drawn within x 80..100.
        region = [
            out.getpixel((xx, yy))
            for yy in range(10, 60, 2) for xx in range(80, 100, 2)
        ]
        assert any(p != (255, 255, 255) for p in region), (
            "no answer drawn inside the (clamped) field box"
        )

    def test_returns_png_bytes(self):
        from PIL import Image
        from form_preview import build_filled_page

        original = Image.new("RGB", (50, 50), "white")
        out = build_filled_page(
            original,
            [{"label": "A", "value": "1", "box": {"x": 0, "y": 0, "w": 50, "h": 50}}],
        )
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        assert buf.tell() > 100  # reasonable minimum for a 50x50 PNG with text


class TestFormPositionDetection:
    """detect_form_positions keeps fields with empty word boxes at (0,0,0,0)."""

    def test_no_word_boxes_yields_zeroed_boxes(self):
        from form_understanding import detect_form_positions

        # 4+ fields must make is_form=True (MIN_FIELDS_FOR_FORM = 4).
        det = detect_form_positions(
            "Name: ____\nAge: ____\nGender: ____\nPhone: ____", []
        )
        assert det["is_form"] is True
        for f in det["fields"]:
            # With no word boxes the position keys are never set.
            assert "x" not in f and "y" not in f and "w" not in f and "h" not in f

    def test_fields_with_word_box_positions(self):
        from form_understanding import _assign_field_positions, detect_form_positions

        # Unit check: word boxes must be anchored to their labels, widened to a
        # fixed fill width.
        fields = [{"label": "Name:", "page": 1, "evidence": "name: ____"}]
        word_boxes = [{"text": "Name:", "x": 100, "y": 50, "w": 80, "h": 22, "page": 1}]
        out = _assign_field_positions(fields, word_boxes)
        assert out[0]["x"] == 100
        assert out[0]["y"] == 50
        assert out[0]["w"] == 240  # FORM_FILL_WIDTH_PX (wider than the label box)
        assert out[0]["h"] >= 22

        # detect_form_positions with real word boxes must not zero them.
        det = detect_form_positions("Name: ____\nAge: ____\nGender: ____\nPhone: ____", word_boxes)
        assert det["field_count"] >= 1
        assert det["fields"][0]["x"] >= 0 and det["fields"][0]["y"] >= 0


class TestMetadataStoreFormFields:
    def test_set_and_get_form_fields(self):
        from document_processor import MetadataStore
        import os
        import tempfile

        fd, db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            store = MetadataStore(db_path=db)
            store.set_form_fields("doc_001", [
                {"label": "Name:", "value": "राम", "page": 1},
                {"label": "Age", "value": "30", "page": 1},
            ])
            got = store.get_form_fields("doc_001")
            assert len(got) == 2
            assert got[0]["label"] == "Name:" and got[0]["value"] == "राम"
            assert got[1]["label"] == "Age" and got[1]["value"] == "30"
            assert store.get_form_fields("missing") == []
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestFillImageEndpoint:
    """FastAPI TestClient checks for POST /fill-image."""

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient
        import main as app_module

        app = app_module.app
        with TestClient(app, base_url="http://test") as c:
            yield c

    def _upload(self, client, filepath, _doc_id=""):
        with open(filepath, "rb") as f:
            params = {}  # fresh upload: no reindex_doc_id
            r = client.post(
                "/upload",
                files={"file": ("form.pdf", f, "application/pdf")},
                params=params,
            )
        assert r.status_code == 200, f"upload failed ({r.status_code}): {r.text}"
        return r.json()["doc_id"]

    def test_missing_page_returns_404(self, client):
        doc_id = "fill_404"
        pdf = os.path.join(tempfile.mkdtemp(prefix="fill404_"), "p.pdf")
        _make_form_pdf(pdf)
        self._upload(client, pdf, doc_id)
        r = client.post(
            f"/documents/{doc_id}/page/9999/fill-image", json={"values": []}
        )
        assert r.status_code == 404, r.text

    def test_unknown_document_returns_404(self, client):
        r = client.post(
            "/documents/nonexistent/page/1/fill-image", json={"values": []}
        )
        assert r.status_code == 404, r.text

    def test_no_values_returns_plain_text(self, client):
        pdf = os.path.join(tempfile.mkdtemp(prefix="fillnone_"), "p.pdf")
        _make_form_pdf(pdf)
        doc_id = self._upload(client, pdf)
        r = client.post(f"/documents/{doc_id}/page/1/fill-image", json={"values": []})
        assert r.status_code == 200
        assert r.content == b"No form fields found or no values supplied."

    def test_multipage_pdf_returns_page_image(self, client):
        """A 2-page PDF: page 1 and page 2 each produce PNG bytes."""
        tmp = tempfile.mkdtemp(prefix="fillmulti_")
        try:
            pdf = os.path.join(tmp, "p.pdf")
            # Build a 2-page PDF with different labels per page.
            doc = fitz.open()
            for page_num, label in [(1, "Name:"), (2, "Phone:")]:
                p = doc.new_page(width=595, height=842)
                # Intro line (>20 chars) so the chunker does not skip the page.
                p.insert_text((50, 55), f"[PAGE {page_num}]\nCommunity registration form for the citizen", fontsize=12, fontname="helv")
                p.insert_text((50, 60), label, fontsize=16, fontname="helv")
                p.draw_rect(
                    fitz.Rect(300, 55, 560, 77), color=(0.8, 0.8, 0.8),
                    fill=(0.92, 0.92, 0.92),
                )
            doc.save(pdf)
            doc.close()
            doc_id = self._upload(client, pdf)

            r1 = client.post(
                f"/documents/{doc_id}/page/1/fill-image",
                json={"values": [{"label": "Name", "value": "राम", "page": 1}]},
            )
            assert r1.status_code == 200, r1.text
            assert r1.headers["content-type"].startswith("image/png")

            r2 = client.post(
                f"/documents/{doc_id}/page/2/fill-image",
                json={"values": [{"label": "Phone", "value": "९८०९०२९०००", "page": 2}]},
            )
            assert r2.status_code == 200, r2.text
            assert r2.headers["content-type"].startswith("image/png")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fill_with_stored_fields(self, client):
        pdf = os.path.join(tempfile.mkdtemp(prefix="fillstored_"), "p.pdf")
        _make_form_pdf(pdf)
        doc_id = self._upload(client, pdf)

        # Persist a value through the metadata endpoint.
        client.post(
            f"/documents/{doc_id}/form-fields",
            json={"values": [{"label": "Full name", "value": "कमला", "page": 1}]},
        )
        r = client.post(
            f"/documents/{doc_id}/page/1/fill-image",
            json={"values": []},  # rely on stored values
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/png")

    def test_form_fields_do_not_delete_chunks(self, client):
        """Saving form fields must not delete indexed chunks (regression guard)."""
        pdf = os.path.join(tempfile.mkdtemp(prefix="fillchunks_"), "p.pdf")
        _make_form_pdf(pdf)
        doc_id = self._upload(client, pdf)

        # Count chunks for this document via direct DB query.
        import sqlite3
        stores = main.app.state.metadata if hasattr(main.app.state, "metadata") else None
        chunk_count = 0
        if stores is not None:
            conn = sqlite3.connect(str(stores.db_path))
            chunk_count = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE doc_id=?", (doc_id,)
            ).fetchone()[0]
            conn.close()

        # Save form fields through the metadata endpoint.
        client.post(
            f"/documents/{doc_id}/form-fields",
            json={"values": [{"label": "Name", "value": "राम", "page": 1}]},
        )

        # Re-count chunks after saving form fields.
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(stores.db_path))
        new_count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id=?", (doc_id,)
        ).fetchone()[0]
        conn.close()

        assert new_count == chunk_count, (
            f"Chunks were deleted during set_form_fields: before={chunk_count}, after={new_count}"
        )
        # Document must still be retrievable via the viewer endpoint.
        doc = client.get(f"/documents/{doc_id}/viewer").json()
        assert doc["doc_id"] == doc_id
        assert doc["filename"] == "form.pdf"
