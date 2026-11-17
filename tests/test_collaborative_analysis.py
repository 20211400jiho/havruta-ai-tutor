from datetime import datetime, timedelta

from app.models.chat import RoomChatMessage
from app.models.learning import LearningRoom
from app.models.user import User
from app.services import collaborative_service
from conftest import TestSession

A_VIEW = "나는 헌법에 기본권이 적혀 있으니까 국가가 알아서 인권을 지켜줄 거라고 생각해."
B_CLAIM = "헌법에 기본권이 적혀 있어도 차별은 계속 일어나서 시민이 목소리를 내야 제도가 바뀌어. 저상버스가 그 예야."
B_FOLLOW = "그리고 국가 기관이 오히려 인권을 침해하는 경우도 있으니까 시민의 감시도 필요해."


def setup_room(db):
    users = [User(email=f"{name}@example.com", password_hash="x", name=name) for name in ("김", "이")]
    db.add_all(users)
    db.flush()
    room = LearningRoom(title="토론", subject="사회", owner_id=users[0].id, invite_code="TEST01")
    db.add(room)
    db.flush()
    start = datetime(2026, 11, 17, 12, 0)
    for minute, (user, text) in enumerate([(users[0], A_VIEW), (users[1], B_CLAIM), (users[1], B_FOLLOW)]):
        db.add(RoomChatMessage(room_id=room.id, user_id=user.id, content=text,
                               created_at=start + timedelta(minutes=minute)))
    db.commit()
    return room


def test_participant_view_keeps_earlier_claim_not_only_last_message(monkeypatch):
    prompts = []
    monkeypatch.setattr(collaborative_service, "generate_with_provider",
                        lambda prompt, subject: (prompts.append(prompt), ("- 김: 국가 책임\n- 이: 시민 참여", "openai"))[1])
    db = TestSession()
    try:
        result = collaborative_service.analyze_room_discussion(db, setup_room(db), "인권과 헌법")
    finally:
        db.close()
    views = {view["user_name"]: view["key_point"] for view in result["participant_views"]}
    assert "저상버스" in views["이"] and "감시" in views["이"]
    assert "저상버스" in prompts[0]
    assert "말하지 않은 주장을 덧붙이지 마세요" in prompts[0]
    assert result["summary"] == "• 김: 국가 책임\n• 이: 시민 참여"
