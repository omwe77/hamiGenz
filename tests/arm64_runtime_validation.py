"""
hamiGenZ — Native ARM64 Runtime Validation Suite (Task 4.3.8.2)

Executed inside the linux/arm64 Docker container built on ubuntu-24.04-arm runner.
Validates architecture, dependencies, PyTorch CPU, SentenceTransformers, FAISS,
SQLite, Tesseract (eng+nep), and records memory/timing metrics using pure standard library.
"""

import os
import sys
import time
import platform
import subprocess
import resource
from pathlib import Path


def get_memory_info() -> dict:
    """Return current process peak resident memory info using pure Linux standard interfaces."""
    # 1. resource.getrusage: on Linux ru_maxrss is in kilobytes
    usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    ru_maxrss_mb = usage_kb / 1024.0

    # 2. Read /proc/self/status for VmRSS and VmHWM if available
    vm_rss_mb = None
    vm_hwm_mb = None
    status_path = Path("/proc/self/status")
    if status_path.is_file():
        try:
            for line in status_path.read_text().splitlines():
                if line.startswith("VmHWM:"):
                    vm_hwm_mb = float(line.split()[1]) / 1024.0
                elif line.startswith("VmRSS:"):
                    vm_rss_mb = float(line.split()[1]) / 1024.0
        except Exception:
            pass

    return {
        "ru_maxrss_mb": ru_maxrss_mb,
        "vm_rss_mb": vm_rss_mb or ru_maxrss_mb,
        "vm_hwm_mb": vm_hwm_mb or ru_maxrss_mb,
    }


def log_header(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def test_1_architecture():
    log_header("1. Verify Python & Machine Architecture is aarch64")
    machine = platform.machine()
    proc = platform.processor()
    system = platform.system()
    py_ver = sys.version
    print(f"System: {system}, Machine: {machine}, Processor: {proc}")
    print(f"Python Version: {py_ver}")
    assert machine in ("aarch64", "arm64"), f"Expected aarch64/arm64, got '{machine}'"
    print(">>> PASS: Architecture verified as native aarch64.")


def test_2_pip_check():
    log_header("2. Run pip check for Dependency Conflicts")
    res = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    print("pip check output:")
    print(res.stdout or "(empty)")
    if res.stderr:
        print("pip check stderr:", res.stderr)
    assert res.returncode == 0, f"pip check failed with exit code {res.returncode}:\n{res.stdout}\n{res.stderr}"
    print(">>> PASS: No broken requirements found.")


def test_3_dependency_imports():
    log_header("3. Import Core Dependencies")
    deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("torch", "PyTorch"),
        ("sentence_transformers", "SentenceTransformers"),
        ("faiss", "FAISS CPU"),
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
        ("fitz", "PyMuPDF"),
        ("PIL.Image", "Pillow"),
        ("pdfplumber", "pdfplumber"),
        ("pytesseract", "pytesseract"),
        ("google.genai", "Google GenAI SDK"),
    ]
    for mod_name, label in deps:
        t0 = time.perf_counter()
        mod = __import__(mod_name, fromlist=["*"])
        dt = (time.perf_counter() - t0) * 1000
        ver = getattr(mod, "__version__", "N/A")
        print(f"  - {label} ({mod_name} {ver}) imported in {dt:.1f}ms")
    print(">>> PASS: All 13 core packages imported cleanly.")


def test_4_pytorch_cpu_tensor():
    log_header("4. PyTorch CPU Tensor Operations")
    import torch

    device = torch.device("cpu")
    print(f"PyTorch Version: {torch.__version__}, Device: {device}")
    a = torch.tensor([[1.0, 2.0], [3.0, 4.0]], device=device)
    b = torch.tensor([[5.0, 6.0], [7.0, 8.0]], device=device)
    c = torch.matmul(a, b)
    expected = torch.tensor([[19.0, 22.0], [43.0, 50.0]], device=device)
    assert torch.allclose(c, expected), f"Matrix multiply mismatch:\n{c}\nvs\n{expected}"
    print(f"Matrix multiply result:\n{c.tolist()}")
    print(">>> PASS: PyTorch CPU tensor operations function accurately.")


def test_5_sentence_transformer_embedding():
    log_header("5. SentenceTransformers Multilingual Embedding on Nepali Text")
    from sentence_transformers import SentenceTransformer
    import numpy as np

    mem_before = get_memory_info()
    model_name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    cache_dir = os.getenv("HF_HOME", "/app/backend/data/huggingface")
    print(f"Embedding model: '{model_name}'")
    print(f"Cache location (HF_HOME): '{cache_dir}'")

    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    load_duration = time.perf_counter() - t0
    mem_after_load = get_memory_info()

    nepali_sentence = "नेपालको नागरिकता र राहदानी सम्बन्धी आधिकारिक सरकारी प्रक्रिया।"
    t1 = time.perf_counter()
    # Generate raw unnormalized embeddings first
    raw_emb = model.encode([nepali_sentence], convert_to_numpy=True, normalize_embeddings=False)
    infer_duration = time.perf_counter() - t1
    mem_after_infer = get_memory_info()

    assert raw_emb.shape == (1, 384), f"Expected shape (1, 384), got {raw_emb.shape}"
    assert raw_emb.dtype == np.float32, f"Expected float32, got {raw_emb.dtype}"
    raw_norm = float(np.linalg.norm(raw_emb[0]))
    print(f"Raw embedding shape: {raw_emb.shape}, Raw L2 norm: {raw_norm:.5f}")

    # Explicit vector normalization step (required check)
    emb_normalized = raw_emb / np.linalg.norm(raw_emb, axis=1, keepdims=True)
    norm_after = float(np.linalg.norm(emb_normalized[0]))
    print(f"Explicitly normalized L2 norm: {norm_after:.5f}")
    assert np.isclose(norm_after, 1.0, atol=1e-5), f"Expected unit norm 1.0 after normalization, got {norm_after}"

    print(f"Model load duration: {load_duration:.2f}s")
    print(f"Nepali embedding duration: {infer_duration:.4f}s")
    print(f"Memory RSS before load: {mem_before['vm_rss_mb']:.1f} MB")
    print(f"Memory RSS after model load: {mem_after_load['vm_rss_mb']:.1f} MB (+{mem_after_load['vm_rss_mb'] - mem_before['vm_rss_mb']:.1f} MB)")
    print(f"Peak memory (VmHWM): {mem_after_infer['vm_hwm_mb']:.1f} MB")
    print(">>> PASS: SentenceTransformers correctly loads model and embeds Nepali text on ARM64.")


def test_6_faiss_operations():
    log_header("6. FAISS Index Creation, Serialization, and Search")
    import faiss
    import numpy as np
    import tempfile

    dim = 384
    index = faiss.IndexFlatIP(dim)
    print(f"Created IndexFlatIP(dimension={dim})")

    # Add 10 random unit-norm vectors
    rng = np.random.default_rng(42)
    raw_vecs = rng.normal(size=(10, dim)).astype(np.float32)
    faiss.normalize_L2(raw_vecs)
    index.add(raw_vecs)
    assert index.ntotal == 10, f"Expected 10 vectors, got {index.ntotal}"

    with tempfile.TemporaryDirectory() as tmpdir:
        idx_file = Path(tmpdir) / "test_doc.faiss"
        faiss.write_index(index, str(idx_file))
        assert idx_file.exists() and idx_file.stat().st_size > 0
        print(f"Serialized index to disk: {idx_file.stat().st_size} bytes")

        reloaded = faiss.read_index(str(idx_file))
        assert reloaded.ntotal == 10

        # Query with vector 0 — top hit must be index 0 with score ~1.0
        query = raw_vecs[:1]
        scores, indices = reloaded.search(query, k=3)
        print(f"Top 3 match indices: {indices[0].tolist()}, scores: {scores[0].tolist()}")
        assert indices[0][0] == 0, f"Expected top match 0, got {indices[0][0]}"
        assert np.isclose(scores[0][0], 1.0, atol=1e-5), f"Expected score ~1.0, got {scores[0][0]}"

    print(">>> PASS: FAISS vector indexing, file I/O, and similarity search passed.")


def test_7_sqlite_persistence():
    log_header("7. SQLite WAL Mode Table Operations")
    import sqlite3
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "hamigenz_test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                page_count INTEGER,
                language_hint TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?);",
            ("doc_001", "नागरिकता_प्रमाणपत्र.pdf", 2, "nepali"),
        )
        conn.commit()

        cur = conn.execute("SELECT doc_id, filename, language_hint FROM documents WHERE doc_id = 'doc_001';")
        row = cur.fetchone()
        assert row == ("doc_001", "नागरिकता_प्रमाणपत्र.pdf", "nepali"), f"Unexpected row: {row}"
        conn.close()

    print(">>> PASS: SQLite WAL mode table operations and Unicode storage passed.")


def test_8_tesseract_languages():
    log_header("8. Tesseract OCR Language Support (eng + nep)")
    import pytesseract

    langs = pytesseract.get_languages()
    print(f"Detected Tesseract languages: {langs}")
    assert "eng" in langs, f"'eng' language model missing from {langs}"
    assert "nep" in langs, f"'nep' (Nepali) language model missing from {langs}"
    print(">>> PASS: Both English ('eng') and Nepali ('nep') trained models verified.")


def main():
    print("=" * 70)
    print("hamiGenZ ARM64 Container Runtime Test Suite")
    print("=" * 70)
    start_time = time.perf_counter()

    test_1_architecture()
    test_2_pip_check()
    test_3_dependency_imports()
    test_4_pytorch_cpu_tensor()
    test_5_sentence_transformer_embedding()
    test_6_faiss_operations()
    test_7_sqlite_persistence()
    test_8_tesseract_languages()

    total_time = time.perf_counter() - start_time
    mem_final = get_memory_info()
    print("\n" + "=" * 70)
    print(f"ALL IN-CONTAINER TESTS PASSED in {total_time:.2f}s | Peak RSS (VmHWM): {mem_final['vm_hwm_mb']:.1f} MB")
    print("=" * 70)


if __name__ == "__main__":
    main()
