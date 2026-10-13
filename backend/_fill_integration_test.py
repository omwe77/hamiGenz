"""Integration test: fill-image endpoint (end-to-end) + failure handling."""
import os
import sys
import io
import traceback
import tempfile
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

# Project venv is used so backend imports exist in this interpreter.
import _fill_pipeline_test  # noqa: F401 (traverses backend as a package import)

from main import app, UPLOAD_DIR
from document_processor import MetadataStore

# Keep the test hermetic: point the app's data paths at a throwaway dir so the
# real `data/hamigenz.db` and `data/uploads` are never touched by the suite.
_TMP = tempfile.TemporaryDirectory()
_TMP_PATH = Path(_TMP.name)
import main as _main
_main.DB_PATH = _TMP_PATH / "test.db"
_main.UPLOAD_DIR = _TMP_PATH / "uploads"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_fill_image_flow():
    with TestClient(app) as client:
        meta = app.state.metadata
        assert meta is not None
        print("[ok] metadata store initialised")

        # Insert a real document row so the endpoint can open it. The filepath is
        # placed inside the temp `UPLOAD_DIR` so the endpoint's path check passes.
        import shutil
        fixture = os.path.join(BASE, "data", "uploads", "11e2e975.pdf")
        assert os.path.exists(fixture), "upload fixture missing"
        os.makedirs(_TMP_PATH / "uploads", exist_ok=True)
        mp = os.path.join(str(_TMP_PATH / "uploads"), "11e2e975.pdf")
        shutil.copy2(fixture, mp)
        meta.add_document("d1", "11e2e975.pdf", mp, 6, language_hint="nep")
        assert meta.get_document("d1") is not None
        print("[ok] inserted document d1")

        # Missing document -> 404.
        r = client.post("/documents/d999/page/1/fill-image", json={"values": [{"label": "Name:", "value": "X"}]})
        assert r.status_code == 404, f"expected 404, got {r.status_code}"
        print("[ok] 404 on missing doc")

        # Missing page -> 404.
        r = client.post("/documents/d1/page/999/fill-image", json={"values": [{"label": "Name:", "value": "X"}]})
        assert r.status_code == 404, f"expected 404, got {r.status_code}"
        print("[ok] 404 on missing page")

        # Failure handling: missing file -> 500; out-of-upload-dir path -> 403.
        meta.add_document("d2", "broken.pdf", "/no/such/path.pdf", 1)
        r = client.post("/documents/d2/page/1/fill-image",
                        json={"values": [{"label": "Name:", "value": "X"}]})
        assert r.status_code == 500, f"expected 500, got {r.status_code}"
        print(f"[ok] 500 on missing file (got {r.status_code})")

        meta.add_document("d3", "escaped.pdf", "/etc/passwd", 1)
        r = client.post("/documents/d3/page/1/fill-image",
                        json={"values": [{"label": "Name:", "value": "X"}]})
        assert r.status_code == 403, f"expected 403, got {r.status_code}"
        print(f"[ok] 403 on out-of-upload-dir path (got {r.status_code})")

        # Fill with values -> 200 + PNG.
        r = client.post("/documents/d1/page/1/fill-image",
                        json={"values": [{"label": "Name:", "value": "राम बहादुर"},
                                         {"label": "Surname:", "value": "तामाङ"}]})
        assert r.status_code == 200, f"expected 200, got {r.status_code}"
        assert r.headers["content-type"].startswith("image/png")
        png = r.content
        assert len(png) > 4000, "fill-image response too small"
        print(f"[ok] fill-image 200, {len(png)} bytes, type={r.headers['content-type']}")

        # Empty values -> 200 with the original page image (no text drawn).
        r2 = client.post("/documents/d1/page/1/fill-image", json={"values": []})
        assert r2.status_code == 200
        assert len(r2.content) > 4000
        print(f"[ok] empty values -> 200, {len(r2.content)} bytes")

        # Persistence: set_form_fields then read back.
        r = client.post("/documents/d1/form-fields",
                        json={"values": [{"label": "Name:", "value": "पेशावर", "page": 1}]})
        assert r.status_code == 200
        back = client.get("/documents/d1/form-fields")
        assert back.status_code == 200
        print(f"[ok] form-fields set(200) + get({back.status_code})")

    print("FILL-IMAGE-INTEGRATION: OK")
    return True


if __name__ == "__main__":
    try:
        test_fill_image_flow()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
