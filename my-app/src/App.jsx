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
import "./Home.css";

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("화면 렌더링 오류", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-error-page">
          <h1>화면을 표시하지 못했습니다.</h1>
          <p>입력한 내용은 유지되지 않을 수 있습니다. 화면을 다시 불러와 주세요.</p>
          <button type="button" onClick={() => window.location.reload()}>다시 불러오기</button>
        </main>
      );
    }
    return this.props.children;
  }
}

function getInitialDarkMode() {
  const savedTheme = localStorage.getItem("havruta_theme");
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
    localStorage.setItem("havruta_theme", theme);
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
