// Home.jsx
import { useEffect, useState } from "react";
import "./Home.css";
import HomeAi from "./assets/Home_ai.png";
import { api } from "./api";

export default function Home({ setActiveMenu, user }) {
  const [dashboard, setDashboard] = useState(null);
  useEffect(() => { api("/dashboard/me").then(setDashboard).catch(() => {}); }, []);
  const summary = dashboard?.summary || { completed_sessions: 0, total_messages: 0, average_score: null };
  const todayStatus = {
    studyTime: { title: "완료한 학습", value: `${summary.completed_sessions}회`, sub: "누적 세션", progress: Math.min(100, summary.completed_sessions * 10) },
    achievement: { title: "학습 성취도", value: `${summary.average_score ?? 0}%`, sub: "AI 평가 평균", progress: summary.average_score ?? 0 },
    quizzes: { title: "대화 메시지", value: `${summary.total_messages}개`, sub: "누적" },
    notes: { title: "학습 기록", value: `${dashboard?.recent_records?.length ?? 0}개`, sub: "최근" }
  };

  return (
    <main className="content">
      {/* 1. 상단 헤더 (인사말 및 AI 튜터 카드) */}
      <div className="header">
        <div>
          <h1 className="hello">안녕하세요, {user?.name}님!</h1>
          <p className="cheer">오늘도 꾸준히 학습해봐요!</p>
        </div>

        <div className="ai-card">
          <div>
            <h3>AI 튜터</h3>
            <p>무엇을 도와드릴까요?</p>
          </div>
          <div className="robot">
            <img src={HomeAi} alt="AI Tutor" />
          </div>
        </div>
      </div>

      {/* 2. 오늘의 학습 현황 섹션 */}
      <section className="status-section" style={{ marginTop: '30px' }}>
        <h2 className="section-title">오늘의 학습 현황</h2>
        <div className="status-grid">
          
          {/* 카드 1: 학습 시간 */}
          <div className="status-card-custom">
            <div className="card-info">
              <span className="card-label">{todayStatus.studyTime.title}</span>
              <h3 className="card-value">{todayStatus.studyTime.value}</h3>
              <span className="card-sub">{todayStatus.studyTime.sub}</span>
            </div>
            <div className="card-visual">
              <svg width="70" height="70" viewBox="0 0 36 36" className="circular-chart blue-arc">
                <path className="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="circle" strokeDasharray={`${todayStatus.studyTime.progress}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
            </div>
          </div>

          {/* 카드 2: 학습 성취도 */}
          <div className="status-card-custom">
            <div className="card-info">
              <span className="card-label">{todayStatus.achievement.title}</span>
              <h3 className="card-value">{todayStatus.achievement.value}</h3>
              <span className="card-sub">{todayStatus.achievement.sub}</span>
            </div>
            <div className="card-visual">
              <svg width="70" height="70" viewBox="0 0 36 36" className="circular-chart green-arc">
                <path className="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="circle" strokeDasharray={`${todayStatus.achievement.progress}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
            </div>
          </div>

          {/* 카드 3: 완료한 퀴즈 */}
          <div className="status-card-custom">
            <div className="card-info">
              <span className="card-label">{todayStatus.quizzes.title}</span>
              <h3 className="card-value">{todayStatus.quizzes.value}</h3>
              <span className="card-sub">{todayStatus.quizzes.sub}</span>
            </div>
            <div className="card-visual align-bottom">
              <div className="icon-box orange-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              </div>
            </div>
          </div>

          {/* 카드 4: 생성한 노트 */}
          <div className="status-card-custom">
            <div className="card-info">
              <span className="card-label">{todayStatus.notes.title}</span>
              <h3 className="card-value">{todayStatus.notes.value}</h3>
              <span className="card-sub">{todayStatus.notes.sub}</span>
            </div>
            <div className="card-visual align-bottom">
              <div className="icon-box purple-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z"></path></svg>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* 3. 바로가기 메뉴 섹션 (중복 제거 및 스위칭 기능 유지) */}
      <section className="menu-section" style={{ marginTop: '40px' }}>
        <h3>바로가기</h3>
        <div className="quick-menu">
          <button className="btn blue" onClick={() => setActiveMenu(1)}>
            학습 시작
            <span>AI와 학습하기</span>
          </button>
          <button className="btn green" onClick={() => setActiveMenu(2)}>
            퀴즈 풀기
            <span>복습 퀴즈 풀기</span>
          </button>
          <button className="btn purple" onClick={() => setActiveMenu(3)}>
            정리노트 보기
            <span>핵심 노트 확인</span>
          </button>
          <button className="btn orange" onClick={() => setActiveMenu(4)}>
            캘린더 보기
            <span>학습 기록 확인</span>
          </button>
        </div>
      </section>

      {/* 4. 하단 기록 섹션 (최근 기록 및 주간 그래프) */}
      <div className="bottom-section" style={{ marginTop: '40px' }}>
        <div className="history">
          <h3>최근 학습 기록</h3>
          <ul>{(dashboard?.recent_records || []).slice(0, 3).map((record) => <li key={record.id}>{record.topic || "하브루타 학습"} · {record.average_score ?? "-"}점</li>)}</ul>
        </div>

        <div className="weekly">
          <h3>주간 학습 기록</h3>
          <div className="graph-box">완료 세션 {summary.completed_sessions}회 · 총 메시지 {summary.total_messages}개</div>
        </div>
      </div>
    </main>
  );
}
