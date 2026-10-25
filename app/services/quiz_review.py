"""Review saved quiz answers without changing scores or making another AI call."""
from app.models.study_content import Quiz, QuizAttempt, QuizQuestion


def question_review(question: QuizQuestion, selected_index: int) -> dict:
    correct = question.options[question.correct_index]
    selected = question.options[selected_index]
    is_correct = selected_index == question.correct_index
    explanations = question.option_explanations or []
    reason = explanations[selected_index] if selected_index < len(explanations) else None
    # Legacy quizzes keep their original source explanation; do not invent why an
    # old distractor was authored when that provenance was never saved.
    if not isinstance(reason, str) or not reason.strip():
        reason = (
            f"이 문제에서 묻는 내용은 ‘{question.question}’입니다. "
            f"고른 보기 ‘{selected}’는 자료가 제시하는 답 ‘{correct}’와 다릅니다. "
            "아래 정답 해설을 기준으로 두 설명을 비교해보세요."
        )
    return {
        "question_id": question.id,
        "selected_index": selected_index,
        "selected_answer": selected,
        "correct_index": question.correct_index,
        "correct_answer": correct,
        "is_correct": is_correct,
        "wrong_reason": None if is_correct else reason,
        "explanation": question.explanation or correct,
        "review_tip": "문제의 핵심 조건을 찾고, 정답인 이유를 자신의 말로 한 문장으로 설명해보세요.",
    }


def attempt_review(quiz: Quiz, attempt: QuizAttempt) -> dict:
    if (len(attempt.answers) != len(quiz.questions)
            or any(type(answer) is not int or not 0 <= answer < len(question.options)
                   for question, answer in zip(quiz.questions, attempt.answers))):
        raise ValueError("이전 답안의 선택지 정보를 확인할 수 없습니다. 퀴즈를 다시 풀어주세요.")
    results = [question_review(question, answer) for question, answer in zip(quiz.questions, attempt.answers)]
    return {
        "attempt_id": attempt.id,
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "correct_count": sum(item["is_correct"] for item in results),
        "total_questions": attempt.total_questions,
        "results": results,
    }
