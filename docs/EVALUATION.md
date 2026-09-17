# hamiGenZ — Evaluation (PR-014)

Core question the evaluation answers:

> **Did hamiGenZ make the information easier to understand without changing its meaning?**

Two benchmarks cover the two halves of that question:

1. **Retrieval** (`tests/evaluation/bench_retrieval.py`) — did we find the
   right evidence, in every language style our users use?
2. **Explanation quality** (`tests/evaluation/eval_explanations.py`) — did
   the explanation preserve the verified key facts, avoid hallucination,
   and match the requested level/language?

LLM-as-judge is deliberately NOT the primary signal. Fact checks are
deterministic substring/regex checks against a **human-verified gold
dataset**; the LLM judge would only ever be a secondary signal.

---

## 1. Gold dataset (`tests/evaluation/gold_dataset.py`)

12+ cases across these categories:

| Category | What it exercises |
|---|---|
| `formal_nepali` | Government-notice register → Simple / Very Simple |
| `legal_nepali` | Statute wording, appeal windows |
| `negation` | Meaning-flip risk (grant NOT available, etc.) |
| `conditions` | Conditional eligibility, numeric limits |
| `exceptions` | Fee-waiver exception clauses |
| `dates` | BS date preservation |
| `fees` | Two-fee swap detection |
| `english_to_nepali` | Numeric anchors across languages |
| `terminology` | Technical terms must survive simplification |
| `romanized_nepali` | Romanized input with embedded facts |
| `mixed` | Mixed-script penalty ranges |

Each case carries:
- `key_facts` — facts a correct explanation MUST preserve. A fact may be a
  string or a list of alternatives (any one match passes), e.g.
  `["५००", "500"]` or `["७०", "सत्तरी"]`.
- `forbidden_facts` — substrings that indicate hallucination/drift.
- `negation_guards` — `(affirmative_phrase, negated_form)` pairs. If the
  affirmative phrase appears WITHOUT its negated form, the model dropped a
  negation. This catches meaning flips that bare substring checks cannot.
- `notes` — the human rationale for the expected facts.

Dataset integrity is enforced by `tests/test_evaluation.py`: every key fact
must actually occur in the source text, no forbidden fact may occur in the
source, and an echo-mock (perfect fact preservation) must pass every case.
These self-consistency tests caught 4 real dataset bugs during development.

## 2. Retrieval benchmark results

12-topic synthetic corpus (realistic Nepali government content), 18 queries
across 4 styles, 3 negative probes. Similarity = cosine (inner product on
normalized vectors).

### all-MiniLM-L6-v2 (the previous default)

| Style | n | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|
| English (over Nepali docs) | 5 | **0.00** | 0.40 | 0.26 |
| Nepali script | 5 | 0.40 | 0.60 | 0.54 |
| Romanized | 4 | 0.25 | 0.25 | 0.36 |
| Mixed | 4 | 0.25 | 0.50 | 0.49 |
| **Overall** | 18 | **0.22** | 0.44 | **0.41** |

Negative probes: **false-match rate 0.33** — a Nepali poetry request
matched a government-notice chunk at 0.76 similarity (the model matches
script tokens, not meaning).

### paraphrase-multilingual-MiniLM-L12-v2 (the new default)

| Style | n | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|
| English (over Nepali docs) | 5 | **1.00** | 1.00 | 1.00 |
| Nepali script | 5 | **1.00** | 1.00 | 1.00 |
| Romanized | 4 | 0.50 | 0.50 | 0.61 |
| Mixed | 4 | 0.25 | 0.75 | 0.53 |
| **Overall** | 18 | **0.72** | 0.83 | **0.81** |

Negative probes: **false-match rate 0.00** (top similarity 0.19 on
irrelevant queries).

## 3. Embedding-model decision

**Decision: switch the default to `paraphrase-multilingual-MiniLM-L12-v2`.**

Evidence:
- Overall Hit@1 0.22 → 0.72 (3.2×), MRR 0.41 → 0.81 (~2×)
- Cross-lingual English→Nepali Hit@1 0.00 → 1.00 — the old model could
  not answer English questions about Nepali documents at all
- False-match rate 0.33 → 0.00
- Same 384-dim output, same sentence-transformers interface, local and
  free — no architecture change required
- Remaining weakness: romanized queries (0.50 Hit@1). Romanized Nepali is
  under-served by every public multilingual model; candidates like
  LaBSE or multilingual-E5 are heavier. Re-evaluate only if a future
  benchmark shows a better free/local option.

Known cost: the multilingual model is somewhat slower to load/encode than
the English-only MiniLM. For this product, correctness of retrieval
outranks embedding latency.

### Model-switch safety (silent-vector-corruption guard)

Both models output 384 dims, so a dimension check alone cannot detect a
model switch — and a switched model silently turns an existing FAISS index
into garbage. `VectorStore` now keeps an `embed_model.txt` stamp:

- On startup, if the stamp differs from the active model, documents whose
  chunk text is still stored are **re-embedded in place** (no original
  file needed); indices that cannot be re-embedded are **quarantined**
  (removed) rather than served from the wrong vector space.
- `REINDEX_ON_STARTUP=0` disables auto-reindexing (stamp mismatch is then
  reported as a warning and non-reindexable docs are still quarantined).
- `POST /upload?reindex_doc_id=<id>` manually re-embeds one document
  (file re-upload required; same doc_id preserved).

## 4. How to run

```bash
# Retrieval benchmark (optionally for any model)
.venv/Scripts/python.exe -m tests.evaluation.bench_retrieval
.venv/Scripts/python.exe -m tests.evaluation.bench_retrieval --model paraphrase-multilingual-MiniLM-L12-v2

# Explanation evaluator — offline self-consistency (mock)
.venv/Scripts/python.exe -m tests.evaluation.eval_explanations

# Explanation evaluator — live LLM run (requires Ollama qwen3:8b)
.venv/Scripts/python.exe -m tests.evaluation.eval_explanations --live --out eval_results.json

# Dataset integrity / evaluation machinery tests
.venv/Scripts/python.exe -m pytest tests/test_evaluation.py -v
```

## 5. Live explanation evaluation (qwen3:8b)

Ran with `--live` (real Ollama qwen3:8b, 17 gold cases):

| Metric | Score |
|---|---|
| All key facts preserved | **0.88** |
| Hallucination-free (no forbidden facts / negation flips) | **1.00** |
| Script-appropriate output (Devanagari for Nepali cases) | **1.00** |
| Overall pass (all of the above + level plausibility) | **0.88** |

The 2 remaining failures are fact-omissions, not hallucinations — the
model summarized without repeating an explicit fact (e.g. a "3 days"
lead time, a license-cancellation consequence). No fabricated facts, no
negation flips, no wrong-script answers.

Checker design notes (learned from live runs):
- Nepali negation has many grammatical forms, so negation guards use a
  **set of negation markers per sentence** (छैन / हुँदैन / पाइँदैन …),
  not a single expected phrasing.
- Key facts accept **alternative surface forms** (देवनागरी/ASCII digits,
  सत्तरी/सत्तर, romanized/Devanagari) so paraphrase isn't punished as
  fact loss — only true omission or wrong numbers are flagged.

## 6. Limitations

- The corpus is synthetic (12 topics) — realistic, but small. Expand with
  real OCR'd government documents over time.
- `--live` explanation evaluation requires manual review of flagged
  failures; automated scoring is deterministic-only for now (LLM judge
  intentionally excluded from CI).
- Romanized-query retrieval (0.50 Hit@1) is the weakest style; tracked as
  future work (possible query-expansion or a romanization-aware index).
