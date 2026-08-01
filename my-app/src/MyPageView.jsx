import React from 'react';
import './MyPageView.css';

export default function MyPageView() {
    const userData = {
    name: "00",
    tier: "Gold",
    exp: 75,
    dDay: "수능 D-120",
    badges: ["열공러", "얼리버드", "퀴즈왕"],
    stats: [
        { subject: "과학", hours: 12 },
        { subject: "수학", hours: 8 },
        { subject: "역사", hours: 5 },
    ]
    };

    return (
    <main className="my-page-container">
      {/* 1. 상단 프로필 영역 */}
        <div className="profile-card">
        <div className="avatar">YEJI</div>
        <div className="user-info">
            <h2>{userData.name}</h2>
            <span className="tier-badge">{userData.tier} Tier</span>
        </div>
        <div className="exp-section">
            <p>레벨업까지 {100 - userData.exp}% 남음</p>
            <div className="progress-bg"><div className="progress-fill" style={{ width: `${userData.exp}%` }}></div></div>
        </div>
        </div>

      {/* 2. D-Day 및 학습 통계 */}
        <div className="grid-section">
        <div className="dday-card">
            <h3>오늘의 목표</h3>
            <p className="dday-text">{userData.dDay}</p>
        </div>
        <div className="stats-card">
            <h3>이번 주 학습 시간</h3>
            {userData.stats.map((s, i) => (
            <div key={i} className="stat-row">
                <span>{s.subject}</span>
              <div className="bar"><div className="fill" style={{ width: `${s.hours * 5}%` }}></div></div>
                <span>{s.hours}h</span>
            </div>
            ))}
        </div>
        </div>

      {/* 3. 배지 영역 */}
        <div className="badge-section">
        <h3>나의 훈장</h3>
        <div className="badge-list">
            {userData.badges.map((b, i) => <div key={i} className="badge-item">🏅 {b}</div>)}
        </div>
        </div>
    </main>
    );
}