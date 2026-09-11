import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import aiImage from "./assets/study_ai.png";
import CurriculumSelector from "./CurriculumSelector";
import { ACTIVE_SESSION_KEY, getClientValue, removeClientValue, setClientValue } from "./clientStorage";
import "./StudyView.css";

export default function StudyView() {
  const [rooms, setRooms] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [curriculumSelection, setCurriculumSelection] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [openSessions, setOpenSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [messageMeta, setMessageMeta] = useState({});
  const [responseMeta, setResponseMeta] = useState(null);
  const [learningReport, setLearningReport] = useState(null);
  const [completedReport, setCompletedReport] = useState(null);
  const [ragStatus, setRagStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const selectedRoom = rooms.find((room) => String(room.id) === roomId);
  const selectedSubject = selectedRoom?.subject || "";
  const topic = curriculumSelection?.subject === selectedSubject ? curriculumSelection.topic : "";
  const displayedTopic = activeSession?.topic || topic;
  const currentRagStatus = ragStatus?.subject === selectedSubject ? ragStatus : null;

  useEffect(() => {
    Promise.all([api("/rooms"), api("/sessions")]).then(async ([roomResult, sessionResult]) => {
      const loadedRooms = Array.isArray(roomResult.rooms) ? roomResult.rooms : [];
      const resumable = (Array.isArray(sessionResult.sessions) ? sessionResult.sessions : [])
        .filter((session) => session.state !== "finished");
      setRooms(loadedRooms);
      setOpenSessions(resumable);
      if (loadedRooms.length) setRoomId(String(loadedRooms[0].id));
      const storedId = Number(getClientValue(ACTIVE_SESSION_KEY));
      const storedSession = resumable.find((session) => session.id === storedId);
      if (storedSession) {
        const restored = await api(`/sessions/${storedSession.id}`);
        setSessionId(restored.session.id);
        setActiveSession(restored.session);
        setRoomId(String(restored.session.room_id));
        setMessages(restored.session.messages || []);
        setMessageMeta(metadataByMessage(restored.session.messages || []));
        setResponseMeta(restored.response_meta || null);
        setLearningReport(restored.session.learning_report || null);
      } else {
        removeClientValue(ACTIVE_SESSION_KEY);
      }
    }).catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => {
    const target = bottomRef.current;
    if (typeof target?.scrollIntoView !== "function") return;
    try {
      target.scrollIntoView({ behavior: "smooth" });
    } catch {
      target.scrollIntoView();
    }
  }, [messages]);
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
          school_level: curriculumSelection.schoolLevel,
          grade: curriculumSelection.grade,
        }),
      });
      if (!result?.session?.id || !Array.isArray(result.session.messages)) {
        throw new Error("학습 세션 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.");
      }
      setSessionId(result.session.id);
      setActiveSession(result.session);
      setClientValue(ACTIVE_SESSION_KEY, String(result.session.id));
      setLearningReport(result.session.learning_report || null);
      setCompletedReport(null);
      setOpenSessions((current) => [result.session, ...current.filter((item) => item.id !== result.session.id)]);
      setMessages(result.session.messages);
      const firstMessage = result.session.messages[0];
      if (firstMessage?.id && result.response_meta) setMessageMeta({ [firstMessage.id]: result.response_meta });
      setResponseMeta(result.response_meta || null);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const resumeSession = async (targetSession) => {
    setLoading(true); setError(""); setFeedback(null); setMessageMeta({});
    try {
      const result = await api(`/sessions/${targetSession.id}`);
      if (!result?.session?.id || !Array.isArray(result.session.messages)) {
        throw new Error("저장된 학습 대화를 불러오지 못했습니다.");
      }
      setSessionId(result.session.id);
      setActiveSession(result.session);
      setRoomId(String(result.session.room_id));
      setLearningReport(result.session.learning_report || null);
      setCompletedReport(null);
      setMessages(result.session.messages);
      setMessageMeta(metadataByMessage(result.session.messages));
      setResponseMeta(result.response_meta || null);
      setClientValue(ACTIVE_SESSION_KEY, String(result.session.id));
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const send = async (event) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    const localId = `local-${Date.now()}`;
    setMessages((current) => [...current, { id: localId, sender_type: "user", content }]);
    setInput(""); setLoading(true); setError("");
    try {
      const result = await api(`/sessions/${sessionId}/messages`, { method: "POST", body: JSON.stringify({ content }) });
      if (!result?.message || typeof result.message.content !== "string") {
        throw new Error("AI 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.");
      }
      setMessages((current) => [...current, {
        ...result.message,
        sender_type: typeof result.message.sender_type === "string" ? result.message.sender_type : "ai",
        content: result.message.content,
      }]);
      setFeedback(result.feedback && typeof result.feedback === "object" ? result.feedback : null);
      setLearningReport(result.learning_report || null);
      if (result.message.id && result.response_meta) {
        setMessageMeta((current) => ({ ...current, [result.message.id]: result.response_meta }));
      }
      setResponseMeta(result.response_meta || null);
    } catch (requestError) {
      setMessages((current) => current.filter((message) => message.id !== localId));
      setInput(content);
      setError(`${requestError.message} 입력 내용은 복구했습니다.`);
    }
    finally { setLoading(false); }
  };

  const finish = async () => {
    setLoading(true);
    try {
      const result = await api(`/sessions/${sessionId}/finish`, { method: "POST" });
      setCompletedReport(result.learning_report || learningReport);
      setOpenSessions((current) => current.filter((item) => item.id !== sessionId));
      removeClientValue(ACTIVE_SESSION_KEY);
      setSessionId(null); setActiveSession(null); setMessages([]); setFeedback(null); setMessageMeta({}); setResponseMeta(null);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  if (!sessionId) return (
    <main className="study-start-card">
      {completedReport && <section aria-label="지난 학습 결과"><h2>이번 학습 돌아보기</h2><LearningReport report={completedReport} finished /><p>결과는 정리노트에서도 다시 볼 수 있어요.</p></section>}
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
      {openSessions.length > 0 && <section className="resume-sessions"><strong>이어할 학습</strong>{openSessions.slice(0, 3).map((session) => <button type="button" key={session.id} onClick={() => resumeSession(session)} disabled={loading}><span>{session.topic || "하브루타 학습"}</span><small>{session.school_level || ""} {session.grade || ""} · 대화 이어가기</small></button>)}</section>}
      {currentRagStatus && !currentRagStatus.available && (
        <p className="rag-notice">현재 {currentRagStatus.curriculum_year} 교육과정의 {currentRagStatus.subject} RAG 자료가 등록되지 않아 학습을 시작할 수 없습니다.</p>
      )}
      {error && <p className="study-error">{error}</p>}
      <button onClick={startSession} disabled={loading || !topic || currentRagStatus?.available === false}>{loading ? "준비 중..." : "선택한 단원으로 학습 시작"}</button>
    </main>
  );

  return (
    <div className="study-chat-container">
      <header className="study-chat-header"><div><strong>{displayedTopic}</strong><span> · {currentRagStatus?.available ? `${currentRagStatus.curriculum_year} 성취기준 연계 RAG 기반` : "일반 하브루타"} 학습</span><small>현재 단계: {responseMeta?.stage || "개념 설명"}</small></div><button onClick={finish} disabled={loading}>학습 종료</button></header>
      <LearningReport report={learningReport} />
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={`${message.sender_type}-${message.id ?? index}`} className={`message-row ${message.sender_type}`}>
            {message.sender_type === "ai" && <img src={aiImage} alt="AI" className="ai-avatar" />}
            <div className="message-content-wrap">
              <div className="bubble"><span>{typeof message.content === "string" ? message.content : "메시지를 표시할 수 없습니다."}</span></div>
              {message.sender_type === "ai" && messageMeta[message.id] && <EvidencePanel meta={messageMeta[message.id]} />}
            </div>
          </div>
        ))}
        {loading && <div className="message-row ai"><img src={aiImage} alt="AI" className="ai-avatar" /><div className="bubble"><span>생각을 정리하고 있어요...</span></div></div>}
        <div ref={bottomRef} />
      </div>
      {feedback && <div className="feedback-strip"><div><strong>설명 수준 {formatFeedback(feedback.level, "분석 중")}</strong><span>{formatFeedback(feedback.strengths, "피드백을 확인해보세요.")}</span></div>{feedback.assessment ? <div className="rubric-scores"><span>AI의 잠정 피드백 · 정답률이 아닙니다</span></div> : <div className="rubric-scores"><span>개념 {feedback.rubric?.concept ?? "-"}/40</span><span>근거 {feedback.rubric?.reasoning ?? "-"}/30</span><span>명료성 {feedback.rubric?.clarity ?? "-"}/20</span><span>참여 {feedback.rubric?.engagement ?? "-"}/10</span></div>}</div>}
      {error && <p className="study-error">{error}</p>}
      <form className="chat-input-bar" onSubmit={send}><input value={input} onChange={(e) => setInput(e.target.value)} maxLength={5000} placeholder="내 생각과 풀이 과정을 입력하세요..." /><button className="send-btn" disabled={loading || !input.trim()} aria-label="전송">➤</button></form>
    </div>
  );
}

function EvidencePanel({ meta }) {
  const providerLabel = { openai: "OpenAI 생성", rule: "규칙 기반 폴백", question_template: "RAG 질문 구성" }[meta.ai_provider] || "응답 구성";
  const retrieverLabel = { chroma: "ChromaDB 의미 검색", lexical: "어휘 검색 폴백", none: "검색 근거 없음" }[meta.retriever] || meta.retriever;
  return <details className="evidence-panel"><summary>{providerLabel} · {retrieverLabel} · 참고 자료 {meta.sources?.length || 0}개</summary><div className="evidence-list">{(meta.sources || []).map((source) => <article key={source.source_id}><strong>{source.achievement_standard || `${source.subject || "교과"} 자료`}</strong><p>{source.excerpt}</p><small>{source.school_level || ""} {source.grade || ""} · {{ bm25_rrf: "BM25 재정렬", cross_encoder: "Cross-Encoder 재정렬" }[source.reranker] || "검색 자료"}</small></article>)}{!meta.sources?.length && <p>현재 질문에 대한 검색 자료를 찾지 못했습니다. 답변의 사실 여부는 별도 확인이 필요합니다.</p>}{meta.dialogue_state && <p>학습 진행: {meta.dialogue_state.transition_reason}</p>}</div></details>;
}

function LearningReport({ report, finished = false }) {
  if (!report || !Array.isArray(report.objectives)) return null;
  return <details className="learning-report" open={finished}>
    <summary>학습목표와 진행 · {report.checked_count}/{report.total_count}개 항목 AI 확인</summary>
    <p className="learning-goal">{report.learning_goal}</p>
    <ol>{report.objectives.map((item) => <li key={item.stage}>
      <span>{item.description}</span><strong>{item.status === "ai_checked" ? "AI 확인" : "미확인"}</strong>
      {finished && item.evidence_quote && <blockquote>{item.evidence_quote}</blockquote>}
    </li>)}</ol>
    {finished && <div className="explanation-comparison">
      <div><strong>처음 설명</strong><p>{report.first_explanation || "작성한 설명이 없습니다."}</p></div>
      <div><strong>마지막 설명</strong><p>{report.has_comparison ? report.latest_explanation : "비교할 두 번째 설명이 아직 없습니다."}</p></div>
    </div>}
    {report.misconception && <p>다시 확인할 개념: {report.misconception}</p>}
    <p>다음 복습: {report.next_review}</p><small>{report.notice}</small>
  </details>;
}

function formatFeedback(value, fallback) {
  if (typeof value === "string" || typeof value === "number") return value;
  return fallback;
}

function metadataByMessage(messages) {
  return Object.fromEntries(
    messages
      .filter((message) => message.id && message.response_meta)
      .map((message) => [message.id, message.response_meta]),
  );
}
