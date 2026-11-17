import re
from collections import Counter

from sqlalchemy.orm import Session, joinedload

from app.database.config import settings
from app.models.chat import RoomChatMessage
from app.models.learning import LearningRoom
from app.rag.retriever import search, tokenize
from app.rag.tutor import generate_with_provider, source_summary

PARTICIPANT_MESSAGE_LIMIT = 3
PARTICIPANT_VIEW_CHARS = 800


def analyze_room_discussion(
    db: Session,
    room: LearningRoom,
    topic: str,
    unit_code: str | None = None,
    school_level: str | None = None,
    grade: str | None = None,
) -> dict:
    messages = (
        db.query(RoomChatMessage)
        .options(joinedload(RoomChatMessage.user))
        .filter(RoomChatMessage.room_id == room.id)
        .order_by(RoomChatMessage.created_at.desc())
        .limit(30)
        .all()
    )
    messages.reverse()
    by_user: dict[int, list[RoomChatMessage]] = {}
    for message in messages:
        by_user.setdefault(message.user_id, []).append(message)
    if len(by_user) < 2:
        raise ValueError("공동 하브루타 분석에는 서로 다른 두 명 이상의 의견이 필요합니다.")

    participant_views = []
    token_counter: Counter[str] = Counter()
    for user_messages in by_user.values():
        latest = user_messages[-1]
        # A participant's view often spans several messages (claim, then example
        # or follow-up). Using only the last one dropped the main claim.
        combined = " ".join(message.content.strip() for message in user_messages[-PARTICIPANT_MESSAGE_LIMIT:])
        token_counter.update(tokenize(combined))
        participant_views.append({
            "user_id": latest.user_id,
            "user_name": latest.user.name,
            "key_point": combined[:PARTICIPANT_VIEW_CHARS],
        })

    discussion_text = " ".join(message.content for message in messages[-12:])
    contexts = search(
        db,
        f"{topic} {discussion_text}",
        top_k=3,
        subject=room.subject,
        unit_code=unit_code,
        school_level=school_level,
        grade=grade,
    )
    common_terms = [term for term, count in token_counter.most_common(8) if count >= 2][:5]
    common_ground = (
        f"참여자들이 공통으로 언급한 핵심어는 {', '.join(common_terms)}입니다."
        if common_terms
        else "참여자들이 같은 주제를 서로 다른 표현으로 설명했습니다."
    )
    differences = " / ".join(
        f"{view['user_name']}: {view['key_point']}" for view in participant_views
    )
    next_question = next(
        (
            str(context.metadata.get("question"))
            for context in contexts
            if context.metadata.get("question") and str(context.metadata.get("question")) not in discussion_text
        ),
        f"각자의 설명을 근거로 ‘{topic}’을 새로운 예시에 적용하면 어떤 결론을 얻을 수 있을까요?",
    )
    context_text = "\n\n".join(context.content[:2500] for context in contexts)
    prompt = (
        f"교과목: {room.subject or '일반'}\n토론 주제: {topic}\n"
        f"참여자별 최근 의견:\n{differences}\n\n검색 근거:\n{context_text or '[검색 자료 없음]'}\n\n"
        "두 학생 의견의 공통점과 차이를 공정하게 비교하고, 잘한 점을 짧게 말한 뒤 "
        f"다음 토론 질문으로 반드시 다음 문장을 사용하세요: {next_question}\n"
        "각 참여자의 핵심 주장은 그 학생이 실제로 쓴 표현에 맞게 요약하고, 말하지 않은 주장을 덧붙이지 마세요. "
        "의견이 서로 갈리는 지점이 있으면 부드럽게 바꾸지 말고 무엇이 다른지 분명히 쓰세요. "
        "공통점이 없으면 억지로 만들지 마세요. 마크다운 기호 없이 문장으로 쓰세요."
    )
    generated, ai_provider = generate_with_provider(prompt, room.subject or "일반")
    if generated:
        # The UI shows plain text; turn markdown list markers into bullets.
        generated = re.sub(r"(?m)^\s*[-*]\s+", "• ", generated)
    summary = generated or (
        f"공통점: {common_ground}\n\n"
        f"관점 비교: {differences}\n\n"
        f"다음 토론 질문: {next_question}"
    )
    return {
        "topic": topic,
        "participant_count": len(participant_views),
        "participant_views": participant_views,
        "common_ground": common_ground,
        "summary": summary,
        "next_question": next_question,
        "response_meta": {
            "ai_provider": ai_provider,
            "retriever": contexts[0].metadata.get("retriever", "lexical") if contexts else "none",
            "grounded": bool(contexts),
            "curriculum_year": settings.rag_curriculum_year,
            "sources": [source_summary(context) for context in contexts],
        },
    }
