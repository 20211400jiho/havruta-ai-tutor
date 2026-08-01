"""Run a real HTTP smoke test against the local API server."""

import json
from time import time

import httpx
from websockets.sync.client import connect


BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    email = f"smoke-{int(time())}@example.com"
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        health = client.get("/")
        health.raise_for_status()
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": "smoke-password", "name": "통합 테스트", "grade": "고1"},
        )
        signup.raise_for_status()
        headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
        room = client.post(
            "/rooms",
            headers=headers,
            json={"title": "통합 테스트방", "subject": "수학", "grade": "고1", "max_members": 2},
        )
        room.raise_for_status()
        room_id = room.json()["room"]["id"]
        token = signup.json()["access_token"]
        with connect(f"ws://127.0.0.1:8000/chat/ws/{room_id}") as websocket:
            websocket.send(json.dumps({"type": "authenticate", "token": token}))
            authenticated = json.loads(websocket.recv())
            assert authenticated["type"] == "authenticated"
            presence = json.loads(websocket.recv())
            assert presence["type"] == "presence"
            websocket.send(json.dumps({"content": "실제 서버 WebSocket 확인"}))
            chat_event = json.loads(websocket.recv())
            assert chat_event["type"] == "message"
        history = client.get(f"/chat/rooms/{room_id}/messages", headers=headers)
        history.raise_for_status()
        assert history.json()["messages"][-1]["content"] == "실제 서버 WebSocket 확인"
        session = client.post(
            "/sessions",
            headers=headers,
            json={"room_id": room_id, "topic": "직선의 방정식"},
        )
        session.raise_for_status()
        session_id = session.json()["session"]["id"]
        answer = client.post(
            f"/sessions/{session_id}/messages",
            headers=headers,
            json={"content": "두 점의 x좌표가 같으면 직선은 y축과 평행합니다."},
        )
        answer.raise_for_status()
        finish = client.post(f"/sessions/{session_id}/finish", headers=headers)
        finish.raise_for_status()
        notes = client.get("/notes", headers=headers)
        notes.raise_for_status()
        quiz = client.post(
            "/quizzes",
            headers=headers,
            json={"topic": "직선의 방정식", "question_count": 3},
        )
        quiz.raise_for_status()
        quiz_id = quiz.json()["quiz"]["id"]
        quiz_detail = client.get(f"/quizzes/{quiz_id}", headers=headers)
        quiz_detail.raise_for_status()
        question_count = len(quiz_detail.json()["quiz"]["questions"])
        quiz_result = client.post(
            f"/quizzes/{quiz_id}/submit",
            headers=headers,
            json={"answers": [0] * question_count},
        )
        quiz_result.raise_for_status()
        dashboard = client.get("/dashboard/me", headers=headers)
        dashboard.raise_for_status()
        print("health:", health.json()["status"])
        print("room:", room.json()["room"]["invite_code"])
        print("rag feedback score:", answer.json()["feedback"]["score"])
        print("completed sessions:", dashboard.json()["summary"]["completed_sessions"])
        print("generated notes:", notes.json()["count"])
        print("quiz questions:", question_count)
        print("room chat messages:", history.json()["count"])


if __name__ == "__main__":
    main()
