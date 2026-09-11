from app.rag.dialogue import DialogueState, STAGES, TutorTurn, apply_assessment, learning_report


def test_repeated_final_review_keeps_all_objective_evidence():
    state = DialogueState(learning_goal="기관의 구성 설명", focus_question="기관은 무엇인가요?", last_intent="answer")
    for _ in range(7):
        turn = TutorTurn(explanation="설명 확인", next_question="다른 예시는 무엇인가요?",
                         assessment="understood", evidence_quote="여러 조직", reasoning="조직과 기관을 연결함",
                         misconception="", source_ids=["source-1"])
        apply_assessment(state, turn, "여러 조직", {"source-1"})
    assert {item["stage"] for item in state.evidence} == set(STAGES)
    report = learning_report([{"sender_type": "ai", "response_meta": {"dialogue_state": state.model_dump()}}], "생물")
    assert report["checked_count"] == 5
    assert report["learning_goal"] == "기관의 구성 설명"


def test_no_evidence_is_unchecked_not_failure_and_hints_are_not_explanations():
    report = learning_report([{"sender_type": "user", "content": "몰라"},
                              {"sender_type": "user", "content": "네"}], "생물")
    assert report["checked_count"] == 0
    assert report["first_explanation"] is None
    assert all(item["status"] == "not_checked" for item in report["objectives"])


def test_finish_persists_report_in_note_and_can_be_reopened(client, auth_headers):
    room = client.post("/rooms", headers=auth_headers, json={"title": "보고서 테스트", "subject": "수학"}).json()["room"]
    session = client.post("/sessions", headers=auth_headers,
                          json={"room_id": room["id"], "topic": "직선의 방정식"}).json()["session"]
    for text in ["두 점이 같아요.", "몰라", "왜냐하면 두 점의 x좌표가 같아 y축에 평행합니다."]:
        result = client.post(f"/sessions/{session['id']}/messages", headers=auth_headers, json={"content": text})
        assert result.status_code == 200
        assert result.json()["feedback"]["score"] is None
    result = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers).json()
    report = result["learning_report"]
    assert report["has_comparison"] is True
    assert report["first_explanation"] == "두 점이 같아요."
    assert report["latest_explanation"].startswith("왜냐하면")
    assert report["checked_count"] == 0
    note = client.get(f"/notes/{result['note_id']}", headers=auth_headers).json()["note"]["content"]
    assert "처음 설명: 두 점이 같아요." in note
    assert "분석 점수 평균" not in note
    assert "미확인" in note
    repeated = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers).json()
    assert repeated["learning_report"] == report
    assert repeated["note_id"] == result["note_id"]


def test_other_users_cannot_read_learning_report(client, auth_headers):
    room = client.post("/rooms", headers=auth_headers, json={"title": "비공개", "subject": "수학"}).json()["room"]
    session = client.post("/sessions", headers=auth_headers,
                          json={"room_id": room["id"], "topic": "수학"}).json()["session"]
    other = client.post("/auth/signup", json={"email": "report-other@example.com", "password": "strong-password", "name": "다른 학생"}).json()
    assert client.get(f"/sessions/{session['id']}", headers={"Authorization": f"Bearer {other['access_token']}"}).status_code == 403
