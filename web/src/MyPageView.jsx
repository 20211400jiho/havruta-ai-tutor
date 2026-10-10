import { useEffect, useState } from "react";
import { api } from "./api";
import "./MyPageView.css";

function NoteIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M6 3.5h11a2 2 0 0 1 2 2v15H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" /><path d="M7.5 3.5v17M11 8h4.5M11 12h4.5" /></svg>;
}

export default function MyPageView({ user, onNavigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [loadError, setLoadError] = useState(false);
  useEffect(() => {
    let active = true;
    api("/dashboard/me").then((result) => { if (active) setDashboard(result); }).catch(() => { if (active) setLoadError(true); });
    return () => { active = false; };
  }, []);
  const retry = async () => {
    setLoadError(false);
    try { setDashboard(await api("/dashboard/me")); }
    catch { setLoadError(true); }
  };
  const recentRecords = (dashboard?.recent_records || []).slice(0, 5);
  const summary = dashboard?.summary;
  const name = user?.name?.trim() || "학생";
  const metrics = [
    { label: "마친 학습", value: summary?.completed_sessions, unit: "회" },
    { label: "학습한 단원", value: summary?.completed_units, unit: "개" },
    { label: "푼 복습 퀴즈", value: summary?.completed_quizzes, unit: "회" },
  ];
  return (
    <main className="my-page-container">
      <header className="mypage-heading">
        <div><span className="mypage-eyebrow">나의 학습 공간</span><h1>마이페이지</h1><p>내 정보와 차곡차곡 쌓인 배움을 살펴보세요.</p></div>
        {onNavigate && <button type="button" className="mypage-start" onClick={() => onNavigate(1)}>학습하러 가기 <span aria-hidden="true">↗</span></button>}
      </header>

      <section className="mypage-profile" aria-labelledby="mypage-profile-title">
        <div className="mypage-identity">
          <span className="mypage-avatar" aria-hidden="true">{Array.from(name).slice(0, 2).join("").toUpperCase()}</span>
          <div><span className="mypage-profile-label">나의 프로필</span><h2 id="mypage-profile-title">{name}<span>님</span></h2><span className="mypage-role">{{ student: "학생", teacher: "교사", admin: "관리자" }[user?.role] || "회원"}</span></div>
        </div>
        <dl className="mypage-account"><div><dt>학년</dt><dd>{user?.grade || "학년 미설정"}</dd></div><div><dt>이메일</dt><dd>{user?.email || "이메일 미등록"}</dd></div></dl>
      </section>

      <section className="mypage-learning" aria-labelledby="mypage-learning-title" aria-busy={!dashboard && !loadError}>
        <div className="mypage-section-heading"><h2 id="mypage-learning-title">나의 학습 발자취</h2><span>누적 기록</span></div>
        <dl className="mypage-metrics">{metrics.map((metric) => <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value == null ? <span className="mypage-metric-pending" aria-label={loadError ? "불러오기 실패" : "불러오는 중"}>—</span> : metric.value.toLocaleString("ko-KR")}<span>{metric.unit}</span></dd></div>)}</dl>
        <p className="mypage-caption">종료한 학습과 제출한 퀴즈 기준이에요. 단원 수는 숙달도를 의미하지 않아요.</p>
      </section>

      <section className="mypage-recent" aria-labelledby="mypage-recent-title">
        <div className="mypage-section-heading"><h2 id="mypage-recent-title">최근 학습 기록</h2>{recentRecords.length > 0 && <span>최근 {recentRecords.length}건</span>}</div>
        {loadError ? <div className="mypage-empty" role="alert"><p>학습 기록을 불러오지 못했어요.</p><button type="button" className="mypage-link" onClick={retry}>다시 불러오기 ↻</button></div>
          : !dashboard ? <p className="mypage-loading" role="status">학습 기록을 불러오고 있어요.</p>
          : recentRecords.length ? <ul className="mypage-recent-list">
            {recentRecords.map((record) => <li key={record.id}>
              <span className="mypage-record-icon"><NoteIcon /></span>
              <div className="mypage-record-content"><h3>{record.topic || "하브루타 학습"}</h3><span>학습 마침</span></div>
              <span className="mypage-record-date">{formatRecordDate(record.completed_at)}</span>
            </li>)}
          </ul> : <div className="mypage-empty"><span className="mypage-empty-icon"><NoteIcon /></span><h3>첫 번째 배움을 기록해 볼까요?</h3><p>학습을 마치면 여기에 기록이 쌓여요.</p>{onNavigate && <button type="button" className="mypage-link" onClick={() => onNavigate(1)}>첫 학습 시작하기 →</button>}</div>}
        {onNavigate && recentRecords.length > 0 && !loadError && <div className="mypage-recent-footer"><button type="button" className="mypage-link" onClick={() => onNavigate(4)}>캘린더에서 전체 기록 보기 →</button></div>}
      </section>

      <aside className="mypage-review">
        <span className="mypage-review-icon"><NoteIcon /></span>
        <div><h2>배운 내용, 내 말로 다시 한 번.</h2><p>정리노트에서 내 설명과 다음에 복습할 것을 확인하세요.</p></div>
        {onNavigate && <button type="button" className="mypage-link" onClick={() => onNavigate(3)}>정리노트 보기 <span aria-hidden="true">→</span></button>}
      </aside>
      {summary?.average_score != null && <details className="mypage-legacy"><summary>이전 평가 기록</summary><p>기존 규칙 평가: {summary.explanation_level}. 검증된 이해도나 숙달도 점수는 아니에요.</p></details>}
    </main>
  );
}

function formatRecordDate(value) {
  if (!value) return "날짜 미상";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 미상" : date.toLocaleDateString("ko-KR", { year: "numeric", month: "short", day: "numeric" });
}
