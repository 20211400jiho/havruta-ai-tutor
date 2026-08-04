import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import aiImage from "./assets/study_ai.png";
import "./StudyView.css";

export default function StudyView() {
  const [rooms, setRooms] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [topic, setTopic] = useState("직선의 방정식");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    api("/rooms").then((result) => {
      setRooms(result.rooms);
      if (result.rooms.length) setRoomId(String(result.rooms[0].id));
    }).catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  const startSession = async () => {
    if (!roomId) return setError("스터디룸 메뉴에서 학습방을 먼저 만들어주세요.");
    setLoading(true); setError(""); setFeedback(null);
    try {
      const result = await api("/sessions", { method: "POST", body: JSON.stringify({ room_id: Number(roomId), topic }) });
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
      <label>학습방<select value={roomId} onChange={(e) => setRoomId(e.target.value)}><option value="">학습방 선택</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.title}</option>)}</select></label>
      <label>오늘의 주제<input value={topic} onChange={(e) => setTopic(e.target.value)} /></label>
      {error && <p className="study-error">{error}</p>}
      <button onClick={startSession} disabled={loading}>{loading ? "준비 중..." : "학습 시작"}</button>
    </main>
  );

  return (
    <div className="study-chat-container">
      <header className="study-chat-header"><div><strong>{topic}</strong><span> · 근거 기반 하브루타 학습</span></div><button onClick={finish} disabled={loading}>학습 종료</button></header>
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message-row ${message.sender_type}`}>
            {message.sender_type === "ai" && <img src={aiImage} alt="AI" className="ai-avatar" />}
            <div className="bubble">{message.content.split("\n").map((line, index) => <p key={index}>{line || <br />}</p>)}</div>
          </div>
        ))}
        {loading && <div className="message-row ai"><img src={aiImage} alt="AI" className="ai-avatar" /><div className="bubble">생각을 정리하고 있어요...</div></div>}
        <div ref={bottomRef} />
      </div>
      {feedback && <div className="feedback-strip"><strong>최근 평가 {feedback.score}점</strong><span>{feedback.strengths}</span></div>}
      {error && <p className="study-error">{error}</p>}
      <form className="chat-input-bar" onSubmit={send}><input value={input} onChange={(e) => setInput(e.target.value)} placeholder="내 생각과 풀이 과정을 입력하세요..." /><button className="send-btn" disabled={loading}>➤</button></form>
    </div>
  );
}
