import { useState } from "react";
import { api } from "./api";
import MathText from "./MathText";

export default function InterruptedSessions({ sessions, suggestedId, loading, onResume, onRestart, onDelete }) {
  const [showAll, setShowAll] = useState(false);
  const [previews, setPreviews] = useState({});
  const [pendingId, setPendingId] = useState(null);
  const [errors, setErrors] = useState({});
  const preview = async (id) => {
    if (previews[id] || pendingId === id) return;
    setPendingId(id);
    setErrors((current) => ({ ...current, [id]: "" }));
    try {
      const result = await api(`/sessions/${id}`);
      setPreviews((current) => ({ ...current, [id]: result.session }));
    } catch (error) { setErrors((current) => ({ ...current, [id]: error.message })); }
    finally { setPendingId((current) => current === id ? null : current); }
  };
  if (!sessions.length) return null;
  return <section className="resume-sessions" aria-labelledby="resume-sessions-title">
    <div className="resume-heading"><h3 id="resume-sessions-title">멈췄던 배움, 다시 이어볼까요?</h3><span>{sessions.length}개</span></div>
    <p className="resume-intro">지난 대화와 확인된 학습목표는 그대로 남아 있어요.</p>
    {(showAll ? sessions : sessions.slice(0, 3)).map((session) => <article className="resume-session" key={session.id}>
      <div className="resume-session-top"><span>{session.subject || "학습"} · {session.school_level || ""} {session.grade || ""}</span><small>{session.id === suggestedId ? "최근 열었던 학습" : session.state === "paused" ? "저장 후 중단" : "미완료"}</small></div>
      <h4>{session.topic || "하브루타 학습"}</h4>
      <p className="resume-date">마지막 대화 {formatDate(session.last_activity_at || session.started_at)} · 내 답변 {session.answer_count || 0}회</p>
      <div className="resume-progress"><label htmlFor={`resume-progress-${session.id}`}>학습목표 AI 확인 <strong>{session.checked_count || 0}/{session.total_count || 5}</strong></label><progress id={`resume-progress-${session.id}`} value={session.checked_count || 0} max={session.total_count || 5} /><span>현재 단계 · {session.stage || "개념 설명"}</span></div>
      {session.last_question && <p className="resume-question"><span>이어서 생각할 질문</span><MathText text={session.last_question} /></p>}
      <details className="resume-history" onToggle={(event) => { if (event.currentTarget.open) preview(session.id); }}><summary>지난 대화 보기</summary>
        {errors[session.id] ? <p role="alert">{errors[session.id]} <button type="button" onClick={() => preview(session.id)}>다시 불러오기</button></p>
          : previews[session.id] ? <ol>{previews[session.id].messages.map((message) => <li key={message.id}><strong>{message.sender_type === "user" ? "나 🙋" : "하루 🦉"}</strong><p><MathText text={message.content} /></p></li>)}</ol>
          : <p role="status">저장된 대화를 불러오고 있어요.</p>}
      </details>
      <div className="resume-actions"><button type="button" disabled={loading || session.can_resume === false} onClick={() => onResume(session)}>이어서 학습</button><button type="button" className="resume-restart" disabled={loading || session.can_restart === false} onClick={() => onRestart(session)}>처음부터 다시</button></div>
      {session.can_resume === false && <p className="resume-intro">이 학습방은 더 이상 이용할 수 없어 기록만 볼 수 있어요.</p>}
      {session.can_delete && <button type="button" className="resume-delete" disabled={loading} onClick={() => onDelete(session)}>기록 삭제</button>}
    </article>)}
    {sessions.length > 3 && <button type="button" className="resume-show-all" onClick={() => setShowAll(!showAll)}>{showAll ? "최근 3개만 보기" : `중단된 학습 ${sessions.length}개 모두 보기`}</button>}
    <small className="resume-notice">AI 확인은 대화에서 수집한 잠정적 이해 근거이며, 시험 점수나 숙달도는 아니에요. 처음부터 다시 시작해도 기존 기록은 삭제하지 않아요.</small>
  </section>;
}

function formatDate(value) {
  if (!value) return "날짜 미상";
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  const date = new Date(utc);
  return Number.isNaN(date.getTime()) ? "날짜 미상" : date.toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
