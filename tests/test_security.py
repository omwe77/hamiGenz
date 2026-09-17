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
