// CalendarView.jsx
import { useEffect, useState } from 'react';
import './CalendarView.css';
import { api } from './api';

export default function CalendarView() {
  // 1. 현재 시스템의 실시간 날짜를 초기값으로 설정
  const today = new Date();
  const [currentDate, setCurrentDate] = useState(today); // 달력 내비게이션용 (년, 월)
  const [selectedDate, setSelectedDate] = useState(today); // 우측 리포트 표시용 (년, 월, 일)
  const [records, setRecords] = useState([]);
  useEffect(() => { api('/dashboard/me').then((result) => setRecords(result.recent_records || [])).catch(() => {}); }, []);

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

  const learningRecords = records.reduce((accumulator, record) => {
    if (!record.completed_at) return accumulator;
    const date = new Date(record.completed_at);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    const current = accumulator[key] || { dateText: `${date.getMonth() + 1}월 ${date.getDate()}일`, records: [], notes: [], completedCount: 0 };
    const scoreText = record.average_score == null ? '' : ` · 응답 평가 ${record.average_score}점`;
    current.records.push({ title: record.topic || '하브루타 학습', detail: `${record.total_messages}개 메시지${scoreText}`, color: '#4f7df3' });
    current.notes.push(`${record.topic || '학습'} 핵심 정리`);
    current.completedCount = current.records.length;
    accumulator[key] = current;
    return accumulator;
  }, {});

  const selectedDateKey = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
  
  const activeRecord = learningRecords[selectedDateKey] || {
    dateText: `${selectedDate.getMonth() + 1}월 ${selectedDate.getDate()}일`,
    records: [],
    notes: [],
    completedCount: 0
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

            // 실제 학습 기록이 있는 날짜에 표시할 키 생성
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

        {/* 서버가 제공하는 실제 완료 세션 수 */}
        <div className="total-time-footer-card">
          <span className="total-label">완료한 학습</span>
          <span className="total-value">{activeRecord.completedCount}회</span>
        </div>
      </div>
    </main>
  );
}
