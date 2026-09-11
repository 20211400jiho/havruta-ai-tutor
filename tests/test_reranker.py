import math

import pytest

from app.database.config import settings
from app.rag.retriever import SearchResult
from app.rag import retriever, reranker


def result(source, text, score=0.8):
    return SearchResult(None, source, text, score, {"retriever": "chroma"})


def test_bm25_promotes_specific_context_and_deduplicates():
    candidates = [result("a", "생물의 구성 단계를 공부합니다."),
                  result("b", "기관은 여러 조직이 모여 특정 기능을 수행하는 구성 단계입니다."),
                  result("c", "기관은 여러 조직이 모여 특정 기능을 수행하는 구성 단계입니다.")]
    selected = reranker.rerank("조직이 모인 기관의 기능", candidates, 3)
    assert selected[0].source_id == "b"
    assert len(selected) == 2
    assert selected[0].metadata["reranker"] == "bm25_rrf"
    assert selected[0].metadata["retrieval_rank"] == 2
    assert selected[0].score == 0.8  # preserve legacy retrieval score, no probability fabrication
    assert "reranker" not in candidates[1].metadata


def test_off_empty_and_no_overlap_are_stable():
    candidates = [result("a", "first"), result("b", "second")]
    # Ordering is stable when the second-stage evidence is tied.
    assert [item.source_id for item in reranker.rerank("unrelated", candidates, 2)] == ["a", "b"]
    assert reranker.rerank("q", candidates, 1, mode="off") == candidates[:1]
    assert reranker.rerank("q", [], 3) == []
    assert all(math.isfinite(s) for s in reranker.bm25_scores("q", ["", "q"]))


@pytest.mark.parametrize("outcome", [None, "raise", "nan", "short"])
def test_cross_encoder_failure_falls_back(monkeypatch, outcome):
    class FakeModel:
        def predict(self, *_args, **_kwargs):
            if outcome == "raise":
                raise RuntimeError("unavailable")
            return [float("nan"), 1] if outcome == "nan" else [1]
    monkeypatch.setattr(reranker, "_cross_encoder", lambda _: None if outcome is None else FakeModel())
    selected = reranker.rerank("기관", [result("a", "세포"), result("b", "기관")], 1, mode="cross_encoder")
    assert selected[0].metadata["rerank_fallback"] is True
    assert selected[0].metadata["reranker"] == "bm25_rrf"


def test_cross_encoder_scores_order_candidates(monkeypatch):
    class FakeModel:
        def predict(self, pairs, **kwargs):
            assert len(pairs) == 2
            return [-2.0, 4.0]
    monkeypatch.setattr(reranker, "_cross_encoder", lambda _: FakeModel())
    selected = reranker.rerank("기관", [result("a", "세포"), result("b", "기관")], 1, mode="cross_encoder")
    assert selected[0].source_id == "b"
    assert selected[0].metadata["rerank_fallback"] is False


def test_search_expands_candidates_preserves_scope_and_honors_off(monkeypatch):
    captured = []
    def fake_search(*args):
        captured.append(args)
        return [result("a", "생물"), result("b", "조직 기관")]
    monkeypatch.setattr(settings, "rag_provider", "chroma")
    monkeypatch.setattr(settings, "rag_reranker", "bm25")
    monkeypatch.setattr(settings, "rag_rerank_candidates", 15)
    monkeypatch.setattr(retriever, "search_chroma", fake_search)
    selected = retriever.search(None, "생물", 1, subject="과학", unit_code="9과02", school_level="중학교",
                                grade="2학년", rerank_query="조직 기관")
    assert captured[-1][1] == 15
    assert captured[-1][2:] == ("과학", "2022", None, "9과02", "중학교", "2학년")
    assert selected[0].source_id == "b"
    monkeypatch.setattr(settings, "rag_reranker", "off")
    assert retriever.search(None, "생물", 1)[0].source_id == "a"
    assert captured[-1][1] == 1


def test_evaluation_reports_labelled_rank_changes_not_probability():
    from scripts.evaluate_reranking import evaluate
    report = evaluate([{
        "id": "synthetic-regression", "query": "조직 기관", "relevant_source_ids": ["b"],
        "candidates": [{"source_id": "a", "content": "다항식 계산"},
                       {"source_id": "b", "content": "조직 기관"}],
    }], k=1)
    assert report["means"]["baseline"]["hit_at_k"] == 0
    assert report["means"]["reranked"]["hit_at_k"] == 1
    assert report["scope"] == "labelled_candidate_replay_only"
    assert report["details"][0]["actual_reranker"] == "bm25_rrf"


def test_evaluation_requires_labels():
    from scripts.evaluate_reranking import evaluate
    with pytest.raises(ValueError):
        evaluate([])
    with pytest.raises(ValueError):
        evaluate([{"relevant_source_ids": []}])
