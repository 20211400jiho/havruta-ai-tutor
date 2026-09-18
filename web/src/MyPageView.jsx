import { useEffect, useState } from "react";
import { api } from "./api";
import "./MyPageView.css";

export default function MyPageView({ user }) {
  const [dashboard, setDashboard] = useState(null);
  const [loadError, setLoadError] = useState(false);
  useEffect(() => { api("/dashboard/me").then(setDashboard).catch(() => setLoadError(true)); }, []);
  const recentRecords = (dashboard?.recent_records || []).slice(0, 5);
  const summary = dashboard?.summary || { completed_sessions: 0, completed_units: 0, completed_quizzes: 0, explanation_level: "학습 전" };
  return (
    <main className="my-page-container">
      <div className="profile-card">
        <div className="avatar">{user.name.slice(0, 2).toUpperCase()}</div>
        <div className="user-info"><h2>{user.name}</h2><span className="tier-badge">{user.grade || "학년 미설정"}</span></div>
        <div className="exp-section"><p>{user.email}</p><p>계정 유형: {user.role === "student" ? "학생" : user.role}</p></div>
      </div>
      <div className="grid-section">
        <div className="dday-card"><h3>완료한 학습</h3><p className="dday-text">{summary.completed_sessions}회</p></div>
        <div className="stats-card">
          <h3>누적 학습 통계</h3>
          <p>학습한 교육과정 단원 {summary.completed_units}개 (세션 종료 기준)</p>
          <p>완료한 복습 퀴즈 {summary.completed_quizzes}회</p>
          <p>기존 규칙 평가 기록: {summary.explanation_level} (숙달도 아님)</p>
          <p>새 학습의 목표 확인과 복습 제안은 정리노트에서 확인하세요.</p>
        </div>
      </div>
      <section className="mypage-recent">
        <h3>최근 학습 기록</h3>
        <ul className="mypage-recent-list">
          {recentRecords.map((record) => <li key={record.id}>
            <span>{record.topic || "하브루타 학습"}</span>
            <span className="mypage-record-date">{formatRecordDate(record.completed_at)}</span>
          </li>)}
        </ul>
        {loadError ? <p>학습 기록을 불러오지 못했어요.</p>
          : !dashboard ? <p>학습 기록을 불러오는 중이에요.</p>
          : !recentRecords.length && <p>아직 완료한 학습이 없어요.</p>}
      </section>
    </main>
  );
}

function formatRecordDate(value) {
  if (!value) return "날짜 미상";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 미상" : date.toLocaleDateString("ko-KR");
}
