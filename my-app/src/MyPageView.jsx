import { useEffect, useState } from "react";
import { api } from "./api";
import "./MyPageView.css";

export default function MyPageView({ user }) {
  const [dashboard, setDashboard] = useState(null);
  useEffect(() => { api("/dashboard/me").then(setDashboard).catch(() => {}); }, []);
  const summary = dashboard?.summary || { completed_sessions: 0, total_messages: 0, average_score: null };
  return (
    <main className="my-page-container">
      <div className="profile-card">
        <div className="avatar">{user.name.slice(0, 2).toUpperCase()}</div>
        <div className="user-info"><h2>{user.name}</h2><span className="tier-badge">{user.grade || "학년 미설정"}</span></div>
        <div className="exp-section"><p>{user.email}</p><p>역할: {user.role}</p></div>
      </div>
      <div className="grid-section">
        <div className="dday-card"><h3>완료한 학습</h3><p className="dday-text">{summary.completed_sessions}회</p></div>
        <div className="stats-card">
          <h3>누적 학습 통계</h3>
          <p>대화 메시지 {summary.total_messages}개</p>
          <p>AI 평가 평균 {summary.average_score ?? "-"}점</p>
        </div>
      </div>
      <div className="badge-section"><h3>최근 학습 기록</h3><div className="badge-list">
        {(dashboard?.recent_records || []).map((record) => <div key={record.id} className="badge-item">🏅 {record.average_score ?? "-"}점 · {record.total_messages}개 메시지</div>)}
        {!dashboard?.recent_records?.length && <p>완료한 학습 세션이 아직 없습니다.</p>}
      </div></div>
    </main>
  );
}
