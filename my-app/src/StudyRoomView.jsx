import { useEffect, useRef, useState } from "react";
import { api, getToken, getWebSocketUrl } from "./api";
import CurriculumSelector from "./CurriculumSelector";
import "./StudyRoomView.css";

const SUBJECT_OPTIONS = ["국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"];

export default function StudyRoomView({ user }) {
  const [rooms, setRooms] = useState([]);
  const [title, setTitle] = useState("고1 수학 하브루타");
  const [subject, setSubject] = useState("수학");
  const [inviteCode, setInviteCode] = useState("");
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [curriculumSelection, setCurriculumSelection] = useState(null);
  const [discussionFeedback, setDiscussionFeedback] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const messagesEndRef = useRef(null);

  const load = () => api("/rooms")
    .then((result) => setRooms(result.rooms))
    .catch((requestError) => setError(requestError.message));

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!selectedRoom) return undefined;
    let cancelled = false;

    api(`/chat/rooms/${selectedRoom.id}/messages`)
      .then((result) => setMessages(result.messages))
      .catch((requestError) => setError(requestError.message));

    const connect = () => {
      if (cancelled) return;
      setConnectionStatus("connecting");
      const socket = new WebSocket(getWebSocketUrl(selectedRoom.id));
      socketRef.current = socket;

      socket.onopen = () => socket.send(JSON.stringify({ type: "authenticate", token: getToken() }));
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "authenticated") {
            setConnectionStatus("connected");
          } else if (payload.type === "message") {
            setMessages((current) => (
              current.some((message) => message.id === payload.message.id)
                ? current
                : [...current, payload.message]
            ));
          } else if (payload.type === "presence") {
            const action = payload.action === "joined" ? "입장했습니다." : "퇴장했습니다.";
            setNotice(`${payload.user_name}님이 ${action}`);
          } else if (payload.type === "error") {
            setError(payload.detail);
          }
        } catch {
          setError("채팅 메시지를 읽지 못했습니다.");
        }
      };
      socket.onerror = () => setConnectionStatus("error");
      socket.onclose = (event) => {
        socketRef.current = null;
        if (cancelled) return;
        if (event.code === 4401 || event.code === 4403) {
          setConnectionStatus("denied");
          setError(event.reason || "채팅방 연결 권한이 없습니다.");
          return;
        }
        setConnectionStatus("reconnecting");
        reconnectTimerRef.current = window.setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      cancelled = true;
      window.clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [selectedRoom]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const createRoom = async (event) => {
    event.preventDefault(); setError(""); setNotice("");
    try {
      const result = await api("/rooms", {
        method: "POST",
        body: JSON.stringify({ title, subject, grade: "고등학교 1학년", max_members: 4 }),
      });
      setNotice(`학습방을 만들었습니다. 초대 코드: ${result.room.invite_code}`);
      load();
    } catch (requestError) { setError(requestError.message); }
  };

  const joinRoom = async (event) => {
    event.preventDefault(); setError(""); setNotice("");
    try {
      const result = await api("/rooms/join", {
        method: "POST",
        body: JSON.stringify({ invite_code: inviteCode.toUpperCase() }),
      });
      setNotice(result.message); setInviteCode(""); load();
    } catch (requestError) { setError(requestError.message); }
  };

  const sendMessage = (event) => {
    event.preventDefault();
    const content = messageInput.trim();
    if (!content || socketRef.current?.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ content }));
    setMessageInput("");
  };

  const analyzeDiscussion = async () => {
    if (!curriculumSelection?.topic) return setError("공동 하브루타를 분석할 단원을 선택해주세요.");
    setAnalysisLoading(true); setError("");
    try {
      const result = await api(`/chat/rooms/${selectedRoom.id}/ai-feedback`, {
        method: "POST",
        body: JSON.stringify({
          topic: curriculumSelection.topic,
          unit_code: curriculumSelection.unit.code,
          school_level: curriculumSelection.schoolLevel,
          grade: curriculumSelection.grade,
        }),
      });
      setDiscussionFeedback(result);
    } catch (requestError) { setError(requestError.message); }
    finally { setAnalysisLoading(false); }
  };

  const connectionLabel = {
    connected: "연결됨",
    connecting: "연결 중",
    reconnecting: "재연결 중",
    error: "연결 오류",
    denied: "접근 거부",
    disconnected: "연결 안 됨",
  }[connectionStatus];

  if (selectedRoom) {
    return (
      <main className="study-room-page">
        <section className="chat-container room-chat-container">
          <header className="chat-header">
            <button className="back-button" onClick={() => setSelectedRoom(null)}>← 방 목록</button>
            <div><h2>{selectedRoom.title}</h2><p>{selectedRoom.subject} · {selectedRoom.grade}</p></div>
            <span className={`connection-status ${connectionStatus}`}>{connectionLabel}</span>
          </header>
          {notice && <div className="chat-notice">{notice}</div>}
          {error && <div className="room-error">{error}</div>}
          <section className="collaborative-panel">
            <div><strong>공동 하브루타 AI 분석</strong><p>두 명 이상이 의견을 남긴 뒤 단원을 선택해 비교·분석합니다.</p></div>
            <CurriculumSelector subject={selectedRoom.subject} preferredGrade={selectedRoom.grade} onSelectionChange={setCurriculumSelection} disabled={analysisLoading} compact />
            <button type="button" onClick={analyzeDiscussion} disabled={analysisLoading || !curriculumSelection?.topic}>{analysisLoading ? "의견 분석 중..." : "AI로 토론 비교하기"}</button>
            {discussionFeedback && <DiscussionFeedback result={discussionFeedback} />}
          </section>
          <div className="chat-messages">
            {messages.map((message) => {
              const isMine = message.user_id === user.id;
              return (
                <div key={message.id} className={`message-row ${isMine ? "user" : "friend"}`}>
                  <div className="message-content">
                    {!isMine && <span className="message-author">{message.user_name}</span>}
                    <div className="bubble">{message.content}</div>
                  </div>
                </div>
              );
            })}
            {!messages.length && <p className="empty-chat">첫 메시지를 보내 대화를 시작해보세요.</p>}
            <div ref={messagesEndRef} />
          </div>
          <form className="chat-input" onSubmit={sendMessage}>
            <input
              value={messageInput}
              onChange={(event) => setMessageInput(event.target.value)}
              maxLength={5000}
              placeholder="친구에게 메시지 보내기"
              disabled={connectionStatus !== "connected"}
            />
            <button disabled={connectionStatus !== "connected" || !messageInput.trim()}>전송</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="study-room-page">
      <div className="room-panel">
        <header><h2>스터디룸</h2><p>친구와 학습방을 공유하고 실시간으로 토론하세요.</p></header>
        <div className="room-actions">
          <form onSubmit={createRoom}>
            <h3>새 학습방</h3>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            <select value={subject} onChange={(event) => setSubject(event.target.value)}>
              {SUBJECT_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
            <button className="btn-primary">생성하기</button>
          </form>
          <form onSubmit={joinRoom}><h3>초대 코드 참여</h3><input value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} maxLength={6} placeholder="6자리 코드" required /><button className="btn-primary">참여하기</button></form>
        </div>
        {notice && <div className="room-notice">{notice}</div>}{error && <div className="room-error">{error}</div>}
        <section className="room-list"><h3>내 학습방 {rooms.length}개</h3>{rooms.map((room) => (
          <article key={room.id} className="room-item">
            <div><strong>{room.title}</strong><p>{room.subject} · {room.grade} · {room.member_count}/{room.max_members}명</p></div>
            <div className="room-item-actions">
              <button onClick={() => navigator.clipboard.writeText(room.invite_code)}>{room.invite_code} 복사</button>
              <button className="enter-room" onClick={() => { setError(""); setNotice(""); setSelectedRoom(room); }}>채팅 입장</button>
            </div>
          </article>
        ))}{!rooms.length && <p>아직 참여 중인 학습방이 없습니다.</p>}</section>
      </div>
    </main>
  );
}

function DiscussionFeedback({ result }) {
  const meta = result.response_meta || {};
  const provider = { openai: "OpenAI", rule: "규칙 기반 폴백" }[meta.ai_provider] || "AI";
  const retriever = { chroma: "ChromaDB", lexical: "어휘 검색 폴백", none: "근거 없음" }[meta.retriever] || meta.retriever;
  return <article className="discussion-feedback"><div className="discussion-meta">참여자 {result.participant_count}명 · {provider} · {retriever}</div><p>{result.summary}</p><details><summary>참여자 의견과 RAG 근거 보기</summary>{result.participant_views.map((view) => <p key={view.user_id}><strong>{view.user_name}</strong>: {view.key_point}</p>)}{(meta.sources || []).map((source) => <p key={source.source_id}><strong>{source.achievement_standard || source.subject}</strong><br />{source.excerpt}</p>)}</details></article>;
}
