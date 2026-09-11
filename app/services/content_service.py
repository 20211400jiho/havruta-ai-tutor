import random
import re

from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.models.study_content import Quiz, QuizQuestion, StudyNote
from app.rag.retriever import search
from app.rag.dialogue import learning_report


class QuizSourceNotFoundError(ValueError):
    pass


def _unique_text(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def create_note_for_session(db: Session, session: ChatSession) -> StudyNote:
    existing = db.query(StudyNote).filter(StudyNote.session_id == session.id).first()
    if existing:
        return existing
    ordered_messages = sorted(session.messages, key=lambda item: (item.created_at, item.id))
    report = learning_report([{"sender_type": message.sender_type, "content": message.content,
                               "response_meta": message.response_meta_json} for message in ordered_messages],
                             session.topic or "학습")
    user_messages = [message.content.strip() for message in session.messages if message.sender_type == "user"]
    scores = [feedback.score for feedback in session.feedbacks if feedback.score is not None]
    average = round(sum(scores) / len(scores)) if scores else None
    strengths = _unique_text([feedback.strengths for feedback in session.feedbacks])
    improvements = _unique_text([feedback.improvements for feedback in session.feedbacks])
    followups = _unique_text([feedback.followup_question for feedback in session.feedbacks])
    standards: list[str] = []
    for message in session.messages:
        for source in (message.response_meta_json or {}).get("sources", []):
            if source.get("achievement_standard"):
                standards.append(source["achievement_standard"])
        for reference in message.rag_references:
            metadata = reference.chunk.metadata_json or {}
            standard = str(metadata.get("achievement_standard_2022") or "").strip()
            if standard:
                standards.append(standard)
    level = "우수" if average is not None and average >= 80 else "충분함" if average is not None and average >= 60 else "보완 필요" if average is not None else "미확인"
    content_lines = [
        f"# {session.topic or '학습'} 핵심 정리",
        "",
        "## 학습 개요",
        f"- 과목: {session.room.subject if session.room and session.room.subject else '학습'}",
        f"- 단원: {session.topic or '자유 학습'}",
        f"- 교육과정 단원 코드: {session.unit_code or '미지정'}",
        f"- 이번 대화의 학습목표: {report['learning_goal']}",
        "",
        "## 핵심 개념과 나의 설명",
        f"- 이번 학습의 핵심 주제는 ‘{session.topic or '학습 주제'}’입니다.",
        f"- 처음 설명: {report['first_explanation'] or '아직 설명을 작성하지 않았습니다.'}",
        f"- 마지막 설명: {report['latest_explanation'] or '아직 설명을 작성하지 않았습니다.'}",
        "- 위 기록은 설명 변화를 돌아보기 위한 자료이며 사전·사후 시험 점수가 아닙니다.",
        "",
        "## 잘한 점",
        *([f"- {item}" for item in strengths] or ["- 자신의 생각을 말로 표현하며 학습에 참여했습니다."]),
        "",
        "## 보완할 개념",
        *([f"- {item}" for item in improvements] or ["- 핵심 원리를 예시와 함께 다시 설명해보세요."]),
        "",
        "## 학습 결과",
        *[f"- {item['description']}: {'AI 확인' if item['status'] == 'ai_checked' else '미확인'}"
          + (f" / 학생 설명: {item['evidence_quote']}" if item['evidence_quote'] else "") for item in report["objectives"]],
        f"- {report['notice']}",
        *([f"- 과거 규칙 평가 기록: {level}, {average}점 (검증된 이해도 아님)"] if average is not None else []),
        f"- 다음 복습: {report['next_review']}",
        f"- 총 대화 메시지: {len(session.messages)}개",
        "",
        "## 2022 교육과정 근거",
        *([f"- {item}" for item in _unique_text(standards)] or [f"- 선택 단원 코드 {session.unit_code or '미지정'}를 기준으로 RAG 검색했습니다."]),
        "",
        "## 다시 생각할 질문",
        *([f"- {item}" for item in followups[-3:]] or ["- 핵심 원리를 다른 예시로 설명해보세요."]),
        "",
        "## 나의 답변 기록",
        *([f"- {message}" for message in user_messages] or ["- 작성한 답변이 없습니다."]),
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


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _answer_similarity(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"[가-힣A-Za-z0-9]+", left.lower()))
    right_tokens = set(re.findall(r"[가-힣A-Za-z0-9]+", right.lower()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _misconception_variants(answer: str) -> list[str]:
    replacements = (
        ("이상", "미만"), ("이하", "초과"), ("증가", "감소"), ("감소", "증가"),
        ("평행", "수직"), ("수직", "평행"), ("양수", "음수"), ("음수", "양수"),
        ("최대", "최소"), ("최소", "최대"), ("같", "다르"), ("포함", "제외"),
        ("가능", "불가능"), ("합", "차"), ("곱", "합"),
    )
    variants: list[str] = []
    for source, target in replacements:
        if source in answer:
            candidate = answer.replace(source, target, 1)
            if candidate != answer:
                variants.append(candidate)
    return _unique_text(variants)


def _distractors_for(correct: str, question: str, candidates: list[dict]) -> list[str]:
    ranked: list[tuple[float, str]] = []
    normalized_correct = _normalized_text(correct)
    normalized_question = _normalized_text(question)
    for item in candidates:
        answer = str(item.get("answer") or "").strip()
        other_question = str(item.get("question") or "").strip()
        if not answer or _normalized_text(answer) == normalized_correct:
            continue
        if _normalized_text(other_question) == normalized_question:
            continue
        similarity = _answer_similarity(correct, answer)
        if similarity >= 0.55:
            continue
        ranked.append((similarity, answer[:280]))
    ranked.sort(key=lambda item: item[0], reverse=True)
    distractors = _unique_text([answer for _, answer in ranked])[:3]
    for variant in _misconception_variants(correct):
        if len(distractors) == 3:
            break
        if variant not in distractors:
            distractors.append(variant[:280])
    return distractors[:3]


def generate_quiz(
    db: Session,
    user_id: int,
    topic: str,
    question_count: int,
    subject: str | None = None,
    unit_code: str | None = None,
    school_level: str | None = None,
    grade: str | None = None,
) -> Quiz:
    contexts = search(
        db,
        topic,
        max(question_count * 12, 40),
        subject,
        unit_code=unit_code,
        school_level=school_level,
        grade=grade,
    )
    candidates = [context for context in contexts if context.metadata.get("question") and context.metadata.get("answer")]
    if not candidates:
        raise QuizSourceNotFoundError("해당 주제와 일치하는 RAG 문제 자료가 없습니다.")

    question_rows: list[dict] = []
    candidate_rows = [
        {
            "question": context.metadata["question"],
            "answer": context.metadata["answer"].strip()[:280],
        }
        for context in candidates
    ]
    seen_questions: set[str] = set()
    for context in candidates:
        if len(question_rows) == question_count:
            break
        question = context.metadata["question"].strip()
        correct = context.metadata["answer"].strip()[:280]
        normalized_question = _normalized_text(question)
        if normalized_question in seen_questions:
            continue
        distractors = _distractors_for(correct, question, candidate_rows)
        if len(distractors) < 3:
            continue
        seen_questions.add(normalized_question)
        options = [correct, *distractors]
        random.Random(context.source_id).shuffle(options)
        question_rows.append(
            {
                "question": question,
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
