import { useEffect, useState } from 'react';
import { api } from './api';
import './SettingsView.css';

export default function SettingsView({ user, isDarkMode, toggleDarkMode }) {
  const [systemStatus, setSystemStatus] = useState(null);
  const [statusError, setStatusError] = useState('');
  useEffect(() => {
    api('/health/ready').then(setSystemStatus).catch((error) => setStatusError(error.message));
  }, []);
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

        <section className="setting-section">
          <h3>시스템 동작 상태</h3>
          {systemStatus ? <div className="system-status-grid" role="status"><StatusItem label="데이터베이스" ready={systemStatus.database.ready} detail={systemStatus.database.ready ? '정상' : '연결 오류'} /><StatusItem label="RAG 검색" ready={systemStatus.rag.ready} detail={`${systemStatus.rag.provider} · ${systemStatus.rag.chroma_documents || systemStatus.rag.lexical_documents}건`} /><StatusItem label="AI 생성" ready={systemStatus.ai.provider_configured} detail={systemStatus.ai.provider_configured ? 'OpenAI 설정됨' : 'OpenAI 미설정 · 규칙 폴백'} /><StatusItem label="실시간 채팅" ready={systemStatus.realtime.redis_connected || systemStatus.realtime.local_websocket_fallback_ready} detail={systemStatus.realtime.redis_connected ? 'Redis 연결' : '단일 서버 폴백'} /></div> : <p className="setting-help">{statusError || '상태를 확인하고 있습니다...'}</p>}
        </section>
      </div>
    </main>
  );
}

function StatusItem({ label, ready, detail }) {
  return <div className="system-status-item"><span className={ready ? 'status-dot ready' : 'status-dot fallback'}></span><div><strong>{label}</strong><p>{detail}</p></div></div>;
}
