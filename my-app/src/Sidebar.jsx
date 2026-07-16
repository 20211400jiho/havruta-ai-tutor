// Sidebar.jsx
import React from "react";
import "./Home.css";

// 사이드바 이미지 임포트
import homeIcon from "./assets/home.png";
import studyIcon from "./assets/study.png";
import quizIcon from "./assets/quiz.png";
import noteIcon from "./assets/note.png";
import calendarIcon from "./assets/calendar.png";
import roomIcon from "./assets/room.png";
import mypageIcon from "./assets/mypage.png";
import settingIcon from "./assets/setting.png";

const menus = [
  { icon: homeIcon, text: "홈" },
  { icon: studyIcon, text: "학습하기" },
  { icon: quizIcon, text: "퀴즈" },
  { icon: noteIcon, text: "정리노트" },
  { icon: calendarIcon, text: "캘린더" },
  { icon: roomIcon, text: "스터디룸" },
  { icon: mypageIcon, text: "마이페이지" },
  { icon: settingIcon, text: "설정" },
];

export default function Sidebar({ activeMenu, setActiveMenu }) {
  return (
    <aside className="sidebar">
      <div className="logo">AI Study</div>
      <ul className="menu">
        {menus.map((menu, index) => (
          <li
            key={index}
            className={activeMenu === index ? "active" : ""}
            onClick={() => setActiveMenu(index)}
          >
            <img src={menu.icon} alt={menu.text} />
            {menu.text}
          </li>
        ))}
      </ul>
    </aside>
  );
}