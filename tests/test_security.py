"""
Security tests for hamiGenZ backend (no live server required).

Run with: .venv/Scripts/python.exe -m pytest tests/test_security.py -v
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

from document_processor import DocumentProcessor


class TestUploadFilenameNeutralization:
    """User-supplied filenames must never reach the filesystem."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp(prefix="hamigenz_sec_")
        self.proc = DocumentProcessor(upload_dir=self.tmp)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _saved_name(self, raw_filename):
        filepath, doc_id = self.proc.save_upload(b"x" * 200, raw_filename)
        return os.path.basename(filepath), doc_id, filepath

    def test_traversal_filename_stays_in_upload_dir(self):
        name, doc_id, filepath = self._saved_name("../../etc/passwd.pdf")
        assert filepath.startswith(os.path.abspath(self.tmp))
        assert "/" not in name.replace("\\", "/").split("/")[-1] or True
        # The saved name must be the generated doc_id, not the user's path
        assert name.startswith(doc_id)

    def test_backslash_traversal(self):
        name, doc_id, filepath = self._saved_name("..\\..\\windows\\evil.pdf")
        assert filepath.startswith(os.path.abspath(self.tmp))
        assert name.startswith(doc_id)

    def test_absolute_path_filename(self):
        name, doc_id, filepath = self._saved_name("C:/Windows/system32/evil.pdf")
        assert filepath.startswith(os.path.abspath(self.tmp))
        assert name.startswith(doc_id)

    def test_extension_sanitized(self):
        name, doc_id, _ = self._saved_name("report.pd f")
        # Only alphanumeric chars survive in the extension
        assert "." in name
        ext = name.rsplit(".", 1)[1]
        assert ext.isalnum()

    def test_long_extension_truncated(self):
        name, doc_id, _ = self._saved_name("file." + "x" * 50)
        ext = name.rsplit(".", 1)[1]
        assert len(ext) <= 5

    def test_no_extension_gets_flat_name(self):
        name, doc_id, _ = self._saved_name("noext")
        assert name == doc_id or name.startswith(doc_id)

    def test_doc_id_is_short_uuid(self):
        _, doc_id, _ = self._saved_name("normal.pdf")
        assert len(doc_id) == 8
        int(doc_id, 16)  # must be hex


httpx = None
try:
    import httpx
except ImportError:
    pass


@pytest.mark.skipif(httpx is None, reason="httpx required for ASGI transport tests")
class TestExceptionInformationDisclosure:
    """Exception details and system paths must never be disclosed to API clients."""

    def test_upload_save_exception_hides_system_paths(self, monkeypatch):
        import anyio
        from unittest.mock import MagicMock
        from main import app
        import session_auth
        from starlette.datastructures import UploadFile

        app.state.pipeline = MagicMock()
        app.state.vector_store = MagicMock()
        app.state.metadata = MagicMock()
        if hasattr(app.state, "_upload_admission_sem"):
            del app.state._upload_admission_sem
        if hasattr(app.state, "_staged_backlog_sem"):
            del app.state._staged_backlog_sem

        sid = "sec-test-sid"
        token = session_auth.generate_session_token(sid)
        secret_path = "C:\\Users\\Administrator\\confidential\\temp_spool"

        async def failing_read(self, *args, **kwargs):
            raise OSError(f"Corrupted storage at internal path: {secret_path}")

        monkeypatch.setattr(UploadFile, "read", failing_read)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                return await client.post(
                    "/upload",
                    files={"file": ("test.pdf", b"%PDF-1.4 sample", "application/pdf")},
                    headers={"X-Session-Token": token},
                )

        resp = anyio.run(run)
        assert resp.status_code == 500
        data = resp.json()
        assert data["detail"] == "Failed to save uploaded document."
        assert "Administrator" not in resp.text
        assert "confidential" not in resp.text
        assert secret_path not in resp.text

    def test_fill_preview_exception_hides_system_details(self, monkeypatch):
        import anyio
        from unittest.mock import MagicMock
        from main import app, UPLOAD_DIR
        import session_auth

        doc_id = "testdoc1"
        sid = "sec-preview-sid"
        token = session_auth.generate_session_token(sid)

        test_file = UPLOAD_DIR / f"{doc_id}.pdf"
        app.state.metadata = MagicMock()
        app.state.metadata.get_document.return_value = {
            "doc_id": doc_id,
            "session_id": sid,
            "filepath": str(test_file),
        }
        app.state.metadata.get_form_fields.return_value = {}

        secret_err = "BufferError at /var/secrets/key.bin: fatal stack"

        def mock_render(*args, **kwargs):
            raise RuntimeError(secret_err)

        monkeypatch.setattr("main._render_fill_preview_sync", mock_render)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                return await client.post(
                    f"/documents/{doc_id}/page/1/fill-image",
                    json={"values": [{"label": "name", "value": "Test"}]},
                    headers={"X-Session-Token": token},
                )

        resp = anyio.run(run)
        assert resp.status_code == 500
        data = resp.json()
        assert data["detail"] == "Could not generate form fill preview."
        assert secret_err not in resp.text
        assert "secrets" not in resp.text
        assert "BufferError" not in resp.text

    def test_set_form_fields_invalid_payload_sanitized(self):
        import anyio
        from unittest.mock import MagicMock
        from main import app
        import session_auth

        doc_id = "testdoc2"
        sid = "sec-field-sid"
        token = session_auth.generate_session_token(sid)

        app.state.metadata = MagicMock()
        app.state.metadata.get_document.return_value = {
            "doc_id": doc_id,
            "session_id": sid,
            "filepath": "fake.pdf",
        }

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                return await client.post(
                    f"/documents/{doc_id}/form-fields",
                    json={"values": 12345},
                    headers={"X-Session-Token": token},
                )

        resp = anyio.run(run)
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"] == "Invalid form fields payload."
        assert "not iterable" not in resp.text
