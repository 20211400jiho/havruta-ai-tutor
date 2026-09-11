"""Run the complete presentation flow against a running Havruta API."""

import json
import os
from datetime import datetime
from time import time
from urllib.parse import urlparse, urlunparse

import httpx
from websockets.sync.client import connect


API_URL = os.getenv("HAVRUTA_API_URL", "http://127.0.0.1:8000").rstrip("/")


def websocket_url(room_id: int) -> str:
    parsed = urlparse(API_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, f"/chat/ws/{room_id}", "", "", ""))


def send_room_message(room_id: int, token: str, content: str) -> None:
    with connect(websocket_url(room_id), open_timeout=20, close_timeout=10) as websocket:
        websocket.send(json.dumps({"type": "authenticate", "token": token}))
        assert json.loads(websocket.recv())["type"] == "authenticated"
        assert json.loads(websocket.recv())["type"] == "presence"
        websocket.send(json.dumps({"content": content}, ensure_ascii=False))
        event = json.loads(websocket.recv())
        assert event["type"] == "message"
        assert event["message"]["content"] == content


def signup(client: httpx.Client, email: str, name: str) -> tuple[str, dict]:
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "smoke-password", "name": name, "grade": "고등학교 1학년"},
    )
    response.raise_for_status()
    payload = response.json()
    return payload["access_token"], {"Authorization": f"Bearer {payload['access_token']}"}


def main() -> None:
    stamp = int(time())
    with httpx.Client(base_url=API_URL, timeout=90) as client:
        live = client.get("/health/live")
        live.raise_for_status()
        ready = client.get("/health/ready")
        ready.raise_for_status()
        assert ready.json()["database"]["ready"] is True
        assert ready.json()["rag"]["ready"] is True

        owner_token, owner_headers = signup(client, f"smoke-owner-{stamp}@example.com", "발표 점검 학생1")
        partner_token, partner_headers = signup(client, f"smoke-partner-{stamp}@example.com", "발표 점검 학생2")
        room_response = client.post(
            "/rooms",
            headers=owner_headers,
            json={"title": "발표 점검 공동 하브루타", "subject": "수학", "grade": "고등학교 1학년", "max_members": 2},
        )
        room_response.raise_for_status()
        room = room_response.json()["room"]
        joined = client.post("/rooms/join", headers=partner_headers, json={"invite_code": room["invite_code"]})
        joined.raise_for_status()

        send_room_message(room["id"], owner_token, "두 점의 x좌표가 같으면 직선은 y축과 평행합니다.")
        send_room_message(room["id"], partner_token, "이때 기울기를 정의할 수 없다는 점도 확인해야 합니다.")
        discussion = client.post(
            f"/chat/rooms/{room['id']}/ai-feedback",
            headers=owner_headers,
            json={
                "topic": "직선의 방정식",
                "unit_code": "10공수2-01",
                "school_level": "고등학교",
                "grade": "1학년",
            },
        )
        discussion.raise_for_status()
        assert discussion.json()["participant_count"] == 2

        session = client.post(
            "/sessions",
            headers=owner_headers,
            json={
                "room_id": room["id"],
                "topic": "직선의 방정식",
                "unit_code": "10공수2-01",
                "school_level": "고등학교",
                "grade": "1학년",
            },
        )
        session.raise_for_status()
        assert session.json()["response_meta"]["sources"]
        session_id = session.json()["session"]["id"]
        answer = client.post(
            f"/sessions/{session_id}/messages",
            headers=owner_headers,
            json={"content": "두 점의 x좌표가 같으므로 이 직선은 y축과 평행하며 기울기는 정의되지 않습니다."},
        )
        answer.raise_for_status()
        answer_payload = answer.json()
        assert answer_payload["response_meta"]["grounded"] is True
        assert answer_payload["response_meta"]["dialogue_state"]["learning_goal"]
        assert len(answer_payload["learning_report"]["objectives"]) == 5
        assert answer_payload["feedback"]["score"] is None

        finish = client.post(f"/sessions/{session_id}/finish", headers=owner_headers)
        finish.raise_for_status()
        note = client.get(f"/notes/{finish.json()['note_id']}", headers=owner_headers)
        note.raise_for_status()
        assert len(note.json()["note"]["sections"]) >= 6

        quiz = client.post(
            "/quizzes",
            headers=owner_headers,
            json={
                "subject": "수학",
                "topic": "직선의 방정식",
                "unit_code": "10공수2-01",
                "school_level": "고등학교",
                "grade": "1학년",
                "question_count": 3,
            },
        )
        quiz.raise_for_status()
        quiz_detail = client.get(f"/quizzes/{quiz.json()['quiz']['id']}", headers=owner_headers)
        quiz_detail.raise_for_status()
        questions = quiz_detail.json()["quiz"]["questions"]
        assert questions and all(len(set(question["options"])) == 4 for question in questions)

        dashboard = client.get("/dashboard/me", headers=owner_headers)
        dashboard.raise_for_status()
        now = datetime.now()
        calendar = client.get(
            f"/dashboard/calendar?year={now.year}&month={now.month}",
            headers=owner_headers,
        )
        calendar.raise_for_status()
        assert any(event["notes"] for event in calendar.json()["events"])

        print(json.dumps({
            "result": "PASS",
            "api": API_URL,
            "health": ready.json()["status"],
            "rag_provider": answer_payload["response_meta"]["retriever"],
            "ai_provider": answer_payload["response_meta"]["ai_provider"],
            "rag_sources": len(answer_payload["response_meta"]["sources"]),
            "feedback_level": answer_payload["feedback"]["level"],
            "collaboration_participants": discussion.json()["participant_count"],
            "note_sections": len(note.json()["note"]["sections"]),
            "quiz_questions": len(questions),
            "completed_units": dashboard.json()["summary"]["completed_units"],
            "calendar_events": len(calendar.json()["events"]),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
