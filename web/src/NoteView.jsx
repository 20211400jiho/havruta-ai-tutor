import { useEffect, useState } from "react";
import { api } from "./api";
import { getNoteSummary } from "./noteSummary";
import "./NoteView.css";

const formatDate = (value) => {
  if (!value) return "날짜 미기록";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 미기록" : date.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
};

function NoteText({ text }) {
  const [expanded, setExpanded] = useState(false);
  const long = text.length > 200;
  return <div className="note-text">
    <p className={long && !expanded ? "note-text-preview" : ""}>{text}</p>
    {long && <button type="button" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>{expanded ? "접기" : "전체 내용 보기"}</button>}
  </div>;
}

function NoteDetail({ note }) {
  const summary = getNoteSummary(note);
  const checked = summary.objectives.filter((item) => item.checked).length;
  return (
    <article className="note-paper">
      <header className="note-detail-header">
        <div className="note-detail-meta"><span className="badge">{note.subject || "학습"}</span><span>{formatDate(note.created_at)}</span></div>
        <h1>{note.title}</h1>
        {summary.goal && <p className="note-goal"><span>오늘의 질문</span>{summary.goal}</p>}
      </header>

      <section className="note-takeaway" aria-labelledby="note-explanation-title">
        <h2 id="note-explanation-title">내가 남긴 핵심 설명</h2>
        <NoteText text={summary.explanation || "아직 남긴 설명이 없어요. 다음 학습에서는 내 생각을 한 문장으로 적어 보세요."} />
        <small>내 답변 기록이며, 정답으로 검증된 요약은 아니에요.</small>
      </section>

      <div className="note-summary-grid">
        <section className="note-summary-block">
          <h2><span aria-hidden="true">01</span> 잘한 점</h2>
          {summary.strengths.length ? <ul>{summary.strengths.map((item, index) => <li key={index}><NoteText text={item} /></li>)}</ul> : <p>저장된 피드백이 없어요.</p>}
        </section>
        <section className="note-summary-block note-review-block">
          <h2><span aria-hidden="true">02</span> 다음에 복습할 것</h2>
          <NoteText text={summary.review} />
          {summary.question && summary.question !== summary.review && <details className="note-review-question"><summary>복습 질문 보기</summary><p>{summary.question}</p></details>}
        </section>
      </div>

      {summary.hasProgress && <section className="note-progress" aria-label="학습 확인 기록">
        <div className="note-progress-heading"><h2>학습 확인</h2><span>{checked} / {summary.objectives.length}개 AI 확인</span></div>
        <ul>{summary.objectives.map((item) => <li key={item.stage} className={item.checked ? "is-checked" : ""}><span aria-hidden="true">{item.checked ? "✓" : "○"}</span>{item.stage}<span className="note-sr-only"> · {item.checked ? "AI 확인" : "아직 확인 전"}</span></li>)}</ul>
        <p className="note-caption">AI의 잠정 판단이에요. 미확인은 오답이 아니며, 학습효과나 단원 전체 숙달을 보장하지 않아요.</p>
      </section>}

      <details className="note-archive">
        <summary>전체 학습 기록 · 참고 자료<span>원문 보기</span></summary>
        <div className="note-archive-body">
          {(note.sections || []).map((section, sectionIndex) => <section key={sectionIndex} className="note-section"><h2>{section.title}</h2><ul>{(section.items || []).map((item, index) => <li key={index}>{item}</li>)}</ul></section>)}
          {!note.sections?.length && <p className="note-raw-content">{note.content || "저장된 내용이 없어요."}</p>}
        </div>
      </details>
    </article>
  );
}

export default function NoteView() {
  const [notes, setNotes] = useState([]);
  const [selectedNote, setSelectedNote] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api("/notes").then((result) => setNotes(result.notes)).catch((requestError) => setError(requestError.message)).finally(() => setLoading(false));
  }, []);

  const openNote = async (id) => {
    setBusy(true); setError(""); setNotice("");
    try { const result = await api(`/notes/${id}`); setSelectedNote(result.note); }
    catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  };
  const deleteNote = async (note) => {
    if (busy || !window.confirm(`“${note.title}” 정리노트를 삭제할까요?\n삭제한 노트는 복구할 수 없습니다. 학습 대화와 기록은 유지됩니다.`)) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await api(`/notes/${note.id}`, { method: "DELETE" });
      setNotes((current) => current.filter((item) => item.id !== note.id));
      setSelectedNote((current) => current?.id === note.id ? null : current);
      setNotice(data.message);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  };

  if (selectedNote) return (
    <main className="content note-page"><div className="note-detail-container">
      <div className="content-item-actions"><button className="back-btn" disabled={busy} onClick={() => setSelectedNote(null)}>← 노트 목록</button><button className="content-delete" disabled={busy} onClick={() => deleteNote(selectedNote)}>{busy ? "처리 중..." : "노트 삭제"}</button></div>
      {error && <p className="study-error" role="alert">{error}</p>}
      <NoteDetail key={selectedNote.id} note={selectedNote} />
    </div></main>
  );
  return (
    <main className="content note-page"><div className="note-library">
      <div className="note-header"><div><span className="note-eyebrow">나의 복습 기록</span><h2>정리노트</h2><p>내가 설명한 내용과 다음에 복습할 것을 한눈에.</p></div><span className="note-count">{notes.length}개</span></div>
      {error && <p className="study-error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {loading && <p role="status">노트를 불러오고 있어요.</p>}
      <div className="note-grid">{notes.map((note) => <article key={note.id} className="note-card">
        <button className="note-open" disabled={busy} onClick={() => openNote(note.id)}><span className="badge">{note.subject || "학습"}</span><h3>{note.title}</h3><span className="note-card-date">{formatDate(note.created_at)}</span></button>
        <div className="note-card-footer"><span>정리노트</span><button className="content-delete" disabled={busy} aria-label={`${note.title} 노트 삭제`} onClick={() => deleteNote(note)}>삭제</button></div>
      </article>)}</div>
      {!loading && !notes.length && !error && <p className="note-empty">학습을 마치면 정리노트가 자동으로 만들어져요.</p>}
    </div></main>
  );
}
