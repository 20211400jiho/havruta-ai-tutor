"""Replay human-labelled candidate sets; no DB, network or paid LLM calls by default.

This evaluates ranking only, not production retrieval, answer accuracy or learning.
Run from the repository root: python -m scripts.evaluate_reranking cases.json
"""
import argparse
import json
from pathlib import Path
from time import perf_counter

from app.rag.retriever import SearchResult
from app.rag.reranker import rerank


def metrics(results, relevant, k):
    hits = [item.source_id in relevant for item in results[:k]]
    return {
        "precision_at_k": sum(hits) / k,
        "hit_at_k": float(any(hits)),
        "mrr_at_k": next((1 / (i + 1) for i, hit in enumerate(hits) if hit), 0.0),
    }


def evaluate(cases, k=3, mode="bm25", model_name=""):
    if not cases or k < 1:
        raise ValueError("Provide nonempty labelled cases and positive k")
    rows = []
    for case in cases:
        relevant = set(case["relevant_source_ids"])
        if not relevant:
            raise ValueError("Cases require labelled relevant_source_ids")
        candidates = [SearchResult(None, item["source_id"], item["content"], float(item.get("score", 0)), {})
                      for item in case["candidates"]]
        if len({item.source_id for item in candidates}) != len(candidates):
            raise ValueError("Candidate source IDs must be unique")
        start = perf_counter()
        selected = rerank(case["query"], candidates, k, mode=mode, model_name=model_name)
        rows.append({
            "id": case["id"], "query": case["query"],
            "baseline": metrics(candidates, relevant, k),
            "reranked": metrics(selected, relevant, k),
            "baseline_ids": [item.source_id for item in candidates[:k]],
            "reranked_ids": [item.source_id for item in selected],
            "actual_reranker": selected[0].metadata.get("reranker", "off") if selected else "none",
            "rerank_only_ms": round((perf_counter() - start) * 1000, 3),
        })
    return {
        "scope": "labelled_candidate_replay_only",
        "warning": "Not production accuracy, Ragas, hallucination rate, or learning effectiveness.",
        "cases": len(rows), "k": k, "requested_mode": mode,
        "means": {variant: {metric: round(sum(row[variant][metric] for row in rows) / len(rows), 4)
                             for metric in ("precision_at_k", "hit_at_k", "mrr_at_k")}
                  for variant in ("baseline", "reranked")},
        "details": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--mode", choices=["bm25", "cross_encoder"], default="bm25")
    parser.add_argument("--model", default="")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    report = evaluate(cases, args.top_k, args.mode, args.model)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
