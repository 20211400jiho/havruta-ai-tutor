import { useEffect, useState } from "react";
import { api } from "./api";
import "./QuizView.css";

const SUBJECT_OPTIONS = ["국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"];

export default function QuizView() {
  const [quizzes, setQuizzes] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [topic, setTopic] = useState("직선의 방정식");
  const [subject, setSubject] = useState("수학");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = () => api("/quizzes").then((data) => setQuizzes(data.quizzes)).catch((requestError) => setError(requestError.message));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setLoading(true); setError("");
    try { await api("/quizzes", { method: "POST", body: JSON.stringify({ subject, topic, question_count: 3 }) }); await load(); }
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
    <main className="content"><div className="quiz-list-header"><div><h2 className="quiz-main-title">2022 교육과정 RAG 퀴즈</h2><p className="quiz-main-sub">선택한 과목의 2022 성취기준 연계 자료에서만 문제를 생성합니다.</p></div><div className="quiz-generate-form"><select aria-label="퀴즈 과목" value={subject} onChange={(e) => setSubject(e.target.value)}>{SUBJECT_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select><input aria-label="퀴즈 주제" placeholder="자료에 있는 주제 입력" value={topic} onChange={(e) => setTopic(e.target.value)} /><button className="btn-generate-quiz" onClick={generate} disabled={loading || !topic.trim()}>{loading ? "생성 중..." : "새 퀴즈"}</button></div></div>
      {error && <p className="study-error">{error}</p>}<div className="quiz-grid">{quizzes.map((item) => <div key={item.id} className="quiz-history-card"><div className="card-top"><span className="quiz-card-date">{new Date(item.created_at).toLocaleDateString()}</span><span className="quiz-card-count">{item.total_questions}문항</span></div><h3 className="quiz-card-title">{item.title}</h3><p>최고 점수: {item.best_score ?? "미응시"}</p><button className="btn-quiz-start" onClick={() => start(item.id)}>풀기 ➔</button></div>)}</div>
      {!quizzes.length && !error && <p>새 퀴즈를 생성해보세요.</p>}
    </main>
  );
}

function resultItemText(item) {
  return item ? <p className={item.is_correct ? "quiz-explanation correct-text" : "quiz-explanation"}>{item.is_correct ? "정답입니다. " : "다시 확인해보세요. "}{item.explanation}</p> : null;
}
