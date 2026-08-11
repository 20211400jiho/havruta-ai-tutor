from app.database.config import settings
from app.services import tutor_service


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

    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "test-model")
    monkeypatch.setattr(tutor_service, "OpenAI", FakeOpenAI)

    result = tutor_service._openai_generate("학습 자료와 학생 답변", "과학")

    assert result == "검색 근거를 사용한 후속 질문"
    assert captured["client"]["api_key"] == "test-key"
    assert captured["model"] == "test-model"
    assert captured["reasoning"] == {"effort": "none"}
    assert captured["input"] == "학습 자료와 학생 답변"
    assert "하브루타 과학 튜터" in captured["instructions"]
