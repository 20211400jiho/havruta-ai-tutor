import MathText from "./MathText";

export default function StudyCompletion({ report, completion, onNotes, onQuiz, onNewStudy }) {
  if (!report) return null;
  const checked = (report.objectives || []).filter((item) => item.status === "ai_checked");
  const complete = checked.length === 5;
  const highlights = checked.filter((item) => item.evidence_quote).filter((_, index, items) => index === 0 || index === items.length - 1);
  return <section className="study-ending" aria-labelledby="study-ending-title">
    <span className="study-kicker">{complete ? "학습목표 확인 완료 · 5/5" : `이번 학습 기록 · ${checked.length}/5`}</span>
    <h2 id="study-ending-title">{complete ? "오늘의 배움을 정리했어요" : "여기까지의 배움을 남겼어요"}</h2>
    <p>{complete ? "오늘 계획한 5개 목표를 모두 확인했어요. 대화와 정리노트를 자동 저장했습니다." : "확인된 내용과 아직 확인하지 않은 내용을 그대로 저장했어요. 미확인은 오답이 아니에요."}</p>
    {highlights.length > 0 && <div className="study-ending-summary"><h3>내가 설명한 핵심</h3><ul>{highlights.map((item) => <li key={item.stage}><strong>{item.stage}</strong><MathText text={item.evidence_quote.length > 180 ? `${item.evidence_quote.slice(0, 180)}…` : item.evidence_quote} /></li>)}</ul></div>}
    <p className="study-ending-strength">{complete ? "개념부터 적용과 정리까지, 자신의 답변으로 목표를 확인했어요." : "남긴 설명은 정리노트에서 다시 볼 수 있어요."}</p>
    <p><strong>다음 복습</strong> · <MathText text={report.next_review || "시간을 두고 다른 문제로 다시 확인해 보세요."} /></p>
    <div className="study-ending-actions"><button type="button" disabled={!completion?.note_id} onClick={onNotes}>정리노트 보기</button><button type="button" onClick={onQuiz}>복습 퀴즈 풀기</button><button type="button" onClick={onNewStudy}>다른 단원 시작</button></div>
    <small>이번에 정한 목표의 확인 기록이며, 단원 전체의 완벽한 숙달을 뜻하지는 않아요.</small>
  </section>;
}
