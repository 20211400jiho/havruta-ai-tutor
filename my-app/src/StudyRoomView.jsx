import React, { useState } from 'react';
import './StudyRoomView.css';

export default function StudyRoomView() {
    const [view, setView] = useState('HOME'); // HOME, CREATE, JOIN, WAITING, CHAT
    const [inviteCode, setInviteCode] = useState('');
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');

    // 1. 방 생성 (코드 생성)
    const handleCreateRoom = () => {
        const code = Math.random().toString(36).substring(2, 8).toUpperCase();
        setInviteCode(code);
        setView('CREATE');
    };

    // 2. 코드 복사 (공유)
    const copyCode = () => {
        // inviteCode가 있다면 그걸 복사하고, 없으면 기본 메시지 복사
        const codeToCopy = inviteCode || "스터디코드123";
        navigator.clipboard.writeText(codeToCopy).then(() => {
            alert('코드가 복사되었습니다!');
        });
    };

    // 3. 카카오톡 공유
    const shareKakao = () => {
        alert("카카오톡 공유 기능을 구현해보세요!");
    };

    // 4. 참여 (코드 검증)
    const handleJoinRoom = (e) => {
        e.preventDefault();
        if (inviteCode.length === 6) { 
            setView('CHAT');
        } else {
            alert('올바른 초대 코드를 입력해주세요.');
        }
    };

    return (
        <main className="content study-room-page">
            {view === 'HOME' && (
                <div className="center-card">
                    <h2>그룹 학습 세션</h2>
                    <p>친구와 함께 실시간으로 학습을 시작하세요.</p>
                    <div className="button-group">
                        <button className="btn-primary" onClick={handleCreateRoom}>스터디룸 생성</button>
                        <button className="btn-primary" onClick={() => setView('JOIN')}>코드 입력 참여</button>
                    </div>
                </div>
            )}

            {view === 'CREATE' && (
                <div className="center-card">
                    <h3>초대 코드 생성 완료!</h3>
                    <div className="code-box">{inviteCode}</div>
                    <div className="button-group">
                        <button className="btn-primary" onClick={copyCode}>코드 복사</button>
                        <button className="btn-primary" onClick={shareKakao}>카카오톡 공유</button>
                    </div>
                    <p className="wait-msg">참여자를 기다리는 중...</p>
                    <button className="start-btn" onClick={() => setView('CHAT')}>참여자 입장 시뮬레이션</button>
                </div>
            )}

            {view === 'JOIN' && (
                <div className="center-card">
                    <h3>초대 코드 입력</h3>
                    <input type="text" placeholder="6자리 코드 입력" onChange={(e) => setInviteCode(e.target.value)} />
                    <button className="btn-primary" onClick={handleJoinRoom}>입장하기</button>
                </div>
            )}

            {view === 'CHAT' && (
                <div className="chat-container">
                    <div className="chat-header">
                    <h3>하브루타 학습 세션</h3>
                    <span className="status">● 연결됨</span>
                    </div>
                    
                    <div className="chat-messages">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`message-row ${msg.sender}`}>
                        {/* 친구나 AI일 때만 프로필 이미지 표시 */}
                        {(msg.sender === 'ai' || msg.sender === 'friend') && (
                            <img 
                            src={msg.sender === 'ai' ? '/study_ai.png' : '/friend_profile.png'} 
                            alt={msg.sender} 
                            className="avatar" 
                            />
                        )}
                        
                        <div className="bubble">
                            {msg.text}
                        </div>
                        </div>
                    ))}
                    </div>

                    <div className="chat-input">
                    <input 
                        value={inputText} 
                        onChange={(e) => setInputText(e.target.value)} 
                        placeholder="대화를 입력하세요..." 
                    />
                    <button onClick={() => {
                        setMessages([...messages, { sender: 'user', text: inputText }]);
                        setInputText('');
                    }}>전송</button>
                    </div>
                </div>
                )}
        </main>
    );
}