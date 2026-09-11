"""Check deployed RAG + three real AI turns + restore + learning report.

Creates one synthetic test account/room, leaves its finished note for inspection,
and closes only that test room. Calls the deployed OpenAI integration three times.
"""
import json
import os
import secrets
from time import perf_counter

import httpx


def main():
    url = os.getenv("HAVRUTA_API_URL", "http://127.0.0.1:8000").rstrip("/")
    run_id = secrets.token_hex(6)
    with httpx.Client(base_url=url, timeout=90) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        auth = request("POST", "/auth/signup", json={
            "email": f"goals-smoke-{run_id}@example.com", "password": secrets.token_urlsafe(24),
            "name": "배포 검증용 가상 학생", "grade": "중학교 2학년",
        })
        client.headers["Authorization"] = f"Bearer {auth['access_token']}"
        scope = {"subject": "과학", "school_level": "중학교", "grade": "2학년", "unit_code": "9과02"}
        search = request("POST", "/rag/search", json={**scope, "query": "여러 조직이 모인 기관의 구성", "top_k": 3})
        assert search["results"], "No real RAG documents"
        assert all(item["metadata"].get("reranker") == "bm25_rrf" for item in search["results"])
        room = request("POST", "/rooms", json={"title": f"배포 검증 {run_id}", "subject": "과학", "grade": "중학교 2학년"})["room"]
        session = request("POST", "/sessions", json={
            "room_id": room["id"], "topic": "생물의 구성과 다양성",
            **{key: value for key, value in scope.items() if key != "subject"},
        })["session"]
        goal = session["learning_report"]["learning_goal"]
        turns = []
        for text in ["몰라", "아직 잘 모르겠어. 쉬운 예시로 설명해줘.",
                     "조직은 비슷한 기능의 세포가 모인 것이고, 기관은 여러 조직이 모여 특정 기능을 하는 구조입니다."]:
            start = perf_counter()
            result = request("POST", f"/sessions/{session['id']}/messages", json={"content": text})
            meta = result["response_meta"]
            assert meta["ai_provider"] == "openai", "Actual OpenAI did not respond"
            assert meta["retriever"] == "chroma"
            assert meta["dialogue_state"]["learning_goal"] == goal
            if len(turns) < 2:
                assert meta["stage"] == "개념 설명"
                assert meta["dialogue_state"]["hint_count"] == len(turns) + 1
            assert result["feedback"]["score"] is None
            turns.append({"student": text, "reply": result["message"]["content"],
                          "stage": meta["stage"], "assessment": meta["dialogue_state"]["assessment"],
                          "elapsed_seconds": round(perf_counter() - start, 2)})
        restored = request("GET", f"/sessions/{session['id']}")
        assert restored["response_meta"]["dialogue_state"] == meta["dialogue_state"]
        finished = request("POST", f"/sessions/{session['id']}/finish")
        assert len(finished["learning_report"]["objectives"]) == 5
        note = request("GET", f"/notes/{finished['note_id']}")["note"]
        assert "이번 대화의 학습목표" in note["content"] and "처음 설명" in note["content"]
        repeated = request("POST", f"/sessions/{session['id']}/finish")
        assert repeated["learning_report"] == finished["learning_report"]
        request("DELETE", f"/rooms/{room['id']}")
        print(json.dumps({"result": "PASS", "api": url, "session_id": session["id"],
                          "note_id": note["id"], "goal": goal, "reranker": "bm25_rrf",
                          "turns": turns, "restored": True, "finished_report": True,
                          "scope": "synthetic smoke test, not measured learning effectiveness"},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
