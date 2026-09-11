from app.database.config import settings
from app.rag import tutor as tutor_service
from app.rag.retriever import SearchResult
from app.rag import retriever as rag_service
from app.rag.dialogue import TutorTurn


def test_openai_generation_uses_configured_model(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"output_text": "검색 근거를 사용한 후속 질문"})()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "test-model")
    monkeypatch.setattr(tutor_service, "OpenAI", FakeOpenAI)

    result = tutor_service._openai_generate("학습 자료와 학생 답변", "과학")

    assert result == "검색 근거를 사용한 후속 질문"
    assert captured["client"]["api_key"] == "test-key"
    assert captured["model"] == "test-model"
    assert captured["reasoning"] == {"effort": "none"}
    assert captured["input"] == [{"role": "user", "content": "학습 자료와 학생 답변"}]
    assert captured["max_output_tokens"] == settings.openai_max_output_tokens
    assert captured["store"] is False
    assert "하브루타 과학 튜터" in captured["instructions"]


def test_generation_failure_reports_rule_fallback(monkeypatch):
    monkeypatch.setattr(tutor_service, "_openai_generate", lambda *args, **kwargs: None)

    generated, provider = tutor_service.generate_with_provider("발표 중 강제 장애", "수학")

    assert generated is None
    assert provider == "rule"


def test_uncertain_answer_keeps_previous_question_context(monkeypatch):
    captured = {}
    context = SearchResult(
        chunk_id=None,
        source_id="english-useful-convenient",
        content="useful은 도움이 되는, convenient는 사용하기 편리한 상황을 나타낸다.",
        score=0.91,
        metadata={
            "subject": "영어",
            "description": "useful은 쓸모나 도움, convenient는 이용상의 편리함에 초점을 둔다.",
            "question": "I didn't know that에서 didn't know는 무슨 뜻인가요?",
            "retriever": "chroma",
        },
    )

    def fake_search(_db, query, **kwargs):
        captured["query"] = query
        captured["search_options"] = kwargs
        return [context]

    monkeypatch.setattr(tutor_service, "search", fake_search)
    monkeypatch.setattr(tutor_service, "generate_with_provider", lambda *_args: (None, "rule"))

    reply, feedback, _, response_meta = tutor_service.tutor_reply(
        None,
        "용이한 표현",
        "몰라",
        "영어",
        conversation_history=[
            {
                "sender_type": "ai",
                "content": "useful과 convenient는 각각 어떤 상황에서 쓰면 좋을까요?",
            },
            {"sender_type": "user", "content": "몰라"},
        ],
    )

    assert "useful과 convenient" in captured["query"]
    assert "몰라" not in captured["query"]
    assert "방금 질문을 더 쉽게" in reply
    assert "I didn't know that" not in reply
    assert "이해되는 단어나 조건 하나" in feedback["followup_question"]
    assert feedback["score"] is None
    assert feedback["level"] == "힌트 단계"
    assert response_meta["stage"] == "개념 설명"


def test_openai_prompt_explicitly_preserves_conversation_continuity(monkeypatch):
    captured = {}

    monkeypatch.setattr(tutor_service, "search", lambda *_args, **_kwargs: [])

    def fake_generate(prompt, subject, conversation_history=None, response_schema=None):
        captured["prompt"] = prompt
        captured["subject"] = subject
        captured["conversation_history"] = conversation_history
        return TutorTurn(explanation="앞선 질문을 이어가는 답변", next_question="두 표현의 쓰임을 골라볼까요?",
                         assessment="partial", evidence_quote="", reasoning="차이를 추가 확인합니다.",
                         misconception="", source_ids=[]).model_dump_json(), "openai"

    monkeypatch.setattr(tutor_service, "generate_with_provider", fake_generate)

    reply, _, _, _ = tutor_service.tutor_reply(
        None,
        "용이한 표현",
        "둘 다 편리하다는 뜻 같아",
        "영어",
        conversation_history=[
            {"sender_type": "ai", "content": "useful과 convenient의 차이는 무엇일까요?"},
            {"sender_type": "user", "content": "둘 다 편리하다는 뜻 같아"},
        ],
    )

    assert reply.startswith("앞선 질문을 이어가는 답변")
    assert "직전 AI 질문: useful과 convenient의 차이는 무엇일까요?" in captured["prompt"]
    assert "갑자기 다른 개념이나 문제로 전환하지 마세요" in captured["prompt"]
    assert captured["subject"] == "영어"
    assert captured["conversation_history"] == [
        {"sender_type": "ai", "content": "useful과 convenient의 차이는 무엇일까요?"}
    ]


def test_openai_generation_preserves_role_order(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"output_text": "이어지는 질문"})()

    class FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(tutor_service, "OpenAI", FakeOpenAI)
    tutor_service._openai_generate(
        "현재 답변을 평가해줘",
        "영어",
        [
            {"sender_type": "ai", "content": "두 표현의 차이는 무엇일까요?"},
            {"sender_type": "user", "content": "쓰임이 달라요."},
        ],
    )

    assert captured["input"] == [
        {"role": "assistant", "content": "두 표현의 차이는 무엇일까요?"},
        {"role": "user", "content": "쓰임이 달라요."},
        {"role": "user", "content": "현재 답변을 평가해줘"},
    ]


def test_chroma_filter_includes_school_level_and_grade():
    where = rag_service._chroma_where("도덕", None, "중학교", "3학년")

    assert where == {
        "$and": [
            {"subject": {"$eq": "도덕"}},
            {"school_level": {"$eq": "중학교"}},
            {"grade": {"$eq": "3학년"}},
        ]
    }


def test_learning_scope_rejects_other_grade_but_allows_legacy_metadata():
    assert rag_service._matches_learning_scope(
        {"school_level": "중학교", "grade": "1학년"},
        "중학교",
        "3학년",
    ) is False
    assert rag_service._matches_learning_scope({"subject": "수학"}, "고등학교", "1학년") is True
