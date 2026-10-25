import { useEffect, useState } from "react";
import { api } from "./api";
import CurriculumSelector from "./CurriculumSelector";
import QuizReview from "./QuizReview";
import "./QuizView.css";

const SUBJECT_OPTIONS = ["국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"];

export default function QuizView() {
  const [quizzes, setQuizzes] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [wrongOnly, setWrongOnly] = useState(false);
  const [curriculumSelection, setCurriculumSelection] = useState(null);
  const [subject, setSubject] = useState("수학");
  const [questionCount, setQuestionCount] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const topic = curriculumSelection?.subject === subject ? curriculumSelection.topic : "";
  const load = () => api("/quizzes").then((data) => setQuizzes(data.quizzes)).catch((requestError) => setError(requestError.message));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setLoading(true); setError(""); setNotice("");
    try {
      if (!topic) throw new Error("퀴즈 단원을 선택해주세요.");
      const data = await api("/quizzes", {
        method: "POST",
        body: JSON.stringify({
          subject,
          topic,
          unit_code: curriculumSelection.unit.code,
          school_level: curriculumSelection.schoolLevel,
          grade: curriculumSelection.grade,
          question_count: questionCount,
        }),
      });
      const actualCount = data.quiz.total_questions;
      setNotice(actualCount < questionCount
        ? `선택한 ${questionCount}문항 중 자료가 충분한 ${actualCount}문항을 생성했어요.`
        : `${actualCount}문항 퀴즈를 생성했어요.`);
      await load();
    }
    catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  const start = async (id, review = false) => {
    setLoading(true); setError(""); setNotice("");
    try {
      const [data, savedResult] = await Promise.all([api(`/quizzes/${id}`), review ? api(`/quizzes/${id}/review`) : Promise.resolve(null)]);
      setQuiz(data.quiz);
      setResult(savedResult);
      setWrongOnly(false);
      setAnswers(savedResult ? savedResult.results.map((item) => item.selected_index) : Array(data.quiz.questions.length).fill(null));
    }
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

  const deleteQuiz = async (item) => {
    if (loading || !window.confirm(`“${item.title}” 퀴즈를 삭제할까요?\n문제와 해당 퀴즈의 응시 기록이 함께 삭제되며 복구할 수 없습니다.`)) return;
    setLoading(true); setError(""); setNotice("");
    try {
      const data = await api(`/quizzes/${item.id}`, { method: "DELETE" });
      setQuizzes((current) => current.filter((entry) => entry.id !== item.id));
      if (quiz?.id === item.id) { setQuiz(null); setAnswers([]); setResult(null); }
      setNotice(data.message);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const wrongCount = result ? result.total_questions - result.correct_count : 0;
  if (quiz) return (
    <main className="content quiz-page"><div className="quiz-container"><div className="quiz-header"><button className="btn-back" disabled={loading} onClick={() => { setQuiz(null); setResult(null); }}>← 목록으로</button><h2>{quiz.title}</h2><button className="content-delete" disabled={loading} onClick={() => deleteQuiz(quiz)}>퀴즈 삭제</button></div>
      {result && <div className="quiz-review-toolbar"><p role="status">{result.correct_count}/{result.total_questions}문항 정답 · 복습할 오답 {wrongCount}개</p><label><input type="checkbox" checked={wrongOnly} onChange={(event) => setWrongOnly(event.target.checked)} />오답만 보기</label><button type="button" className="btn-back" disabled={loading} onClick={() => { setResult(null); setAnswers(Array(quiz.questions.length).fill(null)); setWrongOnly(false); }}>다시 풀기</button></div>}
      {wrongOnly && wrongCount === 0 && <p className="quiz-all-correct">모두 맞혔어요. ‘오답만 보기’를 해제하면 정답 해설을 볼 수 있어요.</p>}
      {quiz.questions.map((question, questionIndex) => (!wrongOnly || !result?.results?.[questionIndex]?.is_correct) && <section key={question.id} className="quiz-question-block"><h3>Q{questionIndex + 1}. {question.question}</h3><div className="quiz-options">{question.options.map((option, optionIndex) => {
        const resultItem = result?.results?.[questionIndex];
        const selected = answers[questionIndex] === optionIndex;
        const optionClass = resultItem && optionIndex === resultItem.correct_index ? "correct" : resultItem && selected ? "incorrect" : selected ? "selected" : "";
        return <button type="button" key={optionIndex} className={`quiz-option ${optionClass}`} disabled={loading || Boolean(result)} aria-pressed={selected} onClick={() => setAnswers((current) => current.map((value, index) => index === questionIndex ? optionIndex : value))}><span className="option-number">{optionIndex + 1}</span><span>{option}</span>{resultItem && optionIndex === resultItem.correct_index ? <small className="quiz-option-label">{selected ? "내 선택 · 정답" : "정답"}</small> : selected && <small className="quiz-option-label">{resultItem ? "내 선택 · 오답" : "내 선택"}</small>}</button>;
      })}</div><QuizReview item={result?.results?.[questionIndex]} /></section>)}
      {result ? <div className="quiz-result"><strong>{result.score}점</strong> · {result.correct_count}/{result.total_questions}문제 정답</div> : <button className="btn-next" onClick={submit} disabled={loading}>채점하기</button>}{error && <p className="study-error">{error}</p>}
    </div></main>
  );
  return (
    <main className="content quiz-page"><div className="quiz-list-header"><div><h2 className="quiz-main-title">2022 교육과정 RAG 퀴즈</h2><p className="quiz-main-sub">과목과 단원, 문항 수를 선택하세요. 해당 단원의 학습 자료에서 문제를 생성합니다.</p></div><div className="quiz-subject-action"><label>교과목<select aria-label="퀴즈 과목" value={subject} disabled={loading} onChange={(e) => { setSubject(e.target.value); setCurriculumSelection(null); }}>{SUBJECT_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label><label>문항 수<select aria-label="퀴즈 문항 수" value={questionCount} disabled={loading} onChange={(e) => setQuestionCount(Number(e.target.value))}>{[3, 5, 10].map((count) => <option key={count} value={count}>{count}문항</option>)}</select></label><button className="btn-generate-quiz" onClick={generate} disabled={loading || !topic}>{loading ? "생성 중..." : `${questionCount}문항 퀴즈 만들기`}</button></div></div><CurriculumSelector subject={subject} onSelectionChange={setCurriculumSelection} disabled={loading} compact />
      {error && <p className="study-error">{error}</p>}{notice && <p role="status">{notice}</p>}<div className="quiz-grid">{quizzes.map((item) => <div key={item.id} className="quiz-history-card"><div className="card-top"><span className="quiz-card-date">{new Date(item.created_at).toLocaleDateString()}</span><span className="quiz-card-count">{item.total_questions}문항</span></div><h3 className="quiz-card-title">{item.title}</h3><p>최고 점수: {item.best_score ?? "미응시"}</p><div className="content-item-actions"><button className="btn-quiz-start" disabled={loading} onClick={() => start(item.id)}>풀기 ➔</button>{item.attempt_count > 0 && <button className="btn-quiz-start" disabled={loading} onClick={() => start(item.id, true)}>지난 답안·해설</button>}<button className="content-delete" disabled={loading} aria-label={`${item.title} 퀴즈 삭제`} onClick={() => deleteQuiz(item)}>퀴즈 삭제</button></div></div>)}</div>
      {!quizzes.length && !error && <p>새 퀴즈를 생성해보세요.</p>}
    </main>
  );
}
