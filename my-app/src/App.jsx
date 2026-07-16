import { useState, useEffect } from "react";
import Sidebar from "./Sidebar.jsx";//사이드 바
import Home from "./Home.jsx";  //홈 화면
import StudyView from "./StudyView.jsx";  //학습 화면
import QuizView from "./QuizView.jsx";  //퀴즈 화면
import NoteView from "./NoteView.jsx"; // 정리노트
import CalendarView from "./CalendarView.jsx";  //달력 화면
import StudyRoomView from "./StudyRoomView.jsx"; // 1:2
import MyPageView from "./MyPageView.jsx"; //마이페이지
import SettingsView from "./SettingsView.jsx";//설정
import "./Home.css";

function App() {
  const [activeMenu, setActiveMenu] = useState(0); 
  const [isDarkMode,setIsDarkMode] = useState(false);
  const [isReminderEnabled, setIsReminderEnabled] = useState(true);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, [isDarkMode]);

  return (
    <div className="app-container" style={{ display: "flex", minHeight: "100vh"}}>

        <Sidebar activeMenu={activeMenu} setActiveMenu={setActiveMenu} />

        <div className="main-content" style={{ flex: 1, padding: "20px", overflowY: "auto"}}>
        {activeMenu === 0 && <Home setActiveMenu={setActiveMenu} />}
        
        {activeMenu === 1 && <StudyView />}
    
        {activeMenu === 2 && <QuizView />}

        {activeMenu === 3 && <NoteView />}

        {activeMenu === 4 && <CalendarView />}

        {activeMenu === 5 && <StudyRoomView />}

        {activeMenu === 6 && <MyPageView />}

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