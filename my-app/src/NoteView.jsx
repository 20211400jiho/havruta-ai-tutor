import { useEffect, useState } from "react";
import { api } from "./api";
import "./NoteView.css";

export default function NoteView() {
  const [notes, setNotes] = useState([]);
  const [selectedNote, setSelectedNote] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api("/notes").then((result) => setNotes(result.notes)).catch((requestError) => setError(requestError.message)); }, []);
  const openNote = async (id) => {
    try { const result = await api(`/notes/${id}`); setSelectedNote(result.note); }
    catch (requestError) { setError(requestError.message); }
  };
  if (selectedNote) return (
    <main className="content note-page"><div className="notion-page-container"><button className="back-btn" onClick={() => setSelectedNote(null)}>← 목록으로 돌아가기</button><div className="notion-content">
      <span className="badge" style={{ backgroundColor: "#dbeafe" }}>{selectedNote.subject || "학습"}</span><h1>{selectedNote.title}</h1><p className="meta-info">{new Date(selectedNote.created_at).toLocaleDateString()}에 작성됨</p><div className="divider" />
      <div className="page-body">{(selectedNote.sections || []).map((section) => <section key={section.title} className="note-section"><h2>{section.title}</h2><ul>{section.items.map((item, index) => <li key={`${section.title}-${index}`}>{item}</li>)}</ul></section>)}</div>
    </div></div></main>
  );
  return (
    <main className="content note-page"><div className="note-header"><div><h2>정리노트</h2><p>완료한 AI 학습 세션에서 자동 생성됩니다.</p></div></div>
      {error && <p className="study-error">{error}</p>}<div className="note-grid">{notes.map((note) => <button key={note.id} className="note-card" onClick={() => openNote(note.id)}><h3>{note.title}</h3><span className="badge" style={{ backgroundColor: "#dbeafe" }}>{note.subject || "학습"}</span></button>)}</div>
      {!notes.length && !error && <p>학습 세션을 완료하면 첫 정리노트가 만들어집니다.</p>}
    </main>
  );
}
