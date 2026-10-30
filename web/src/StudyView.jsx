import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import CurriculumSelector from "./CurriculumSelector";
import LearningReport from "./LearningReport";
import MathText from "./MathText";
import InterruptedSessions from "./InterruptedSessions";
import { ACTIVE_SESSION_KEY, getClientValue, removeClientValue, setClientValue } from "./clientStorage";
import "./StudyView.css";

const AI_TUTOR_NAME = "하루";

const SUBJECTS = ["국어", "영어", "수학", "사회", "사회문화", "과학", "도덕", "기술가정", "정보"];
const HINT_REQUEST = "지금 질문에 대한 힌트를 주세요.";

export default function StudyView({ user }) {
  const [selectedSubject, setSelectedSubject] = useState("");
  const [curriculumSelection, setCurriculumSelection] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [openSessions, setOpenSessions] = useState([]);
  const [suggestedId, setSuggestedId] = useState(() => Number(getClientValue(ACTIVE_SESSION_KEY)) || null);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState("");
  const [notice, setNotice] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [messageMeta, setMessageMeta] = useState({});
  const [responseMeta, setResponseMeta] = useState(null);
  const [learningReport, setLearningReport] = useState(null);
  const [completedReport, setCompletedReport] = useState(null);
  const [ragStatus, setRagStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pendingHelp, setPendingHelp] = useState(null);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const messagePending = useRef(false);
  const messageSequence = useRef(0);
  const topic = curriculumSelection?.subject === selectedSubject ? curriculumSelection.topic : "";
  const displayedTopic = activeSession?.topic || topic;
  const currentRagStatus = ragStatus?.subject === selectedSubject ? ragStatus : null;

  useEffect(() => {
    let active = true;
    api("/sessions").then((sessionResult) => {
      if (!active) return;
      const resumable = (Array.isArray(sessionResult.sessions) ? sessionResult.sessions : [])
        .filter((session) => session.state !== "finished");
      setOpenSessions(resumable);
      const storedId = Number(getClientValue(ACTIVE_SESSION_KEY));
      const storedSession = resumable.find((session) => session.id === storedId);
      // Show saved progress first, so returning students can deliberately choose
      // resume or restart instead of being silently dropped into an old chat.
      if (!storedSession) {
        removeClientValue(ACTIVE_SESSION_KEY);
        setSuggestedId(null);
      }
    }).catch((requestError) => { if (active) setSessionsError(requestError.message); })
      .finally(() => { if (active) setSessionsLoading(false); });
    return () => { active = false; };
  }, []);

  const reloadSessions = async () => {
    setSessionsLoading(true); setSessionsError("");
    try { const result = await api("/sessions"); setOpenSessions((result.sessions || []).filter((session) => session.state !== "finished")); }
    catch (requestError) { setSessionsError(requestError.message); }
    finally { setSessionsLoading(false); }
  };
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

  const adoptSession = (result) => {
    if (!result?.session?.id || !Array.isArray(result.session.messages)) {
      throw new Error("학습 대화 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.");
    }
    setSessionId(result.session.id);
    setActiveSession(result.session);
    setLearningReport(result.session.learning_report || null);
    setCompletedReport(null);
    setMessages(result.session.messages);
    setMessageMeta(metadataByMessage(result.session.messages));
    setResponseMeta(result.response_meta || null);
    setInput(""); setFeedback(null); setNotice("");
    setClientValue(ACTIVE_SESSION_KEY, String(result.session.id));
    setSuggestedId(result.session.id);
    setOpenSessions((current) => [result.session, ...current.filter((item) => item.id !== result.session.id)]);
  };

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
      adoptSession(result);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const resumeSession = async (targetSession) => {
    setLoading(true); setError("");
    try {
      adoptSession(await api(`/sessions/${targetSession.id}/resume`, { method: "POST" }));
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const restartSession = async (targetSession) => {
    if (loading || !window.confirm(`‘${targetSession.topic || "학습"}’을 처음부터 다시 시작할까요?\n이전 대화와 진행 기록은 그대로 보존하고, 같은 범위의 새 학습을 시작합니다.`)) return;
    setLoading(true); setError("");
    try {
      adoptSession(await api(`/sessions/${targetSession.id}/restart`, { method: "POST" }));
      setOpenSessions((current) => current.map((item) => item.id === targetSession.id ? { ...item, state: "paused" } : item));
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const pauseSession = async () => {
    if (loading || (input.trim() && !window.confirm("아직 보내지 않은 입력은 저장되지 않아요. 대화 기록과 진행 상태를 저장하고 나갈까요?"))) return;
    setLoading(true); setError("");
    try {
      const result = await api(`/sessions/${sessionId}/pause`, { method: "POST" });
      setOpenSessions((current) => [result.session, ...current.filter((item) => item.id !== sessionId)]);
      setSessionId(null); setActiveSession(null); setMessages([]); setInput(""); setFeedback(null);
      setMessageMeta({}); setResponseMeta(null); setLearningReport(null); setCompletedReport(null);
      setNotice(result.message);
      // Keep the id only as a suggestion, not an instruction to auto-resume.
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const send = async (event) => {
    event.preventDefault();
    await sendMessage(input.trim());
  };

  const sendMessage = async (content, helpAction = null) => {
    if (!content || loading || messagePending.current || !sessionId) return;
    messagePending.current = true;
    const localId = `local-${sessionId}-${++messageSequence.current}`;
    setMessages((current) => [...current, { id: localId, sender_type: "user", content }]);
    // Help is a separate request: never submit or erase an unfinished answer.
    if (!helpAction) setInput("");
    setPendingHelp(helpAction); setLoading(true); setError("");
    try {
      const result = await api(`/sessions/${sessionId}/messages`, {
        method: "POST", body: JSON.stringify({ content, ...(helpAction ? { help_action: helpAction } : {}) }),
      });
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
      if (!helpAction) setInput((current) => current || content);
      setError(`${requestError.message} ${helpAction ? "작성 중인 답변은 그대로 남아 있어요." : "입력 내용은 복구했습니다."}`);
    }
    finally { messagePending.current = false; setLoading(false); setPendingHelp(null); }
  };

  const requestHint = () => sendMessage(HINT_REQUEST, "hint");

  const finish = async () => {
    setLoading(true);
    try {
      const result = await api(`/sessions/${sessionId}/finish`, { method: "POST" });
      setCompletedReport(result.learning_report || learningReport);
      setOpenSessions((current) => current.filter((item) => item.id !== sessionId));
      removeClientValue(ACTIVE_SESSION_KEY);
      setSuggestedId(null);
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
      {notice && <p className="study-saved-notice" role="status">{notice}</p>}
      {sessionsLoading && <p role="status">저장된 학습을 확인하고 있어요.</p>}
      {sessionsError && <p className="study-error" role="alert">학습 기록을 불러오지 못했어요. <button type="button" onClick={reloadSessions}>다시 불러오기</button></p>}
      <InterruptedSessions sessions={openSessions} suggestedId={suggestedId} loading={loading || sessionsLoading} onResume={resumeSession} onRestart={restartSession} />
      <label>과목<select value={selectedSubject} disabled={loading} onChange={(e) => { setSelectedSubject(e.target.value); setCurriculumSelection(null); }}><option value="">과목 선택</option>{SUBJECTS.map((subject) => <option key={subject}>{subject}</option>)}</select></label>
      <CurriculumSelector
        subject={selectedSubject}
        preferredGrade={user?.grade || ""}
        onSelectionChange={setCurriculumSelection}
        disabled={loading}
      />
      {currentRagStatus && !currentRagStatus.available && (
        <p className="rag-notice">{currentRagStatus.subject} 학습 자료를 준비 중입니다. 다른 과목을 선택해주세요.</p>
      )}
      {error && <p className="study-error">{error}</p>}
      <button onClick={startSession} disabled={loading || !topic || currentRagStatus?.available === false}>{loading ? "준비 중..." : "선택한 단원으로 학습 시작"}</button>
    </main>
  );

  return (
    <div className="study-chat-container">
      <header className="study-chat-header"><div><span className="study-kicker">나의 학습 노트</span><strong>{displayedTopic}</strong><small>{responseMeta?.stage || "개념 설명"} · AI와 생각 나누기</small></div><div className="study-header-actions"><button type="button" onClick={pauseSession} disabled={loading}>저장하고 나가기</button><button type="button" onClick={finish} disabled={loading}>마치고 돌아보기</button></div></header>
      <LearningReport report={learningReport} />
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={`${message.sender_type}-${message.id ?? index}`} className={`message-row ${message.sender_type}`}>
            <div className="message-content-wrap">
              <span className="message-author">

{message.sender_type === "ai" ? `${AI_TUTOR_NAME} 🦉` : "나 🙋"}

</span>
              <div className="bubble"><MathText text={message.content} /></div>
              {message.sender_type === "ai" && ["example", "simplify"].includes(messageMeta[message.id]?.help_action) && <span className="study-help-label">{messageMeta[message.id].help_action === "example" ? "예시로 이해하기" : "쉬운 말로 이해하기"}</span>}
              {message.sender_type === "ai" && <HintPanel hint={messageMeta[message.id]?.hint} />}
              {message.sender_type === "ai" && messageMeta[message.id] && <EvidencePanel meta={messageMeta[message.id]} />}
            </div>
          </div>
        ))}
        {loading && <div className="message-row ai" role="status"><div className="bubble"><span>생각을 정리하고 있어요...</span></div></div>}
        <div ref={bottomRef} />
      </div>
      {feedback && <div className="feedback-strip"><div><strong>{responseMeta?.help_action ? "학습 도움" : "대화 피드백"} · {formatFeedback(feedback.level, "분석 중")}</strong><span>{formatFeedback(feedback.strengths, "피드백을 확인해보세요.")}</span></div>{feedback.assessment ? <div className="rubric-scores"><span>AI의 잠정 피드백 · 정답률이 아닙니다</span></div> : <div className="rubric-scores"><span>개념 {feedback.rubric?.concept ?? "-"}/40</span><span>근거 {feedback.rubric?.reasoning ?? "-"}/30</span><span>명료성 {feedback.rubric?.clarity ?? "-"}/20</span><span>참여 {feedback.rubric?.engagement ?? "-"}/10</span></div>}</div>}
      {error && <p className="study-error">{error}</p>}
      <div className="study-help-actions" role="group" aria-label="하루에게 학습 도움 요청">
        <span id="study-help-description">막혔다면 하루에게 도움을 요청해보세요.</span>
        <div><button type="button" disabled={loading} onClick={requestHint}><HelpIcon />{pendingHelp === "hint" ? "힌트 요청 중…" : "힌트"}</button></div>
      </div>
      <form className="chat-input-bar" onSubmit={send}><textarea rows={2} aria-label="내 생각과 풀이 과정" aria-describedby="study-help-description" value={input} onChange={(e) => setInput(e.target.value)} maxLength={5000} placeholder="내 생각과 그 이유를 적어보세요." /><button className="send-btn" disabled={loading || !input.trim()}>보내기</button></form>
    </div>
  );
}

function HelpIcon() {
  return <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M9 18h6M10 21h4M8 14a6 6 0 1 1 8 0c-1 .8-1 1.4-1 2H9c0-.6 0-1.2-1-2Z" />
  </svg>;
}

function HintPanel({ hint }) {
  if (!hint || !Array.isArray(hint.keywords) || !hint.keywords.length) return null;
  const keywords = hint.keywords.filter((word) => typeof word === "string" && word.trim()).slice(0, 3);
  if (!keywords.length) return null;
  return <aside className="tutor-hint" aria-label="생각을 돕는 힌트">
    <span className="tutor-hint-label">{hint.trigger === "stalled" ? "잠깐, 생각의 단서" : "생각을 돕는 힌트"} · {Math.min(3, Math.max(1, Number(hint.level) || 1))}단계</span>
    <ul className="tutor-hint-keywords">{keywords.map((word) => <li key={word}>{word}</li>)}</ul>
    {typeof hint.text === "string" && hint.text && <p><MathText text={hint.text} /></p>}
    <small>단어만 따라 쓰기보다, 떠오르는 생각과 이유를 말해보세요.</small>
  </aside>;
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
