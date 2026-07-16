// QuizView.jsx
import React, { useState } from 'react';
import './QuizView.css';

const dummyQuizHistory = [
  {
    id: "quiz-abc-1",
    title: "🌱 광합성과 식물의 호흡 심화 복습",
    date: "2026-07-10",
    totalQuestions: 3,
    questions: [
      {
        id: 1,
        question: "Q1. 광합성에 대한 설명으로 옳은 것은?",
        options: [
          "식물은 빛 에너지를 이용하여 포도당을 만든다.",
          "식물은 빛 에너지를 이용하여 산소를 흡수한다.",
          "식물은 이산화탄소를 흡수하고 물을 방출한다.",
          "식물은 빛 에너지를 이용하여 이산화탄소를 분해한다."
        ],
        correctAnswer: 0
      },
      {
        id: 2,
        question: "Q2. 식물의 호흡 과정에서 주로 흡수하는 기체는 무엇인가요?",
        options: ["이산화탄소", "산소", "질소", "수소"],
        correctAnswer: 1
      },
      {
        id: 3,
        question: "Q3. 광합성이 일어나는 식물 세포 내의 기관은 어디인가요?",
        options: ["미토콘드리아", "핵", "엽록체", "세포벽"],
        correctAnswer: 2
      }
    ]
  },
  {
    id: "quiz-abc-2",
    title: "📐 이차함수의 최대·최소 핵심 퀴즈",
    date: "2026-07-08",
    totalQuestions: 2,
    questions: [
      {
        id: 1,
        question: "Q1. 이차함수 y = (x-2)² + 3 의 최솟값은 얼마인가요?",
        options: ["2", "3", "-2", "-3"],
        correctAnswer: 1
      },
      {
        id: 2,
        question: "Q2. 이차함수의 그래프가 위로 볼록할 때, x²의 계수의 부호는?",
        options: ["양수 (+)", "음수 (-)", "0", "알 수 없다"],
        correctAnswer: 1
      }
    ]
  },
  {
    id: "quiz-abc-3",
    title: "⚔️ 삼국 성립과 한강 유역 쟁탈전",
    date: "2026-07-05",
    totalQuestions: 2,
    questions: [
      {
        id: 1,
        question: "Q1. 5세기 한강 유역을 차지하며 고구려의 전성기를 이끈 왕은?",
        options: ["광개토대왕", "장수왕", "근초고왕", "진흥왕"],
        correctAnswer: 1
      },
      {
        id: 2,
        question: "Q2. 백제 성왕과 신라 진흥왕이 연합하여 고구려를 공격했던 시기로 옳은 것은?",
        options: ["4세기", "5세기", "6세기", "7세기"],
        correctAnswer: 2
      }
    ]
  }
];

export default function QuizView() {
  const [viewMode, setViewMode] = useState('list');
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState({});

  const handleStartQuiz = (quiz) => {
    setCurrentQuiz(quiz);
    setCurrentIndex(0);
    setSelectedAnswers({});
    setViewMode('play');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setCurrentQuiz(null);
  };

  const handleSelectOption = (optionIndex) => {
    if (selectedAnswers[currentIndex] !== undefined) return;
    setSelectedAnswers({
      ...selectedAnswers,
      [currentIndex]: optionIndex
    });
  };

  const handleNext = () => {
    if (!currentQuiz) return;
    if (currentIndex < currentQuiz.questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      alert("퀴즈가 모두 끝났습니다! 수고하셨습니다.");
      setViewMode('list');
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  // VIEW 1: 퀴즈 목록 화면
  if (viewMode === 'list') {
    return (
      <main className="content">
        <div className="quiz-list-header">
          <div>
            <h2 className="quiz-main-title">AI 생성 퀴즈 보관함</h2>
            <p className="quiz-main-sub">학습 노트를 바탕으로 생성된 복습 퀴즈 목록입니다.</p>
          </div>
          <button className="btn-generate-quiz" onClick={() => alert('새로운 노트 요약 기반 퀴즈 생성 기능은 준비 중입니다!')}>
            ✨ 새 퀴즈 생성하기
          </button>
        </div>

        <div className="quiz-grid">
          {dummyQuizHistory.map((quiz) => (
            <div key={quiz.id} className="quiz-history-card">
              <div className="card-top">
                <span className="quiz-card-date">{quiz.date}</span>
                <span className="quiz-card-count">{quiz.totalQuestions}문항</span>
              </div>
              <h3 className="quiz-card-title">{quiz.title}</h3>
              <div className="card-bottom">
                <button className="btn-quiz-start" onClick={() => handleStartQuiz(quiz)}>
                  다시 풀기 ➔
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    );
  }

  if (!currentQuiz || !currentQuiz.questions) {
    return (
      <main className="content">
        <div style={{ textAlign: 'center', marginTop: '40px', color: 'black' }}>
          <p>퀴즈 데이터를 불러오는 중입니다...</p>
          <button className="btn-back" onClick={handleBackToList}>🏠 목록으로 돌아가기</button>
        </div>
      </main>
    );
  }

  const activeQuestion = currentQuiz.questions[currentIndex];
  const totalQuestions = currentQuiz.questions.length;

  return (
    <main className="content">
      <div className="quiz-container">
        
        <div className="quiz-header">
          <div className="quiz-header-left">
            <button className="btn-back" onClick={handleBackToList}>🏠 목록으로</button>
            <h2 className="quiz-title-context">{currentQuiz.title}</h2>
          </div>
          <div className="quiz-progress">
            <span className="quiz-progress-current">{currentIndex + 1}</span>/{totalQuestions}
          </div>
        </div>

        <h3 className="quiz-question">{activeQuestion.question}</h3>

        <div className="quiz-options">
          {activeQuestion.options.map((option, index) => {
            const userSelection = selectedAnswers[currentIndex];
            const isSelected = userSelection === index;
            const isCorrectAnswer = activeQuestion.correctAnswer === index;
            
            let optionClass = "";
            if (userSelection !== undefined) {
              if (isCorrectAnswer) optionClass = "correct";
              else if (isSelected && !isCorrectAnswer) optionClass = "incorrect";
            }

            return (
              <div
                key={index}
                className={`quiz-option ${optionClass}`}
                onClick={() => handleSelectOption(index)}
              >
                <div className="option-number">{index + 1}</div>
                {option}
              </div>
            );
          })}
        </div>

        <div className="quiz-footer">
          <button 
            className="btn-prev" 
            onClick={handlePrev}
            style={{ visibility: currentIndex === 0 ? 'hidden' : 'visible' }}
          >
            이전
          </button>
          <button 
            className="btn-next" 
            onClick={handleNext}
            disabled={selectedAnswers[currentIndex] === undefined}
          >
            {currentIndex === totalQuestions - 1 ? "종료하기" : "다음"}
          </button>
        </div>

      </div>
    </main>
  );
}