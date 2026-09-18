// Sidebar.jsx
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
  { icon: studyIcon, text: "혼자 학습하기" },
  { icon: quizIcon, text: "퀴즈" },
  { icon: noteIcon, text: "정리노트" },
  { icon: calendarIcon, text: "캘린더" },
  { icon: roomIcon, text: "친구와 토론하기" },
  { icon: mypageIcon, text: "마이페이지" },
  { icon: settingIcon, text: "설정" },
];

export default function Sidebar({ activeMenu, setActiveMenu, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="logo">하브루타<small>질문으로 채우는 학습 노트</small></div>
      <ul className="menu">
        {menus.map((menu, index) => (
          <li
            key={index}
            className={activeMenu === index ? "active" : ""}
          >
            <button type="button" onClick={() => setActiveMenu(index)} aria-current={activeMenu === index ? "page" : undefined}>
              <img src={menu.icon} alt="" />
              {menu.text}
            </button>
          </li>
        ))}
      </ul>
      <button className="sidebar-logout" onClick={onLogout}>로그아웃</button>
    </aside>
  );
}
