import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import CurriculumSelector from "./CurriculumSelector";
import LearningReport from "./LearningReport";
import { ACTIVE_SESSION_KEY, getClientValue, removeClientValue, setClientValue } from "./clientStorage";
import "./StudyView.css";

const SUBJECTS = ["국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"];

export default function StudyView({ user }) {
  const [selectedSubject, setSelectedSubject] = useState("");
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
  const topic = curriculumSelection?.subject === selectedSubject ? curriculumSelection.topic : "";
  const displayedTopic = activeSession?.topic || topic;
  const currentRagStatus = ragStatus?.subject === selectedSubject ? ragStatus : null;

  useEffect(() => {
    api("/sessions").then(async (sessionResult) => {
      const resumable = (Array.isArray(sessionResult.sessions) ? sessionResult.sessions : [])
        .filter((session) => session.state !== "finished");
      setOpenSessions(resumable);
      const storedId = Number(getClientValue(ACTIVE_SESSION_KEY));
      const storedSession = resumable.find((session) => session.id === storedId);
      if (storedSession) {
        const restored = await api(`/sessions/${storedSession.id}`);
        setSessionId(restored.session.id);
        setActiveSession(restored.session);
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
    if (!topic) return setError("학습할 단원을 선택해주세요.");
    if (currentRagStatus?.available === false) return setError("선택한 과목의 RAG 자료가 아직 준비되지 않았습니다.");
    setLoading(true); setError(""); setFeedback(null);
    try {
      const personal = await api("/rooms/personal", {
        method: "POST",
        body: JSON.stringify({ subject: selectedSubject, grade: `${curriculumSelection.schoolLevel} ${curriculumSelection.grade}` }),
      });
      const result = await api("/sessions", {
        method: "POST",
        body: JSON.stringify({
          room_id: personal.room.id,
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
    <main className={`study-start-card${completedReport ? " study-start-card--with-report" : ""}`}>
      {completedReport && <section className="study-completed-report" aria-label="지난 학습 결과"><LearningReport report={completedReport} finished /></section>}
      <span className="study-kicker">혼자 학습하기 · 중·고등학생</span>
      <h2>{completedReport ? "다음으로 탐구할 단원은?" : "오늘은 무엇을 알아볼까요?"}</h2>
      <p className="study-intro">단원을 고르고 내 생각을 설명해보세요. AI가 질문을 이어갑니다.</p>
      <label>과목<select value={selectedSubject} disabled={loading} onChange={(e) => { setSelectedSubject(e.target.value); setCurriculumSelection(null); }}><option value="">과목 선택</option>{SUBJECTS.map((subject) => <option key={subject}>{subject}</option>)}</select></label>
      <CurriculumSelector
        subject={selectedSubject}
        preferredGrade={user?.grade || ""}
        onSelectionChange={setCurriculumSelection}
        disabled={loading}
      />
      {openSessions.length > 0 && <section className="resume-sessions"><strong>이어할 학습</strong>{openSessions.slice(0, 3).map((session) => <button type="button" key={session.id} onClick={() => resumeSession(session)} disabled={loading}><span>{session.topic || "하브루타 학습"}</span><small>{session.school_level || ""} {session.grade || ""} · 대화 이어가기</small></button>)}</section>}
      {currentRagStatus && !currentRagStatus.available && (
        <p className="rag-notice">{currentRagStatus.subject} 학습 자료를 준비 중입니다. 다른 과목을 선택해주세요.</p>
      )}
      {error && <p className="study-error">{error}</p>}
      <button onClick={startSession} disabled={loading || !topic || currentRagStatus?.available === false}>{loading ? "준비 중..." : "선택한 단원으로 학습 시작"}</button>
    </main>
  );

  return (
    <div className="study-chat-container">
      <header className="study-chat-header"><div><span className="study-kicker">나의 학습 노트</span><strong>{displayedTopic}</strong><small>{responseMeta?.stage || "개념 설명"} · AI와 생각 나누기</small></div><button onClick={finish} disabled={loading}>마치고 돌아보기</button></header>
      <LearningReport report={learningReport} />
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={`${message.sender_type}-${message.id ?? index}`} className={`message-row ${message.sender_type}`}>
            <div className="message-content-wrap">
              <span className="message-author">{message.sender_type === "ai" ? "하브루타 · AI" : "나의 생각"}</span>
              <div className="bubble"><span>{typeof message.content === "string" ? message.content : "메시지를 표시할 수 없습니다."}</span></div>
              {message.sender_type === "ai" && messageMeta[message.id] && <EvidencePanel meta={messageMeta[message.id]} />}
            </div>
          </div>
        ))}
        {loading && <div className="message-row ai" role="status"><div className="bubble"><span>생각을 정리하고 있어요...</span></div></div>}
        <div ref={bottomRef} />
      </div>
      {feedback && <div className="feedback-strip"><div><strong>설명 수준 {formatFeedback(feedback.level, "분석 중")}</strong><span>{formatFeedback(feedback.strengths, "피드백을 확인해보세요.")}</span></div>{feedback.assessment ? <div className="rubric-scores"><span>AI의 잠정 피드백 · 정답률이 아닙니다</span></div> : <div className="rubric-scores"><span>개념 {feedback.rubric?.concept ?? "-"}/40</span><span>근거 {feedback.rubric?.reasoning ?? "-"}/30</span><span>명료성 {feedback.rubric?.clarity ?? "-"}/20</span><span>참여 {feedback.rubric?.engagement ?? "-"}/10</span></div>}</div>}
      {error && <p className="study-error">{error}</p>}
      <form className="chat-input-bar" onSubmit={send}><textarea rows={2} aria-label="내 생각과 풀이 과정" value={input} onChange={(e) => setInput(e.target.value)} maxLength={5000} placeholder="내 생각과 그 이유를 적어보세요." /><button className="send-btn" disabled={loading || !input.trim()}>보내기</button></form>
    </div>
  );
}

function EvidencePanel({ meta }) {
  const providerLabel = { openai: "OpenAI 생성", rule: "규칙 기반 폴백", question_template: "RAG 질문 구성" }[meta.ai_provider] || "응답 구성";
  const retrieverLabel = { chroma: "ChromaDB 의미 검색", lexical: "어휘 검색 폴백", none: "검색 근거 없음" }[meta.retriever] || meta.retriever;
  return <details className="evidence-panel"><summary>{meta.sources?.length ? `참고한 학습 자료 ${meta.sources.length}개` : "참고 자료 없음 · 답변 확인 필요"}{meta.ai_provider === "rule" ? " · 기본 안내" : ""}</summary><div className="evidence-list">{(meta.sources || []).map((source) => <article key={source.source_id}><strong>{source.achievement_standard || `${source.subject || "교과"} 자료`}</strong><p>{source.excerpt}</p><small>{source.school_level || ""} {source.grade || ""}</small></article>)}{!meta.sources?.length && <p>현재 질문에 대한 검색 자료를 찾지 못했습니다. 답변의 사실 여부는 별도 확인이 필요합니다.</p>}<small>응답 정보: {providerLabel} · {retrieverLabel}</small></div></details>;
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
