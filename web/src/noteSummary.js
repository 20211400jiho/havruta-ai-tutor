const OBJECTIVES = [
  ["개념 설명", "핵심 개념을 자신의 말로 설명하기"],
  ["근거 확인", "설명한 내용의 이유와 근거 제시하기"],
  ["생각 수정", "반례를 검토하고 설명을 수정·보완하기"],
  ["적용", "새로운 사례나 문제에 개념 적용하기"],
  ["최종 정리", "배운 내용을 자신의 말로 다시 정리하기"],
];

export function getNoteSummary(note) {
  const sections = Array.isArray(note.sections) ? note.sections : [];
  const items = (title) => sections.find((section) => section.title === title)?.items || [];
  const field = (values, prefix) => values.find((value) => value.startsWith(prefix))?.slice(prefix.length).trim() || "";
  const explanations = items("핵심 개념과 나의 설명");
  const results = items("학습 결과");
  const latest = field(explanations, "마지막 설명:");
  const first = field(explanations, "처음 설명:");
  const objectives = OBJECTIVES.map(([stage, description]) => ({
    stage,
    // 저장된 체크 상태만 사용한다. 학생 문장의 길이로 이해 여부를 추측하지 않는다.
    checked: results.some((value) => value.startsWith(`${description}: AI 확인`)),
  }));
  return {
    goal: field(items("학습 개요"), "이번 대화의 학습목표:"),
    explanation: latest && latest !== "아직 설명을 작성하지 않았습니다." ? latest : first === "아직 설명을 작성하지 않았습니다." ? "" : first,
    strengths: [...new Set(items("잘한 점"))].slice(-2),
    review: field(results, "다음 복습:") || items("보완할 개념").at(-1) || "배운 내용을 예시와 함께 다시 설명해 보세요.",
    question: items("다시 생각할 질문").at(-1),
    objectives,
    hasProgress: results.some((value) => OBJECTIVES.some(([, description]) => value.startsWith(`${description}:`))),
  };
}
