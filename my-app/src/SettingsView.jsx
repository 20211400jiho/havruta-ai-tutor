import './SettingsView.css';

export default function SettingsView({ user, isDarkMode, toggleDarkMode }) {
  return (
    <main className="content settings-page">
      <h2>설정</h2>
      <div className="settings-section">
        <section className="setting-section">
          <h3>계정 정보</h3>
          <dl className="account-details">
            <div><dt>이름</dt><dd>{user.name}</dd></div>
            <div><dt>이메일</dt><dd>{user.email}</dd></div>
            <div><dt>학년</dt><dd>{user.grade || "미설정"}</dd></div>
            <div><dt>계정 유형</dt><dd>{user.role === "student" ? "학생" : user.role}</dd></div>
          </dl>
          <p className="setting-help">현재 계정 정보는 가입 시 입력한 실제 데이터이며, 프로필 수정 기능은 아직 제공하지 않습니다.</p>
        </section>

        <section className="setting-section">
          <h3>화면 설정</h3>
          <div className="toggle-group">
            <div>
              <strong>다크 모드</strong>
              <p>선택한 테마는 이 브라우저에 저장됩니다.</p>
            </div>
            <label className="switch">
              <input type="checkbox" checked={isDarkMode} onChange={toggleDarkMode} />
              <span className="slider"></span>
            </label>
          </div>
        </section>

        <div className="setting-status" role="status">
          학습 알림은 실제 알림 서버가 준비된 뒤 제공할 예정입니다.
        </div>
      </div>
    </main>
  );
}
