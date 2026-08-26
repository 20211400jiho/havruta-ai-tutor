import random

from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.models.study_content import Quiz, QuizQuestion, StudyNote
from app.services.rag_service import search


class QuizSourceNotFoundError(ValueError):
    pass


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
        f"- 응답 평가 평균: {average if average is not None else '-'}점",
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


def generate_quiz(
    db: Session,
    user_id: int,
    topic: str,
    question_count: int,
    subject: str | None = None,
    unit_code: str | None = None,
) -> Quiz:
    contexts = search(
        db,
        topic,
        max(question_count * 3, 10),
        subject,
        unit_code=unit_code,
    )
    candidates = [context for context in contexts if context.metadata.get("question") and context.metadata.get("answer")]
    if not candidates:
        raise QuizSourceNotFoundError("해당 주제와 일치하는 RAG 문제 자료가 없습니다.")

    all_answers = list(dict.fromkeys(context.metadata["answer"] for context in candidates))
    question_rows: list[dict] = []
    for context in candidates[:question_count]:
        correct = context.metadata["answer"]
        distractors = [answer for answer in all_answers if answer != correct][:3]
        if not distractors:
            continue
        options = [correct, *distractors]
        random.Random(context.source_id).shuffle(options)
        question_rows.append(
            {
                "question": context.metadata["question"],
                "options": options,
                "correct_index": options.index(correct),
                "explanation": context.metadata.get("description") or correct,
            }
        )
    if not question_rows:
        raise QuizSourceNotFoundError("선택지를 구성할 만큼 RAG 문제 자료가 충분하지 않습니다.")

    quiz_subject = subject or candidates[0].metadata.get("subject") or "자료 기반"
    quiz = Quiz(user_id=user_id, title=f"{topic} 복습 퀴즈", subject=quiz_subject)
    db.add(quiz)
    db.flush()
    for row in question_rows:
        db.add(QuizQuestion(quiz_id=quiz.id, **row))
    db.commit()
    db.refresh(quiz)
    return quiz
