"""
tests/test_offline_embedding_mock.py

Regression contract for MockEmbeddingService used in offline CI runs.
Runs without TRANSFORMERS_OFFLINE / HF_HUB_OFFLINE — imports the class directly.
"""
import numpy as np
import pytest
import subprocess
import sys

from tests.conftest import MockEmbeddingService

DIM = 384
MOCK = MockEmbeddingService()


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------

def test_single_text_shape():
    out = MOCK.embed_texts(["hello"])
    assert out.shape == (1, DIM), f"Expected (1, {DIM}), got {out.shape}"


def test_multi_text_shape():
    out = MOCK.embed_texts(["a", "b", "c"])
    assert out.shape == (3, DIM)


def test_empty_batch_shape():
    out = MOCK.embed_texts([])
    assert out.shape == (0, DIM), f"Expected (0, {DIM}), got {out.shape}"


def test_embed_text_shape():
    out = MOCK.embed_text("single")
    assert out.shape == (1, DIM)


# ---------------------------------------------------------------------------
# dtype
# ---------------------------------------------------------------------------

def test_dtype_float32():
    out = MOCK.embed_texts(["dtype check"])
    assert out.dtype == np.float32, f"Expected float32, got {out.dtype}"


def test_empty_dtype_float32():
    out = MOCK.embed_texts([])
    assert out.dtype == np.float32


# ---------------------------------------------------------------------------
# Finite values (no NaN / Inf)
# ---------------------------------------------------------------------------

def test_finite_values():
    out = MOCK.embed_texts(["check finite", "another text"])
    assert np.all(np.isfinite(out)), "Output contains NaN or Inf"


# ---------------------------------------------------------------------------
# Unit L2 norm
# ---------------------------------------------------------------------------

def test_unit_l2_norm_single():
    out = MOCK.embed_texts(["normalize me"])
    norms = np.linalg.norm(out, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_unit_l2_norm_batch():
    texts = ["alpha", "beta", "gamma", "delta"]
    out = MOCK.embed_texts(texts)
    norms = np.linalg.norm(out, axis=1)
    np.testing.assert_allclose(norms, np.ones(len(texts)), atol=1e-5)


# ---------------------------------------------------------------------------
# Determinism — same call, same result
# ---------------------------------------------------------------------------

def test_deterministic_repeated_call():
    text = "determinism test"
    a = MOCK.embed_texts([text])
    b = MOCK.embed_texts([text])
    np.testing.assert_array_equal(a, b)


def test_deterministic_batch_vs_single():
    texts = ["foo", "bar"]
    batch = MOCK.embed_texts(texts)
    single_foo = MOCK.embed_texts(["foo"])
    single_bar = MOCK.embed_texts(["bar"])
    np.testing.assert_array_equal(batch[0], single_foo[0])
    np.testing.assert_array_equal(batch[1], single_bar[0])


# ---------------------------------------------------------------------------
# Cross-process stability (SHA-256 seed — not Python hash())
# ---------------------------------------------------------------------------

def test_cross_process_determinism():
    """Spawn a child process and verify same vector is produced."""
    script = (
        "from tests.conftest import MockEmbeddingService; "
        "import numpy as np; "
        "m = MockEmbeddingService(); "
        "v = m.embed_texts(['cross-process check']); "
        "print(repr(v[0, :4].tolist()))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"Child process failed: {result.stderr}"
    child_vals = eval(result.stdout.strip())  # noqa: S307 — controlled test input

    parent_vals = MOCK.embed_texts(["cross-process check"])[0, :4].tolist()
    assert child_vals == pytest.approx(parent_vals, abs=1e-6)


# ---------------------------------------------------------------------------
# Distinctness — different inputs → different vectors
# ---------------------------------------------------------------------------

def test_distinct_inputs_distinct_vectors():
    texts = ["apple", "banana", "cherry", "date", "elderberry"]
    out = MOCK.embed_texts(texts)
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            assert not np.allclose(out[i], out[j], atol=1e-4), (
                f"Vectors for '{texts[i]}' and '{texts[j]}' are identical"
            )


# ---------------------------------------------------------------------------
# Global RNG state is not polluted
# ---------------------------------------------------------------------------

def test_does_not_mutate_global_rng():
    """Embedding calls must not alter np.random global state."""
    rng_before = np.random.get_state()
    MOCK.embed_texts(["rng pollution check"] * 10)
    rng_after = np.random.get_state()
    # Compare the position and state array
    assert rng_before[1].tolist() == rng_after[1].tolist(), (
        "embed_texts mutated global NumPy RNG state"
    )
    assert rng_before[2] == rng_after[2]


# ---------------------------------------------------------------------------
# dimension property
# ---------------------------------------------------------------------------

def test_dimension_property():
    assert MOCK.dimension == DIM

