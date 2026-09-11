"""Bounded second-stage ranking. Scores are ordering signals, NOT probabilities."""
import logging
import math
import re
from collections import Counter
from dataclasses import replace
from functools import lru_cache
from threading import Lock

logger = logging.getLogger(__name__)
_model_lock = Lock()


def terms(text: str) -> list[str]:
    words = re.findall(r"[가-힣]+|[a-z]+|\d+", text.lower())
    # Korean character bigrams reduce particle/inflection mismatch without a new tokenizer.
    return [term for word in words for term in (
        [word] + ([word[i:i + 2] for i in range(len(word) - 1)] if re.fullmatch(r"[가-힣]{3,}", word) else [])
    )]


def bm25_scores(query: str, documents: list[str]) -> list[float]:
    counters = [Counter(terms(doc)) for doc in documents]
    lengths = [sum(count.values()) for count in counters]
    average = sum(lengths) / max(1, len(lengths)) or 1
    query_terms = set(terms(query))
    frequencies = {term: sum(term in count for count in counters) for term in query_terms}
    scores = []
    for count, length in zip(counters, lengths):
        score = 0.0
        for term in query_terms:
            tf = count[term]
            df = frequencies[term]
            idf = math.log(1 + (len(counters) - df + 0.5) / (df + 0.5))
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / average))
        scores.append(score)
    return scores


@lru_cache(maxsize=1)
def _cross_encoder(model_name: str):
    # Cache missing-model failures as well: do not retry model initialization on every chat.
    try:
        if not model_name:
            raise ValueError("RAG_RERANK_MODEL is empty")
        from sentence_transformers import CrossEncoder
        return CrossEncoder(model_name, device="cpu", max_length=512, local_files_only=True)
    except Exception as exc:
        logger.warning("CrossEncoder unavailable (%s); using BM25 rank fusion", type(exc).__name__)
        return None


def rerank(query, candidates, top_k, *, mode="bm25", model_name=""):
    if mode == "off":
        return candidates[:top_k]
    # Exact content duplicates with different source IDs must not fill the final context.
    unique, seen, baseline_ranks = [], set(), []
    for position, item in enumerate(candidates, 1):
        key = re.sub(r"\s+", " ", item.content).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
        baseline_ranks.append(position)
    if not unique:
        return []
    documents = [item.content[:6000] for item in unique]
    actual_mode = "bm25_rrf"
    scores = None
    if mode == "cross_encoder":
        try:
            with _model_lock:
                model = _cross_encoder(model_name)
                if model is not None:
                    scores = [float(score) for score in model.predict(
                        [(query[:1500], doc) for doc in documents],
                        batch_size=8, show_progress_bar=False,
                    )]
                    if len(scores) != len(unique) or not all(math.isfinite(s) for s in scores):
                        raise ValueError("Invalid reranker scores")
                    actual_mode = "cross_encoder"
        except Exception as exc:
            logger.warning("CrossEncoder prediction failed (%s); using BM25", type(exc).__name__)
            scores = None
    if scores is None:
        scores = bm25_scores(query, documents)
    second_order = sorted(range(len(unique)), key=lambda i: (-scores[i], i))
    ranks = {i: rank + 1 for rank, i in enumerate(second_order)}
    # BM25 can be noisy: retain semantic rank using weighted reciprocal rank fusion.
    ordering_scores = scores if actual_mode == "cross_encoder" else [
        0.35 / (60 + baseline_ranks[i]) + 0.65 / (60 + ranks[i]) for i in range(len(unique))
    ]
    order = sorted(range(len(unique)), key=lambda i: (-ordering_scores[i], i))
    return [replace(unique[i], metadata={
        **unique[i].metadata,
        "reranker": actual_mode,
        "rerank_requested": mode,
        "rerank_fallback": mode == "cross_encoder" and actual_mode != "cross_encoder",
        "retrieval_rank": baseline_ranks[i],
        "rerank_rank": rank + 1,
        "rerank_score": round(ordering_scores[i], 6),
        "rerank_candidate_count": len(unique),
    }) for rank, i in enumerate(order[:top_k])]
