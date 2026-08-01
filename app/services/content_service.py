import random

from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.models.study_content import Quiz, QuizQuestion, StudyNote
from app.services.rag_service import search


def create_note_for_session(db: Session, session: ChatSession) -> StudyNote:
    existing = db.query(StudyNote).filter(StudyNote.session_id == session.id).first()
    if existing:
        return existing
    user_messages = [message.content for message in session.messages if message.sender_type == "user"]
    scores = [feedback.score for feedback in session.feedbacks if feedback.score is not None]
    average = round(sum(scores) / len(scores)) if scores else None
    content_lines = [
        f"# {session.topic or '학습'} 핵심 정리",
        "",
        "## 내가 설명한 내용",
        *([f"- {message}" for message in user_messages] or ["- 아직 작성한 답변이 없습니다."]),
        "",
        "## 학습 결과",
        f"- AI 평가 평균: {average if average is not None else '-'}점",
        f"- 총 대화 메시지: {len(session.messages)}개",
        "",
        "## 다시 생각할 질문",
        *([f"- {feedback.followup_question}" for feedback in session.feedbacks[-3:]] or ["- 핵심 원리를 다른 예시로 설명해보세요."]),
    ]
    note = StudyNote(
        user_id=session.user_id,
        session_id=session.id,
        title=f"{session.topic or '학습'} 핵심 정리",
        subject=session.room.subject if session.room else None,
        content="\n".join(content_lines),
    )
    db.add(note)
    db.flush()
    return note


def generate_quiz(db: Session, user_id: int, topic: str, question_count: int) -> Quiz:
    contexts = search(db, topic, max(question_count, 5))
    candidates = [context for context in contexts if context.metadata.get("question") and context.metadata.get("answer")]
    if not candidates:
        candidates = [context for context in search(db, "직선 기울기 평행", 10) if context.metadata.get("answer")]
    quiz = Quiz(user_id=user_id, title=f"{topic} 복습 퀴즈", subject="수학")
    db.add(quiz)
    db.flush()
    all_answers = list(dict.fromkeys(context.metadata["answer"] for context in candidates))
    fallback_answers = ["조건만으로는 알 수 없다.", "항상 x축과 평행하다.", "원점을 반드시 지난다."]
    for context in candidates[:question_count]:
        correct = context.metadata["answer"]
        distractors = [answer for answer in all_answers + fallback_answers if answer != correct][:3]
        options = [correct, *distractors]
        random.Random(context.source_id).shuffle(options)
        db.add(
            QuizQuestion(
                quiz_id=quiz.id,
                question=context.metadata["question"],
                options=options,
                correct_index=options.index(correct),
                explanation=context.metadata.get("description") or correct,
            )
        )
    db.commit()
    db.refresh(quiz)
    return quiz
