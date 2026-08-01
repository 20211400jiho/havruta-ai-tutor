// CalendarView.jsx
import React, { useState } from 'react';
import './CalendarView.css';

export default function CalendarView() {
  // 1. 현재 시스템의 실시간 날짜를 초기값으로 설정
  const today = new Date();
  const [currentDate, setCurrentDate] = useState(today); // 달력 내비게이션용 (년, 월)
  const [selectedDate, setSelectedDate] = useState(today); // 우측 리포트 표시용 (년, 월, 일)

  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth(); // 0 = 1월, 11 = 12월

  // 2. 월 변경 함수 (화살표 버튼 클릭 이벤트)
  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentYear, currentMonth - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentYear, currentMonth + 1, 1));
  };

  // 3. '오늘' 버튼 함수 (실제 오늘 연/월/일로 즉시 복귀)
  const handleGoToToday = () => {
    const now = new Date();
    setCurrentDate(now);
    setSelectedDate(now);
  };

  // 4. 달력 격자 구성을 위한 동적 날짜 계산기
  const generateCalendarDays = () => {
    // 이번 달의 첫 날 요일 (0: 일요일 ~ 6: 토요일)
    const firstDayIndex = new Date(currentYear, currentMonth, 1).getDay();
    // 이번 달의 총 일수
    const totalDaysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    // 지난 달의 총 일수 (이전 달 흐린 날짜 채우기용)
    const totalDaysInPrevMonth = new Date(currentYear, currentMonth, 0).getDate();

    const days = [];

    // [이전 달 날짜 채우기]
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      days.push({
        day: totalDaysInPrevMonth - i,
        monthOffset: -1,
        isCurrentMonth: false
      });
    }

    // [이번 달 날짜 채우기]
    for (let i = 1; i <= totalDaysInMonth; i++) {
      days.push({
        day: i,
        monthOffset: 0,
        isCurrentMonth: true
      });
    }

    // [다음 달 날짜 채우기] 격자가 깔끔하게 6주(42칸)로 떨어지도록 유연하게 설정
    const totalSlots = 42; 
    const nextMonthSlots = totalSlots - days.length;
    for (let i = 1; i <= nextMonthSlots; i++) {
      days.push({
        day: i,
        monthOffset: 1,
        isCurrentMonth: false
      });
    }

    return days;
  };

  const calendarDays = generateCalendarDays();

  const learningRecords = {
    "2026-08-20": {
      dateText: "8월 20일 (목)",
      records: [
        { title: "광합성 학습", detail: "30분", color: "#4f7df3" },
        { title: "복습 퀴즈", detail: "20분", color: "#6366f1" }
      ],
      notes: ["광합성 핵심 요약"],
      quizResult: "정답 8 / 10 (80%)",
      totalTime: "50분"
    },

    [`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`]: {
      dateText: `${today.getMonth() + 1}월 ${today.getDate()}일 (오늘)`,
      records: [
        { title: "광합성", detail: "40분", color: "#4f7df3" }
      ],
      notes: ["식물의 광합성 과정"],
      quizResult: "정답 10 / 10 (100%)",
      totalTime: "40분"
    }
  };

  const selectedDateKey = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
  
  const activeRecord = learningRecords[selectedDateKey] || {
    dateText: `${selectedDate.getMonth() + 1}월 ${selectedDate.getDate()}일`,
    records: [],
    notes: [],
    quizResult: null,
    totalTime: "0분"
  };

    // 날짜 셀 클릭 처리 함수
  const handleDayClick = (item) => {
    // 클릭한 셀의 연/월 정보를 토대로 정확한 Date 객체 생성
    const targetDate = new Date(currentYear, currentMonth + item.monthOffset, item.day);
    setSelectedDate(targetDate);
    
    // 만약 이전 달이나 다음 달 날짜를 클릭했다면 달력 시점도 같이 이동시켜줌
    if (item.monthOffset !== 0) {
      setCurrentDate(new Date(currentYear, currentMonth + item.monthOffset, 1));
    }
  };

  return (
    <main className="content calendar-page-container">
      <div className="calendar-main-box">
        <div className="calendar-header-zone">
          <h2 className="calendar-main-title">캘린더</h2>
          
          <div className="month-selector">
            <button className="arrow-btn" onClick={handlePrevMonth}>〈</button>
            <span className="current-month-text">{currentYear}년 {currentMonth + 1}월</span>
            <button className="arrow-btn" onClick={handleNextMonth}>〉</button>
          </div>
          
          <button className="btn-today" onClick={handleGoToToday}>오늘</button>
        </div>

        <div className="weekdays-grid">
          {['일', '월', '화', '수', '목', '금', '토'].map((w, idx) => (
            <div key={idx} className={`weekday-label ${w === '일' ? 'sun' : w === '토' ? 'sat' : ''}`}>
              {w}
            </div>
          ))}
        </div>

        <div className="days-grid">
          {calendarDays.map((item, index) => {
            // 이 셀이 가리키는 실제 날짜 객체 연산
            const cellDate = new Date(currentYear, currentMonth + item.monthOffset, item.day);
            
            // 1. 현재 선택된 날짜인지 체크
            const isSelected = 
              selectedDate.getFullYear() === cellDate.getFullYear() &&
              selectedDate.getMonth() === cellDate.getMonth() &&
              selectedDate.getDate() === cellDate.getDate();

            // 2. 실제 오늘 날짜(현실 시간)인지 체크해서 테두리 피드백용
            const isRealToday = 
              today.getFullYear() === cellDate.getFullYear() &&
              today.getMonth() === cellDate.getMonth() &&
              today.getDate() === cellDate.getDate();

            let dayClass = "";
            if (!item.isCurrentMonth) dayClass += "other-month ";
            if (isSelected) dayClass += "selected-day ";
            if (isRealToday && !isSelected) dayClass += "real-today ";

            // 특정 하단 도트 더미 표시용 키 생성
            const cellDateKey = `${cellDate.getFullYear()}-${String(cellDate.getMonth() + 1).padStart(2, '0')}-${String(cellDate.getDate()).padStart(2, '0')}`;
            const hasData = !!learningRecords[cellDateKey];

            return (
              <div 
                key={index} 
                className={`day-cell ${dayClass}`}
                onClick={() => handleDayClick(item)}
              >
                <span className="day-number">{item.day}</span>
                {/* 데이터가 존재하는 날짜는 하단에 작은 점 포인트 표시 */}
                {hasData && !isSelected && <div className="mini-dot green-dot"></div>}
              </div>
            );
          })}
        </div>
      </div>

      <div className="calendar-sidebar-report">
        <h3 className="report-date-title">{activeRecord.dateText}</h3>

        {/* 1. 학습 기록 목록 */}
        <div className="report-section">
          <h4 className="report-section-sub">학습 기록</h4>
          {activeRecord.records.length > 0 ? (
            <ul className="report-list">
              {activeRecord.records.map((rec, idx) => (
                <li key={idx} className="report-item">
                  <span className="bullet" style={{ backgroundColor: rec.color }}></span>
                  <span className="item-title">{rec.title}</span>
                  <span className="item-value">{rec.detail}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-data-text">학습 기록이 없습니다.</p>
          )}
        </div>

        {/* 2. 생성한 노트 */}
        <div className="report-section">
          <h4 className="report-section-sub">생성한 노트</h4>
          {activeRecord.notes.length > 0 ? (
            <ul className="report-list">
              {activeRecord.notes.map((note, idx) => (
                <li key={idx} className="report-item">
                  <span className="bullet purple-bullet"></span>
                  <span className="item-title">{note}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-data-text">생성한 노트가 없습니다.</p>
          )}
        </div>

        {/* 3. 퀴즈 결과 */}
        <div className="report-section">
          <h4 className="report-section-sub">퀴즈 결과</h4>
          {activeRecord.quizResult ? (
            <div className="report-item quiz-success-box">
              <span className="bullet green-bullet"></span>
              <span className="item-title text-green">{activeRecord.quizResult}</span>
            </div>
          ) : (
            <p className="no-data-text">응시한 퀴즈가 없습니다.</p>
          )}
        </div>

        {/* 4. 총 학습 시간 고정 하단바 */}
        <div className="total-time-footer-card">
          <span className="total-label">총 학습 시간</span>
          <span className="total-value">{activeRecord.totalTime}</span>
        </div>
      </div>
    </main>
  );
}