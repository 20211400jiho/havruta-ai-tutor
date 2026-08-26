import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import aiImage from "./assets/study_ai.png";
import CurriculumSelector from "./CurriculumSelector";
import "./StudyView.css";

export default function StudyView() {
  const [rooms, setRooms] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [curriculumSelection, setCurriculumSelection] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [ragStatus, setRagStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const selectedRoom = rooms.find((room) => String(room.id) === roomId);
  const selectedSubject = selectedRoom?.subject || "";
  const topic = curriculumSelection?.subject === selectedSubject ? curriculumSelection.topic : "";
  const currentRagStatus = ragStatus?.subject === selectedSubject ? ragStatus : null;

  useEffect(() => {
    api("/rooms").then((result) => {
      const loadedRooms = Array.isArray(result.rooms) ? result.rooms : [];
      setRooms(loadedRooms);
      if (loadedRooms.length) setRoomId(String(loadedRooms[0].id));
    }).catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);
  useEffect(() => {
    if (!selectedSubject) return undefined;
    let cancelled = false;
    api(`/rag/status?subject=${encodeURIComponent(selectedSubject)}`)
      .then((result) => { if (!cancelled) setRagStatus(result); })
      .catch(() => { if (!cancelled) setRagStatus(null); });
    return () => { cancelled = true; };
  }, [selectedSubject]);

  const startSession = async () => {
    if (!roomId) return setError("스터디룸 메뉴에서 학습방을 먼저 만들어주세요.");
    if (!topic) return setError("학습할 단원을 선택해주세요.");
    if (currentRagStatus?.available === false) return setError("선택한 과목의 RAG 자료가 아직 준비되지 않았습니다.");
    setLoading(true); setError(""); setFeedback(null);
    try {
      const result = await api("/sessions", {
        method: "POST",
        body: JSON.stringify({
          room_id: Number(roomId),
          topic,
          unit_code: curriculumSelection.unit.code,
        }),
      });
      if (!result?.session?.id || !Array.isArray(result.session.messages)) {
        throw new Error("학습 세션 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.");
      }
      setSessionId(result.session.id);
      setMessages(result.session.messages);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const send = async (event) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    setMessages((current) => [...current, { id: `local-${Date.now()}`, sender_type: "user", content }]);
    setInput(""); setLoading(true); setError("");
    try {
      const result = await api(`/sessions/${sessionId}/messages`, { method: "POST", body: JSON.stringify({ content }) });
      if (!result?.message || typeof result.message.content !== "string") {
        throw new Error("AI 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.");
      }
      setMessages((current) => [...current, result.message]);
      setFeedback(result.feedback);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const finish = async () => {
    setLoading(true);
    try {
      await api(`/sessions/${sessionId}/finish`, { method: "POST" });
      setSessionId(null); setMessages([]); setFeedback(null);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  if (!sessionId) return (
    <main className="study-start-card">
      <span className="study-kicker">AI 하브루타 튜터</span>
      <h2>설명하고, 질문받고, 다시 생각해보세요.</h2>
      <label>학습방<select value={roomId} onChange={(e) => { setRoomId(e.target.value); setCurriculumSelection(null); }}><option value="">학습방 선택</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.title} · {room.subject || "일반"}</option>)}</select></label>
      <label>교과목<input value={selectedRoom?.subject || "학습방을 선택하세요"} readOnly /></label>
      <CurriculumSelector
        subject={selectedSubject}
        preferredGrade={selectedRoom?.grade || ""}
        onSelectionChange={setCurriculumSelection}
        disabled={loading}
      />
      {currentRagStatus && !currentRagStatus.available && (
        <p className="rag-notice">현재 {currentRagStatus.curriculum_year} 교육과정의 {currentRagStatus.subject} RAG 자료는 등록되지 않았습니다. 자료를 추가할 때까지 일반 하브루타 질문으로 진행됩니다.</p>
      )}
      {error && <p className="study-error">{error}</p>}
      <button onClick={startSession} disabled={loading || !topic || currentRagStatus?.available === false}>{loading ? "준비 중..." : "선택한 단원으로 학습 시작"}</button>
    </main>
  );

  return (
    <div className="study-chat-container">
      <header className="study-chat-header"><div><strong>{topic}</strong><span> · {currentRagStatus?.available ? `${currentRagStatus.curriculum_year} 성취기준 연계 RAG 기반` : "일반 하브루타"} 학습</span></div><button onClick={finish} disabled={loading}>학습 종료</button></header>
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message-row ${message.sender_type}`}>
            {message.sender_type === "ai" && <img src={aiImage} alt="AI" className="ai-avatar" />}
            <div className="bubble">{(typeof message.content === "string" ? message.content : "메시지를 표시할 수 없습니다.").split("\n").map((line, index) => <p key={index}>{line || <br />}</p>)}</div>
          </div>
        ))}
        {loading && <div className="message-row ai"><img src={aiImage} alt="AI" className="ai-avatar" /><div className="bubble">생각을 정리하고 있어요...</div></div>}
        <div ref={bottomRef} />
      </div>
      {feedback && <div className="feedback-strip"><strong>최근 평가 {feedback.score}점</strong><span>{feedback.strengths}</span></div>}
      {error && <p className="study-error">{error}</p>}
      <form className="chat-input-bar" onSubmit={send}><input value={input} onChange={(e) => setInput(e.target.value)} maxLength={5000} placeholder="내 생각과 풀이 과정을 입력하세요..." /><button className="send-btn" disabled={loading || !input.trim()} aria-label="전송">➤</button></form>
    </div>
  );
}
