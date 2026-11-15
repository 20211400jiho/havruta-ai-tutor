"""Regression cases taken from quizzes generated on the deployed site (2026-11-16)."""
from app.services.content_service import _distractors_for, _is_complete_answer


def test_paraphrased_question_answer_is_not_used_as_distractor():
    correct = "도형의 방정식은 기하학적 도형을 수학적으로 표현하는 방법으로, 예를 들어 직선의 방정식, 원의 방정식 등을 통해 도형의 위치와 형태를 나타낼 수 있습니다."
    candidates = [
        {"question": "도형의 방정식이 뭐예요?",
         "answer": "도형의 방정식은 평면 위의 도형을 수학적으로 표현한 식이에요. 예를 들어, 원의 방정식은 (x-h)² + (y-k)² = r²로 나타냅니다."},
        {"question": "두 원의 교점을 지나는 도형의 방정식의 종류는 어떤것이 있나요?",
         "answer": "두 원의 교점을 지나는 직선의 방정식 (공통현의 방정식) 이 있습니다."},
        {"question": "원점에 대한 대칭이동은?", "answer": "원점에 대하여 대칭이동한 도형의 방정식은 f(-x,-y)=0이다."},
        {"question": "평행이동이란?", "answer": "도형을 일정한 방향으로 일정한 거리만큼 옮기는 것을 평행이동이라고 합니다."},
    ]
    distractors = _distractors_for(correct, "도형의 방정식이란 무엇인가요?", candidates)
    assert not any("평면 위의 도형을 수학적으로 표현한 식" in item for item in distractors)


def test_restated_correct_answer_is_not_used_as_distractor():
    correct = "알고리즘은 프로그래밍 언어로 구현합니다."
    candidates = [
        {"question": "알고리즘을 구현하는 도구는?", "answer": "프로그래밍 언어입니다."},
        {"question": "컴파일러란?", "answer": "컴파일러와 인터프리터는 프로그래밍 언어로 작성된 코드를 컴퓨터가 이해할 수 있는 형태로 변환해주는 프로그램입니다."},
        {"question": "인터프리터란?", "answer": "컴파일러와 인터프리터는 프로그래밍 언어로 작성된 코드를 컴퓨터가 이해할 수 있는 형식으로 변환해주는 프로그램입니다."},
    ]
    distractors = _distractors_for(correct, "알고리즘을 무엇으로 구현하나요?", candidates)
    assert "프로그래밍 언어입니다." not in distractors
    # Near-identical distractors should not both appear.
    assert sum("컴파일러와 인터프리터는" in item for item in distractors) <= 1


def test_cut_off_and_off_topic_answers_are_rejected():
    assert not _is_complete_answer("도형의 방정식은")
    assert not _is_complete_answer("평행이동한 도형의 방정식은")
    assert _is_complete_answer("대칭이동한 도형의 방정식이다.")
    correct = "독자는 다양한 독서의 방법을 알고, 이러한 방법을 적용하여 보다 효과적으로 독서할 수 있어야 합니다."
    candidates = [
        {"question": "방어 대책은?", "answer": "방비를 더욱 철저히 해야 합니다."},
        {"question": "독서 방법은 무엇에 따라 달라지나요?", "answer": "글을 읽는 방법은 글의 특성, 독서의 상황, 목적 등에 따라 달라질 수 있습니다."},
        {"question": "일반적인 독서 방법은?", "answer": "일반적으로 독서의 방법에는 사실적 독해, 추론적 독해, 비판적 독해, 감상적 독해, 창의적 독해가 있습니다."},
        {"question": "독서의 목적은?", "answer": "독서의 목적에는 정보 습득, 문제 해결, 즐거움을 위한 독서가 있습니다."},
    ]
    distractors = _distractors_for(correct, "독자는 독서를 할 때 무엇을 알고 적용해야 하나요?", candidates)
    assert "방비를 더욱 철저히 해야 합니다." not in distractors


class _FakeResponse:
    status = "completed"

    def __init__(self, text):
        self.output_text = text


def _rows():
    return [
        {"question": "알고리즘이란?", "options": ["절차", "언어", "기계", "도구"], "correct_index": 0},
        {"question": "문법이 중요한 이유는?", "options": ["규칙 때문", "형식 때문", "색상", "소리"], "correct_index": 1},
    ]


def test_ai_check_drops_questions_with_more_than_one_right_option(monkeypatch):
    from app.services import content_service

    sent = {}

    class FakeClient:
        def __init__(self, **_):
            self.responses = self

        def create(self, **kwargs):
            sent.update(kwargs)
            return _FakeResponse('{"results": [{"id": 0, "acceptable_options": [1]}, {"id": 1, "acceptable_options": [1, 2]}]}')

    monkeypatch.setattr(content_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(content_service, "OpenAI", FakeClient)
    kept = content_service._verify_quiz_rows(_rows(), "정보")
    assert [row["question"] for row in kept] == ["알고리즘이란?"]
    # The checker must not be told which option is stored as correct.
    assert "correct_index" not in sent["input"][0]["content"]


def test_ai_check_failure_falls_back_to_lexical_filters(monkeypatch):
    from openai import OpenAIError
    from app.services import content_service

    class BrokenClient:
        def __init__(self, **_):
            self.responses = self

        def create(self, **_):
            raise OpenAIError("down")

    monkeypatch.setattr(content_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(content_service, "OpenAI", BrokenClient)
    assert content_service._verify_quiz_rows(_rows(), "정보") is None
    monkeypatch.setattr(content_service.settings, "openai_api_key", None)
    assert content_service._verify_quiz_rows(_rows(), "정보") is None
