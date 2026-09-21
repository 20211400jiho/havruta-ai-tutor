import "./LearningReport.css";

export default function LearningReport({ report, finished = false }) {
  if (!report || !Array.isArray(report.objectives)) return null;
  const checked = report.objectives.filter((item) => item.status === "ai_checked").length;
  return (
    <details className={`learning-report${finished ? " learning-report--finished" : ""}`} open={finished}>
      <summary className="learning-report-summary">
        <span className="learning-report-heading">
          <span className="learning-report-title">{finished ? "이번 학습 돌아보기" : "학습목표와 진행"}</span>
          <span className="learning-report-count">전체 {report.objectives.length}개 항목 중 <strong>{checked}개 AI 확인</strong></span>
        </span>
        <span className="learning-report-chevron" aria-hidden="true">⌄</span>
      </summary>
      <div className="learning-report-body">
        <section className="learning-report-goal" aria-label="이번 대화의 목표 질문">
          <h3>이번 대화의 목표 질문</h3>
          <p>{report.learning_goal || report.topic || "학습목표 기록이 없습니다."}</p>
        </section>

        <section className="learning-report-objectives" aria-label="단계별 확인 기록">
          <h3>단계별 확인 기록</h3>
          {report.assessment_message && <p className="learning-report-empty" role="status">{report.assessment_message}</p>}
          {checked === 0 && <p className="learning-report-empty">아직 AI가 이해를 확인한 항목이 없어요. 틀렸다는 뜻은 아니에요.</p>}
          <ol className="learning-report-steps">
            {report.objectives.map((item, index) => (
              <li key={item.stage} className={item.status === "ai_checked" ? "is-checked" : ""}>
                <span className="learning-report-step-number" aria-hidden="true">{index + 1}</span>
                <div className="learning-report-step-content">
                  <div className="learning-report-step-heading">
                    <strong>{item.stage}</strong>
                    <span className="learning-report-status">{item.status === "ai_checked" ? "AI 확인" : "아직 확인 전"}</span>
                  </div>
                  <p>{item.description}</p>
                  {item.evidence_quote && <blockquote><span>확인에 사용된 내 설명</span>{item.evidence_quote}</blockquote>}
                </div>
              </li>
            ))}
          </ol>
        </section>

        {finished && <section className="learning-report-reflection" aria-label="내 설명 돌아보기">
          <h3>내 설명 돌아보기</h3>
          <div className="learning-report-comparison">
            <div><h4>처음 남긴 설명</h4><p>{report.first_explanation || "작성한 설명이 없어요."}</p></div>
            <div><h4>마지막에 남긴 설명</h4><p>{report.has_comparison ? report.latest_explanation : "비교할 두 번째 설명이 아직 없어요."}</p></div>
          </div>
          <p className="learning-report-caption">서로 다른 질문에 대한 답일 수 있어요. 설명의 길이나 내용만으로 학습 향상을 판단하지 않아요.</p>
        </section>}

        <section className="learning-report-review" aria-label="다음 복습">
          <h3>다음에는 이렇게 복습해요</h3>
          <p>{report.next_review || "배운 개념을 자신의 말로 다시 설명해 보세요."}</p>
          {report.misconception && <p className="learning-report-caption">다시 확인할 개념: {report.misconception}</p>}
        </section>
        <p className="learning-report-notice">{report.notice || "AI의 잠정적 확인 기록입니다. 미확인은 오답이 아니며, 학습효과나 단원 전체 숙달을 증명하지 않습니다."}</p>
        {finished && <p className="learning-report-saved">이 기록은 정리노트에서도 다시 볼 수 있어요.</p>}
      </div>
    </details>
  );
}
