import { useEffect, useState } from "react";
import { api } from "./api";
import "./MyPageView.css";

export default function MyPageView({ user }) {
  const [dashboard, setDashboard] = useState(null);
  useEffect(() => { api("/dashboard/me").then(setDashboard).catch(() => {}); }, []);
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
      <div className="badge-section"><h3>최근 학습 기록</h3><div className="badge-list">
        {(dashboard?.recent_records || []).map((record) => <div key={record.id} className="badge-item">🏅 {record.topic || "하브루타 학습"} · {scoreLevel(record.average_score)}</div>)}
        {!dashboard?.recent_records?.length && <p>완료한 학습 세션이 아직 없습니다.</p>}
      </div></div>
    </main>
  );
}

function scoreLevel(score) {
  if (score == null) return "설명 수준 미확인";
  if (score >= 80) return "기존 규칙 평가: 우수";
  if (score >= 60) return "기존 규칙 평가: 충분함";
  return "기존 규칙 평가: 보완 필요";
}
