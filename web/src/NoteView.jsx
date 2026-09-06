import { useEffect, useState } from "react";
import { api } from "./api";
import "./NoteView.css";

export default function NoteView() {
  const [notes, setNotes] = useState([]);
  const [selectedNote, setSelectedNote] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => { api("/notes").then((result) => setNotes(result.notes)).catch((requestError) => setError(requestError.message)); }, []);
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
    <main className="content note-page"><div className="notion-page-container"><div className="content-item-actions"><button className="back-btn" disabled={busy} onClick={() => setSelectedNote(null)}>← 목록으로 돌아가기</button><button className="content-delete" disabled={busy} onClick={() => deleteNote(selectedNote)}>{busy ? "처리 중..." : "노트 삭제"}</button></div>{error && <p className="study-error" role="alert">{error}</p>}<div className="notion-content">
      <span className="badge" style={{ backgroundColor: "#dbeafe" }}>{selectedNote.subject || "학습"}</span><h1>{selectedNote.title}</h1><p className="meta-info">{new Date(selectedNote.created_at).toLocaleDateString()}에 작성됨</p><div className="divider" />
      <div className="page-body">{(selectedNote.sections || []).map((section) => <section key={section.title} className="note-section"><h2>{section.title}</h2><ul>{section.items.map((item, index) => <li key={`${section.title}-${index}`}>{item}</li>)}</ul></section>)}</div>
    </div></div></main>
  );
  return (
    <main className="content note-page"><div className="note-header"><div><h2>정리노트</h2><p>완료한 AI 학습 세션에서 자동 생성됩니다.</p></div></div>
      {error && <p className="study-error" role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}<div className="note-grid">{notes.map((note) => <article key={note.id} className="note-card"><button className="note-open" disabled={busy} onClick={() => openNote(note.id)}><h3>{note.title}</h3><span className="badge" style={{ backgroundColor: "#dbeafe" }}>{note.subject || "학습"}</span></button><button className="content-delete" disabled={busy} aria-label={`${note.title} 노트 삭제`} onClick={() => deleteNote(note)}>노트 삭제</button></article>)}</div>
      {!notes.length && !error && <p>학습 세션을 완료하면 첫 정리노트가 만들어집니다.</p>}
    </main>
  );
}
