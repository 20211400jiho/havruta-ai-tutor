import React, { useState } from 'react';
import './SettingsView.css';

export default function SettingsView({ isDarkMode, toggleDarkMode, isReminderEnabled, toggleReminder }) {
  // 1. 프로필 정보 상태
  const [profile, setProfile] = useState({
    name: "김OO",
    grade: "2",
    school: "OO고등학교"
  });

  // 2. 수정 모드인지 확인하는 상태
  const [isEditing, setIsEditing] = useState(false);
  
  // 3. 수정 취소 시 되돌리기 위한 임시 상태
  const [tempProfile, setTempProfile] = useState(profile);

  const handleChange = (e) => {
    setTempProfile({ ...tempProfile, [e.target.name]: e.target.value });
  };

  const handleEdit = () => {
    setTempProfile(profile); // 수정 시작 시 현재 값 복사
    setIsEditing(true);
  };

  const handleSave = () => {
    setProfile(tempProfile); // 저장 시 반영
    setIsEditing(false);
    alert("정보가 저장되었습니다!");
  };

  const handleCancel = () => {
    setIsEditing(false); // 취소 시 수정 전 값으로 유지
  };

  return (
    <main className="content settings-page">
      <h2>설정</h2>
      <div className="settings-section">
        <div className="section-header">
          <h3>프로필 수정</h3>
          {!isEditing && <button className="edit-btn" onClick={handleEdit}>수정</button>}
        </div>

        <div className="input-group">
          <label>이름</label>
          <input name="name" value={isEditing ? tempProfile.name : profile.name} onChange={handleChange} disabled={!isEditing} />
        </div>
        <div className="input-group">
          <label>학교명</label>
          <input name="school" value={isEditing ? tempProfile.school : profile.school} onChange={handleChange} disabled={!isEditing} />
        </div>
        <div className="input-group">
          <label>학년</label>
          <select name="grade" value={isEditing ? tempProfile.grade : profile.grade} onChange={handleChange} disabled={!isEditing}>
            {[1, 2, 3].map(g => <option key={g} value={g}>{g}학년</option>)}
          </select>
        </div>

        <div className="setting-section">
          <h3>환경 설정</h3>
          <div className='toggle-group'>
            <span>다크 모드</span>
            <label className='switch'>
            <input
              type="checkbox"
              checked={isDarkMode}
              onChange={toggleDarkMode}
            />
            <span className='slider'></span>
            </label>
          </div>
          
          <div className="toggle-group">
            <span>학습 알림 받기</span>
            <label className="switch">
              <input 
                type="checkbox" 
                checked={isReminderEnabled} 
                onChange={toggleReminder} 
                />
              <span className="slider"></span>
            </label>
          </div>
        </div>

        {/* 수정 모드일 때만 저장/취소 버튼 표시 */}
        {isEditing && (
          <div className="button-group">
            <button className="save-btn" onClick={handleSave}>저장하기</button>
            <button className="cancel-btn" onClick={handleCancel}>취소</button>
          </div>
        )}
      </div>
    </main>
  );
}