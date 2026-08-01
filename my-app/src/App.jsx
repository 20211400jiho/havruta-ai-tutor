import { useEffect, useState } from "react";
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

function App() {
  const [activeMenu, setActiveMenu] = useState(0);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isReminderEnabled, setIsReminderEnabled] = useState(true);
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) return;
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setCheckingAuth(false));
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", isDarkMode ? "dark" : "light");
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
        {activeMenu === 5 && <StudyRoomView />}
        {activeMenu === 6 && <MyPageView user={user} />}
        {activeMenu === 7 && (
          <SettingsView
            isDarkMode={isDarkMode}
            toggleDarkMode={() => setIsDarkMode(!isDarkMode)}
            isReminderEnabled={isReminderEnabled}
            toggleReminder={() => setIsReminderEnabled(!isReminderEnabled)}
          />
        )}
      </div>
    </div>
  );
}

export default App;
