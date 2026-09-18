import { useEffect, useState } from "react";
import { api } from "./api";
import { ACTIVE_SESSION_KEY, removeClientValue, setClientValue } from "./clientStorage";
import "./Home.css";

export default function Home({ setActiveMenu, user }) {
  const [dashboard, setDashboard] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [finishedSessions, setFinishedSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    Promise.all([api("/dashboard/me"), api("/sessions")])
      .then(([data, history]) => {
        if (cancelled) return;
        setDashboard(data);
        setSessions((history.sessions || []).filter((session) => session.state !== "finished"));
        setFinishedSessions((history.sessions || []).filter((session) => session.state === "finished"));
      })
      .catch(() => { if (!cancelled) setError("학습 기록을 불러오지 못했어요. 학습하기에서 다시 확인해주세요."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);
  const latest = sessions[0];
  const today = new Date();
  const week = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - ((today.getDay() + 6) % 7) + index);
    const count = finishedSessions.filter((session) => session.ended_at && new Date(session.ended_at).toDateString() === day.toDateString()).length;
    return { day, count, isToday: day.toDateString() === today.toDateString(), future: day > today };
  });
  const start = (session) => {
    if (session) setClientValue(ACTIVE_SESSION_KEY, String(session.id));
    else removeClientValue(ACTIVE_SESSION_KEY);
    setActiveMenu(1);
  };
  return (
    <main className="notebook-home">
      <header className="notebook-greeting">
        <div className="planner-heading"><span className="notebook-eyebrow">나의 학습 공간</span><span className="planner-grade">{user?.grade || "중·고등학생"}</span><time>{today.toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" })}</time></div>
        <h1>{user?.name || "학생"}님, 오늘의 생각을 이어가요.</h1>
        <p>정답을 찾는 것에서 한 걸음 더. 왜 그런지 나의 말로 설명해보세요.</p>
      </header>
      <section className="notebook-next" aria-labelledby="next-heading">
        <div className="planner-next-copy">
        <span className="notebook-eyebrow">{latest ? "이어서 탐구하기" : "혼자 학습하기"}</span>
        <h2 id="next-heading">{latest?.topic || "궁금한 단원부터 시작해볼까요?"}</h2>
        <p>{latest ? "지난 대화와 질문이 저장되어 있어요." : "과목과 단원을 고르면 AI와 질문을 주고받을 수 있어요."}</p>
        <div className="notebook-actions">
          <button type="button" className="notebook-primary" onClick={() => start(latest)} disabled={loading}>{loading ? "기록 확인 중…" : latest ? "대화 이어가기 →" : "과목 선택하고 시작 →"}</button>
          {latest && <button type="button" className="notebook-link" onClick={() => start(null)}>새로운 단원 학습</button>}
        </div>
        </div>
        <div className="planner-paper" aria-label="학습 방법: 내 생각 설명하기, 질문 주고받기, 배운 내용 정리하기">
          <span className="planner-paper-tab" aria-hidden="true">나의 탐구 노트</span>
          <span className="planner-paper-title">생각을 꺼내는 순서</span>
          <ol><li><span>01</span>내 말로 설명하고</li><li><span>02</span>질문을 주고받고</li><li><span>03</span>다시 정리하기</li></ol>
          <svg className="planner-pencil" viewBox="0 0 24 100" aria-hidden="true"><path d="M4 15h16v62l-8 19-8-19Z" fill="currentColor"/><path d="m4 77 8 19 8-19" fill="#dfc5a1"/><path d="m9 89 3 7 3-7" fill="#394253"/><path d="M4 15V8a8 8 0 0 1 16 0v7" fill="#c98676"/><path d="M4 15h16v5H4Z" fill="#c9cdd2"/><path d="M12 23v49" stroke="#fff" strokeOpacity=".45" strokeWidth="2"/></svg>
        </div>
      </section>
      {error && <p role="alert" className="study-error">{error}</p>}
      <section className="planner-week" aria-labelledby="week-heading">
        <div className="planner-week-title"><HomeIcon kind="calendar" /><div><h2 id="week-heading">이번 주 학습 발자국</h2><p>학습을 마친 날에 표시돼요.</p></div></div>
        <ol className="planner-days" aria-label="월요일부터 일요일까지 학습 종료 기록">{week.map(({ day, count, isToday, future }) => (
          <li key={day.toDateString()} className={isToday ? "is-today" : ""} aria-current={isToday ? "date" : undefined}>
            <span>{day.toLocaleDateString("ko-KR", { weekday: "short" })}</span>
            <span className={count && !error ? "day-mark has-learning" : "day-mark"} aria-label={loading ? "기록 확인 중" : error ? "기록 확인 불가" : `${day.getMonth() + 1}월 ${day.getDate()}일, ${future ? "예정" : `학습 종료 ${count}회`}`}>{loading || error ? "–" : count ? "✓" : day.getDate()}</span>
            <small>{isToday ? "오늘" : count && !error ? `${count}회` : ""}</small>
          </li>
        ))}</ol>
      </section>
      <section className="notebook-records" aria-labelledby="records-heading">
        <header><h2 id="records-heading">최근에 마친 학습</h2><button type="button" className="notebook-link" onClick={() => setActiveMenu(3)}>정리노트 보기 →</button></header>
        {loading ? <p role="status">기록을 불러오고 있어요.</p> : !error && (
          dashboard?.recent_records?.length ? <ul>{dashboard.recent_records.slice(0, 3).map((record) => (
            <li key={record.id}><span className="planner-record-icon"><HomeIcon kind="note" /></span><span className="planner-record-topic">{record.topic || "하브루타 학습"}</span><time>{formatDate(record.completed_at)}</time></li>
          ))}</ul> : <div className="planner-empty"><HomeIcon kind="note" /><div><strong>첫 번째 학습 노트를 기다리고 있어요.</strong><p>단원을 골라 대화해보세요. 마친 학습은 여기에 차곡차곡 쌓입니다.</p></div></div>
        )}
      </section>
      <section className="notebook-tools" aria-label="다른 학습 방법">
        <button type="button" className="planner-tool discussion" onClick={() => setActiveMenu(5)}><span className="planner-tool-icon"><HomeIcon kind="chat" /></span><strong>친구와 토론하기 <span aria-hidden="true">↗</span></strong><span>초대 코드로 모여 서로의 생각 비교하기</span></button>
        <button type="button" className="planner-tool practice" onClick={() => setActiveMenu(2)}><span className="planner-tool-icon"><HomeIcon kind="quiz" /></span><strong>퀴즈로 복습하기 <span aria-hidden="true">↗</span></strong><span>배운 개념을 새로운 문제에 적용하기</span></button>
      </section>
    </main>
  );
}

function HomeIcon({ kind }) {
  const paths = {
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 10h18m-13 5 3 3 5-5" /></>,
    note: <><path d="M6 3h14v18H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Zm1 0v18M11 8h5m-5 4h5m-5 4h3" /></>,
    chat: <><path d="M14 15H7l-4 3V4h15v7M10 18v3h7l4 2V11h-3" /><path d="M7 8h7m-7 3h4" /></>,
    quiz: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="m8 9 2 2 5-5m-7 9h8m-8 3h5" /></>,
  };
  return <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind]}</svg>;
}

function formatDate(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString("ko-KR", { month: "long", day: "numeric" }) : "날짜 미상";
}
