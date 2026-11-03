import MathText from "./MathText";

export default function QuizReview({ item }) {
  if (!item) return null;
  return <section className={`quiz-review ${item.is_correct ? "quiz-review--correct" : ""}`} aria-label="문항 해설">
    <h4>{item.is_correct ? "정답이에요" : "어디서 헷갈렸는지 살펴볼까요?"}</h4>
    {!item.is_correct && <div className="quiz-review-part"><span>내가 고른 답 · {item.selected_index + 1}번</span><p><MathText text={item.selected_answer} /></p><p className="quiz-wrong-reason"><MathText text={item.wrong_reason || ""} /></p></div>}
    <div className="quiz-review-part quiz-review-answer"><span>정답 · {item.correct_index + 1}번</span><p><MathText text={item.correct_answer} /></p></div>
    <div className="quiz-review-part"><span>정답 해설</span><p><MathText text={item.explanation || ""} /></p></div>
    <p className="quiz-review-tip">다시 생각하기 · <MathText text={item.review_tip || ""} /></p>
  </section>;
}
