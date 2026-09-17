"""
hamigenz — Retrieval benchmark for the embedding model (PR-014).

Evaluates all-MiniLM-L6-v2 on:
  - English / Nepali script / Romanized Nepali / mixed queries
  - Hit@1, Hit@3, MRR
  - false-retrieval behavior (irrelevant query → low similarity?)
  - cross-lingual similarity behavior (EN query vs NP content)

Run directly:
    .venv/Scripts/python.exe -m tests.evaluation.bench_retrieval
Or as part of the evaluator runner.
"""
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

# ─── Benchmark corpus ─────────────────────────────────────────────
# Each doc: {id, page, text, topic}. Topics are distinct so a relevant
# query has exactly one clearly-correct target.

CORPUS = [
    {"id": "fee_34page", "page": 1, "topic": "passport_fee",
     "text": "साधारण राहदानी ३४ पृष्ठको शुल्क रु. ५,००० रहेको छ र सेवा अवधि १५ दिन छ।"},
    {"id": "fee_express", "page": 1, "topic": "passport_express",
     "text": "तत्काल (express) सेवाअन्तर्गत ३४ पृष्ठको राहदानी रु. १२,००० मा एक दिनभित्र उपलब्ध हुन्छ।"},
    {"id": "docs_required", "page": 2, "topic": "passport_docs",
     "text": "राहदानीका लागि आवश्यक कागजातहरू: नागरिकताको प्रमाणपत्रको मूल प्रति र प्रतिलिपि।"},
    {"id": "appointment", "page": 2, "topic": "passport_appointment",
     "text": "अनलाइन अपोइन्टमेन्ट बुक गरेर मात्र राहदानी विभाग जानुपर्छ। बिना अपोइन्टमेन्ट काम हुँदैन।"},
    {"id": "license_written", "page": 1, "topic": "license_written",
     "text": "सवारी चालक अनुमतिपत्रको लिखित परीक्षा पास गरेपछि मात्र प्रयोगात्मक परीक्षा दिन पाइन्छ।"},
    {"id": "license_age", "page": 1, "topic": "license_age",
     "text": "मोटरसाइकल लाइसेन्सका लागि न्यूनतम उमेर १८ वर्ष र सार्वजनिक सवारीका लागि २१ वर्ष हुनुपर्छ।"},
    {"id": "license_fine", "page": 3, "topic": "license_fine",
     "text": "लाइसेन्स नवीकरण म्याद नाघेपछि प्रति महिना रु. ५० ढिलाइ शुल्क लाग्छ।"},
    {"id": "nid_enroll", "page": 1, "topic": "nid_enrollment",
     "text": "राष्ट्रिय परिचयपत्र दर्ता निःशुल्क छ र वडा कार्यालयबाट गराउन सकिन्छ।"},
    {"id": "nid_docs", "page": 1, "topic": "nid_docs",
     "text": "राष्ट्रिय परिचयपत्रका लागि नागरिकता, जन्म दर्ता र फोटो चाहिन्छ।"},
    {"id": "birth_reg", "page": 2, "topic": "birth_registration",
     "text": "जन्म दर्ता जन्मभएको ३५ दिनभित्र वडा कार्यालयमा निःशुल्क गराउनुपर्छ।"},
    {"id": "traffic_rule", "page": 4, "topic": "traffic_helmet",
     "text": "मोटरसाइकल चलाउँदा हेलमेट अनिवार्य छ। हेलमेट बिना सवारी चलाउने चालकलाई जरिवाना हुन्छ।"},
    {"id": "visa_onarrival", "page": 1, "topic": "visa_arrival",
     "text": "Arrival visa for tourists is available at Tribhuvan International Airport for 15, 30, and 90 days."},
]

# (query, language_style, expected_topic, expected_page)
QUERIES = [
    # English queries over Nepali content (cross-lingual stress)
    ("How much does a normal 34-page passport cost?", "english", "passport_fee", 1),
    ("What documents do I need for a passport?", "english", "passport_docs", 2),
    ("Minimum age for a motorcycle driving license?", "english", "license_age", 1),
    ("Is national ID card registration free?", "english", "nid_enrollment", 1),
    ("Late renewal fine for license?", "english", "license_fine", 3),
    # Nepali script queries
    ("राहदानी बनाउन कति शुल्क लाग्छ?", "nepali", "passport_fee", 1),
    ("राहदानीको लागि के के कागजात चाहिन्छ?", "nepali", "passport_docs", 2),
    ("लिखित परीक्षा पास गरेपछि के हुन्छ?", "nepali", "license_written", 1),
    ("जन्म दर्ता कहाँ र कति दिनभित्र गर्ने?", "nepali", "birth_registration", 2),
    ("हेलमेट बिना चलाए के हुन्छ?", "nepali", "traffic_helmet", 4),
    # Romanized Nepali queries
    ("passport ko lagi k k kagaja chahinxa?", "romanized", "passport_docs", 2),
    ("license Renewal gareko dherai bhayo fine kati?", "romanized", "license_fine", 3),
    ("rastrastra parichaypatra nishulk huncha?", "romanized", "nid_enrollment", 1),
    ("janma darta kata garne?", "romanized", "birth_registration", 2),
    # Mixed queries
    ("express service ma passport kati din ma milcha?", "mixed", "passport_express", 1),
    ("जन्म दर्ता birth registration ko fee kati ho?", "mixed", "birth_registration", 2),
    ("National ID दर्ता गर्न के चाहिन्छ?", "mixed", "nid_docs", 1),
    ("हेलमेट नलगाए fine kati parcha?", "mixed", "traffic_helmet", 4),
]

# Queries that must NOT strongly match any corpus doc (false-retrieval probe)
NEGATIVE_QUERIES = [
    ("What is the best trekking season in Nepal?", "english"),
    ("मलाई माया भएकी कविता सुनाउनुहोस्।", "nepali"),
    ("how to cook momo at home?", "english"),
]


def run_benchmark(model_name: str = "all-MiniLM-L6-v2") -> dict:
    """Run the retrieval benchmark. Returns a results dict."""
    from vector_store import EmbeddingService

    embedder = EmbeddingService(model_name=model_name)
    doc_texts = [d["text"] for d in CORPUS]
    doc_embeddings = embedder.embed_texts(doc_texts)

    results = []
    for query, style, topic, page in QUERIES:
        q_emb = embedder.embed_text(query).reshape(-1)  # (1, dim) → (dim,)
        sims = (doc_embeddings @ q_emb).tolist()
        ranked = sorted(
            zip(sims, [d["id"] for d in CORPUS],
                [d["topic"] for d in CORPUS], [d["page"] for d in CORPUS]),
            key=lambda x: x[0], reverse=True,
        )
        hit1 = ranked[0][2] == topic
        hit3 = any(r[2] == topic for r in ranked[:3])
        mrr = 0.0
        for rank, r in enumerate(ranked, start=1):
            if r[2] == topic:
                mrr = 1.0 / rank
                break
        results.append({
            "query": query, "style": style, "expected_topic": topic,
            "expected_page": page,
            "top1": ranked[0][1], "top1_topic": ranked[0][2],
            "top1_page": ranked[0][3], "top1_sim": round(ranked[0][0], 4),
            "hit@1": hit1, "hit@3": hit3, "mrr": mrr,
            "page_correct": ranked[0][3] == page or any(
                r[3] == page for r in ranked[:3]),
        })

    negatives = []
    for query, style in NEGATIVE_QUERIES:
        q_emb = embedder.embed_text(query).reshape(-1)
        sims = (doc_embeddings @ q_emb).tolist()
        top = max(sims)
        negatives.append({
            "query": query, "top_sim": round(top, 4),
            "false_match": top > 0.5,
        })

    def agg(rs, key):
        vals = [r[key] for r in rs]
        return (sum(vals) / len(vals)) if vals else 0.0

    summary = {"overall": {}, "by_style": {}, "model": model_name}
    summary["overall"] = {
        "n": len(results),
        "hit@1": round(agg(results, "hit@1"), 3),
        "hit@3": round(agg(results, "hit@3"), 3),
        "mrr": round(agg(results, "mrr"), 3),
        "page_correct@3": round(agg(results, "page_correct"), 3),
    }
    for style in ("english", "nepali", "romanized", "mixed"):
        subset = [r for r in results if r["style"] == style]
        if subset:
            summary["by_style"][style] = {
                "n": len(subset),
                "hit@1": round(agg(subset, "hit@1"), 3),
                "hit@3": round(agg(subset, "hit@3"), 3),
                "mrr": round(agg(subset, "mrr"), 3),
            }
    summary["negative_probes"] = {
        "n": len(negatives),
        "false_match_rate": round(
            sum(1 for n in negatives if n["false_match"]) / len(negatives), 3),
        "detail": negatives,
    }
    summary["detail"] = results
    return summary


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()
    res = run_benchmark(model_name=args.model)
    print(json.dumps({k: v for k, v in res.items() if k != "detail"},
                     indent=2, ensure_ascii=False))
