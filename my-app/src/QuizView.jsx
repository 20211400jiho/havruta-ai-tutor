import { useEffect, useState } from "react";
import { api } from "./api";
import "./QuizView.css";

export default function QuizView() {
  const [quizzes, setQuizzes] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [topic, setTopic] = useState("직선의 방정식");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = () => api("/quizzes").then((data) => setQuizzes(data.quizzes)).catch((requestError) => setError(requestError.message));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setLoading(true); setError("");
    try { await api("/quizzes", { method: "POST", body: JSON.stringify({ topic, question_count: 3 }) }); await load(); }
    catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  const start = async (id) => {
    setLoading(true); setResult(null);
    try { const data = await api(`/quizzes/${id}`); setQuiz(data.quiz); setAnswers(Array(data.quiz.questions.length).fill(null)); }
    catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  const submit = async () => {
    if (answers.some((answer) => answer === null)) return setError("모든 문제에 답해주세요.");
    setLoading(true); setError("");
    try { setResult(await api(`/quizzes/${quiz.id}/submit`, { method: "POST", body: JSON.stringify({ answers }) })); await load(); }
    catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  if (quiz) return (
    <main className="content"><div className="quiz-container"><div className="quiz-header"><button className="btn-back" onClick={() => { setQuiz(null); setResult(null); }}>← 목록으로</button><h2>{quiz.title}</h2></div>
      {quiz.questions.map((question, questionIndex) => <section key={question.id} className="quiz-question-block"><h3>Q{questionIndex + 1}. {question.question}</h3><div className="quiz-options">{question.options.map((option, optionIndex) => {
        const resultItem = result?.results?.[questionIndex];
        const optionClass = resultItem && optionIndex === resultItem.correct_index ? "correct" : resultItem && answers[questionIndex] === optionIndex ? "incorrect" : "";
        return <button key={optionIndex} className={`quiz-option ${optionClass}`} disabled={Boolean(result)} onClick={() => setAnswers(answers.map((value, index) => index === questionIndex ? optionIndex : value))}><span className="option-number">{optionIndex + 1}</span>{option}{answers[questionIndex] === optionIndex && " ✓"}</button>;
      })}</div>{resultItemText(result?.results?.[questionIndex])}</section>)}
      {result ? <div className="quiz-result"><strong>{result.score}점</strong> · {result.correct_count}/{result.total_questions}문제 정답</div> : <button className="btn-next" onClick={submit} disabled={loading}>채점하기</button>}{error && <p className="study-error">{error}</p>}
    </div></main>
  );
  return (
    <main className="content"><div className="quiz-list-header"><div><h2 className="quiz-main-title">AI 복습 퀴즈</h2><p className="quiz-main-sub">AITraining 수학 자료에서 근거가 있는 문제를 생성합니다.</p></div><div className="quiz-generate-form"><input value={topic} onChange={(e) => setTopic(e.target.value)} /><button className="btn-generate-quiz" onClick={generate} disabled={loading}>{loading ? "생성 중..." : "✨ 새 퀴즈"}</button></div></div>
      {error && <p className="study-error">{error}</p>}<div className="quiz-grid">{quizzes.map((item) => <div key={item.id} className="quiz-history-card"><div className="card-top"><span className="quiz-card-date">{new Date(item.created_at).toLocaleDateString()}</span><span className="quiz-card-count">{item.total_questions}문항</span></div><h3 className="quiz-card-title">{item.title}</h3><p>최고 점수: {item.best_score ?? "미응시"}</p><button className="btn-quiz-start" onClick={() => start(item.id)}>풀기 ➔</button></div>)}</div>
      {!quizzes.length && !error && <p>새 퀴즈를 생성해보세요.</p>}
    </main>
  );
}

function resultItemText(item) {
  return item ? <p className={item.is_correct ? "quiz-explanation correct-text" : "quiz-explanation"}>{item.is_correct ? "정답입니다. " : "다시 확인해보세요. "}{item.explanation}</p> : null;
}
