import { Component, useEffect, useState } from "react";
import AuthView from "./AuthView.jsx";
import Sidebar from "./Sidebar.jsx";
import Home from "./Home.jsx";
import StudyView from "./StudyView.jsx";
import QuizView from "./QuizView.jsx";
import NoteView from "./NoteView.jsx";
import CalendarView from "./CalendarView.jsx";
import StudyRoomView from "./StudyRoomView.jsx";
import MyPageView from "./MyPageView.jsx";
import SettingsView from "./SettingsView.jsx";
import { api, getToken, setToken } from "./api.js";
import {
  clearHavrutaClientState,
  getClientValue,
  setClientValue,
  THEME_KEY,
} from "./clientStorage.js";
import "./Home.css";

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorName: "", errorMessage: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorName: String(error?.name || "FrontendError").slice(0, 80),
      errorMessage: String(error?.message || error || "알 수 없는 오류").slice(0, 300),
    };
  }

  componentDidCatch(error, info) {
    console.error("화면 렌더링 오류", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-error-page">
          <h1>화면을 표시하지 못했습니다.</h1>
          <p>일시적인 화면 오류일 수 있습니다. 먼저 화면을 다시 불러오고, 문제가 반복될 때만 로그인 정보를 초기화해주세요. 서버의 학습 기록은 삭제되지 않습니다.</p>
          <details>
            <summary>오류 정보</summary>
            <code>{this.state.errorName}: {this.state.errorMessage}</code>
          </details>
          <div className="app-error-actions"><button type="button" onClick={() => window.location.reload()}>화면 다시 불러오기</button><button type="button" className="secondary" onClick={() => { clearHavrutaClientState(); window.location.replace("/"); }}>로그인 정보 초기화</button></div>
        </main>
      );
    }
    return this.props.children;
  }
}

function getInitialDarkMode() {
  const savedTheme = getClientValue(THEME_KEY);
  if (savedTheme) return savedTheme === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

function App() {
  const [activeMenu, setActiveMenu] = useState(0);
  const [isDarkMode, setIsDarkMode] = useState(getInitialDarkMode);
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) return;
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setCheckingAuth(false));
  }, []);

  useEffect(() => {
    const theme = isDarkMode ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    setClientValue(THEME_KEY, theme);
  }, [isDarkMode]);

  const logout = () => {
    setToken(null);
    setUser(null);
    setActiveMenu(0);
  };

  if (checkingAuth) return <main className="auth-page">로그인 정보를 확인하고 있어요...</main>;
  if (!user) return <AuthView onAuthenticated={setUser} />;

  return (
    <div className="app-container" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar activeMenu={activeMenu} setActiveMenu={setActiveMenu} onLogout={logout} />
      <div className="main-content" style={{ flex: 1, padding: "20px", overflowY: "auto" }}>
        {activeMenu === 0 && <Home setActiveMenu={setActiveMenu} user={user} />}
        {activeMenu === 1 && <StudyView />}
        {activeMenu === 2 && <QuizView />}
        {activeMenu === 3 && <NoteView />}
        {activeMenu === 4 && <CalendarView />}
        {activeMenu === 5 && <StudyRoomView user={user} />}
        {activeMenu === 6 && <MyPageView user={user} />}
        {activeMenu === 7 && (
          <SettingsView
            user={user}
            isDarkMode={isDarkMode}
            toggleDarkMode={() => setIsDarkMode((current) => !current)}
          />
        )}
      </div>
    </div>
  );
}

export default function RootApp() {
  return <AppErrorBoundary><App /></AppErrorBoundary>;
}
