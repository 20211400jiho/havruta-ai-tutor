import React, { useState } from 'react';
import './StudyView.css';
import aiImage from './assets/study_ai.png';

export default function StudyView() {
    const [messages, setMessages] = useState([
    { id: 1, sender: 'user', text: '오늘 학교에서 광합성이라는 걸 배웠어' },
    { id: 2, sender: 'ai', text: '오늘 배운건 광합성이구나!\n광합성이 뭐야?' },
    { id: 3, sender: 'user', text: '광합성이란 식물이 빛 에너지를 이용하여 이산화탄소와 물로부터 유기물을 만들고 산소를 내보내는 과정이야' },
    { id: 4, sender: 'ai', text: '광합성은 식물의 어디에서 이뤄지는거야?' },
    { id: 5, sender: 'user', text: '광합성은 식물의 엽록체에서 일어나' },
    ]);
    const [input, setInput] = useState('');

    return (
    <div className="study-chat-container">
        {/* 메시지 리스트 */}
        <div className="chat-messages">
        {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.sender}`}>
            {msg.sender === 'ai' && <img src={aiImage} alt="AI" className="ai-avatar" />}
            <div className="bubble">
                {msg.text.split('\n').map((line, i) => <p key={i}>{line}</p>)}
            </div>
            </div>
        ))}
        </div>

        {/* 하단 입력창 */}
        <div className="chat-input-bar">
        <input 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            placeholder="질문을 입력하세요..." 
        />
        <button className="send-btn">➤</button>
        </div>
        </div>
        );
}