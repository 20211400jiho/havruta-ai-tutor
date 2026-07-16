// NoteView.jsx
import React, { useState } from 'react';
import './NoteView.css';

export default function NoteView() {
  const [notes, setNotes] = useState([
    { id: 1, title: "광합성 핵심 요약", category: "과학", date: "2024.08.20", fullContent: "광합성은 빛 에너지를 이용하여 이산화탄소와 물을 포도당과 산소로 바꾸는 과정입니다.\n\n### 1. 주요 과정\n- 빛 에너지 흡수: 엽록체에서 발생\n- 화학 반응: 6CO2 + 6H2O → C6H12O6 + 6O2\n\n결과적으로 식물은 생존에 필요한 에너지를 얻고, 산소를 배출합니다." },
    { id: 2, title: "이차함수 정리", category: "수학", date: "2024.08.19", fullContent: "이차함수의 기본형은 y = ax² + bx + c 입니다.\n\na의 부호에 따라 그래프의 모양이 달라집니다.\n- a > 0 : 아래로 볼록\n- a < 0 : 위로 볼록" },
  ]);

  const [selectedNote, setSelectedNote] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);

  const categoryColors = { "과학": "#dcfce7", "수학": "#dbeafe", "역사": "#fef3c7", "국어": "#fce7f3" };

  // 상세 페이지 렌더링 (Notion 스타일)
  const renderDetailView = (note) => (
    <div className="notion-page-container">
      <button className="back-btn" onClick={() => setSelectedNote(null)}>← 목록으로 돌아가기</button>
      
      <div className="notion-content">
        <span className="badge" style={{ backgroundColor: categoryColors[note.category] || "#f1f5f9" }}>{note.category}</span>
        <h1>{note.title}</h1>
        <p className="meta-info">{note.date}에 작성됨</p>
        <div className="divider"></div>
        <div className="page-body">
          {/* 실제 내용이 들어갈 곳 */}
          {note.fullContent.split('\n').map((line, i) => <p key={i}>{line}</p>)}
        </div>
      </div>
    </div>
  );

  return (
    <main className="content note-page">
      {selectedNote ? renderDetailView(selectedNote) : (
        <>
          <div className="note-header">
            <h2>정리노트</h2>
            <button className={`btn-edit ${isEditMode ? 'active' : ''}`} onClick={() => setIsEditMode(!isEditMode)}>
              {isEditMode ? "완료" : "수정"}
            </button>
          </div>
          
          <div className="note-grid">
            {notes.map(note => (
              <div key={note.id} className="note-card" onClick={() => setSelectedNote(note)}>
                {isEditMode && <button className="delete-btn" onClick={(e) => { e.stopPropagation(); setNotes(notes.filter(n => n.id !== note.id)); }}>×</button>}
                <h3>{note.title}</h3>
                <span className="badge" style={{ backgroundColor: categoryColors[note.category] }}>{note.category}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}