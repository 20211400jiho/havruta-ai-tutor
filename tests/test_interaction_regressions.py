import pytest

from app.rag import tutor
from app.rag.dialogue import DialogueState, ProgressiveTutorTurn, classify_intent, prepare_state, apply_assessment, select_followup
from app.rag.retriever import SearchResult

QUESTION = "y=-2x에서 x가 1에서 3으로 증가할 때 y의 값은 어떻게 변하나요?"


def turn(**changes):
    values = dict(explanation="x=3이면 y=-6입니다.", next_question="x=3을 대입할 때 y의 부호는 어떻게 정해지나요?",
                  next_question_goal="reason", assessment="partial", evidence_quote="", source_ids=["m1"],
                  reasoning="부호를 더 확인합니다.", misconception="", answer_status="partial",
                  missing_requirement="x=3을 대입할 때 결과의 부호")
    return ProgressiveTutorTurn(**{**values, **changes})


@pytest.mark.parametrize("answer,intent", [
    ("왜 음수를 곱하면 줄어드는 거야? 설명해줘", "simplify"),
    ("계산하는 방법을 모르겠어. 설명해줘", "simplify"),
    ("다시 설명해주세요", "simplify"), ("모르겠어", "hint"),
    ("정답 말고 힌트로 설명해줘", "hint"), ("예시로 설명해줘", "example"),
    ("정답 말고 힌트로 쉽게 설명해줘", "hint"),
])
def test_help_intent_matches_user_request(answer, intent):
    assert classify_intent(answer) == intent


def test_corrective_question_is_not_discarded_for_first_stage_label():
    state = DialogueState(focus_question=QUESTION, assessment="misconception")
    model = turn()
    assert select_followup(state, model, "정비례", "수학", QUESTION) == model.next_question


def test_wrong_goal_fallback_keeps_current_problem_not_free_topic_example():
    state = DialogueState(focus_question=QUESTION, assessment="misconception")
    q = select_followup(state, turn(next_question_goal="application"), "정비례", "수학", QUESTION)
    assert QUESTION.rstrip("?") in q
    assert "구체적인 사례" not in q and "이유" in q


def test_proven_reasoning_does_not_regress_to_negative_number_comparison():
    state = DialogueState(stage="근거 확인", assessment="understood", answer_status="correct",
                          evidence=[{"stage": "개념 설명", "quote": "Δy=-2Δx이므로 Δx>0이면 Δy<0입니다."}])
    q = select_followup(state, turn(next_question="-2와 -6을 음수의 크기와 연결해 비교해볼까요?"), "정비례", "수학", QUESTION)
    assert "조건" in q and "음수의 크기" not in q
    assert state.question_guard == "기초 회귀 방지"


def test_partial_goal_explains_specific_remaining_requirement_without_promoting():
    state = prepare_state([], "정비례", "-2에서 -6")
    apply_assessment(state, turn(answer_status="correct", evidence_quote="-2에서 -6"), "-2에서 -6", {"m1"})
    assert "결과의 부호" in state.assessment_message
    assert state.stage == "개념 설명" and not state.evidence


def test_already_proven_linear_reason_moves_to_new_condition():
    state = DialogueState(stage="근거 확인", assessment="understood", answer_status="correct",
                          evidence=[{"stage":"개념 설명","quote":"Δy=-2Δx라서 Δx>0이면 Δy<0입니다."}])
    q = select_followup(state, turn(next_question="기울기가 음수일 때 내려가는 이유를 변화량으로 설명해볼까요?"), "정비례", "수학", QUESTION)
    assert "부호를 반대로" in q
    assert len(state.evidence) == 1 and state.stage == "근거 확인"


@pytest.mark.parametrize("stage,expected", [("개념 설명", "근거 확인"), ("적용", "최종 정리")])
def test_alignment_retry_can_confirm_answer_but_only_one_stage(monkeypatch, stage, expected):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SearchResult(None,"m1","y=-2x에서 x=1이면 -2, x=3이면 -6이다.",.9,{})])
    calls = []
    def generate(*args):
        calls.append(args)
        return turn(assessment="partial" if len(calls) == 1 else "understood", answer_status="correct",
                    evidence_quote="-2에서 -6", missing_requirement="").model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "generate_with_provider", generate)
    hist = [{"sender_type":"ai","content":QUESTION,"response_meta":{"dialogue_state":DialogueState(stage=stage,focus_question=QUESTION,last_question=QUESTION).model_dump()}}]
    _, _, _, meta = tutor.tutor_reply(None, "정비례", "-2에서 -6", "수학", conversation_history=hist)
    assert len(calls) == 2 and "goal_alignment" in calls[1][0]
    assert meta["stage"] == expected and len(meta["dialogue_state"]["evidence"]) == 1


def test_explanation_is_not_replaced_by_hint_or_checked(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [])
    model = turn(explanation="-2를 곱한다는 것은 x가 1 늘 때 y가 2 줄어든다는 뜻이에요.", assessment="understood")
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (model.model_dump_json(), "openai"))
    text, feedback, _, meta = tutor.tutor_reply(None,"정비례","왜 줄어드는지 설명해줘","수학")
    assert model.explanation in text and "정답 대신" not in text
    assert meta["hint"] is None and not meta["dialogue_state"]["evidence"]
    assert feedback["assessment"] == "unassessed"


@pytest.mark.parametrize("has_blank", [False, True])
def test_blank_instruction_matches_actual_exercise(has_blank):
    from app.rag.interaction_policy import normalize_question_format
    q = "빈칸에 알맞은 영어를 써 보세요. " + ("Because she ___ late." if has_blank else "Why did Mina run to school?")
    output = normalize_question_format(q)
    assert ("빈칸" in output) == has_blank
    assert ("___" in output) == has_blank
