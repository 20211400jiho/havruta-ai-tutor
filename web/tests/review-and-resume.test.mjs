import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let vite;
let QuizReview;
let InterruptedSessions;
before(async () => {
  vite = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: "custom" });
  QuizReview = (await vite.ssrLoadModule("/src/QuizReview.jsx")).default;
  InterruptedSessions = (await vite.ssrLoadModule("/src/InterruptedSessions.jsx")).default;
});
after(async () => { await vite?.close(); });

const wrong = {
  is_correct: false, selected_index: 0, selected_answer: "처리하지 않고 배출",
  correct_index: 1, correct_answer: "오염물질을 제거한 후 배출",
  wrong_reason: "정화하지 않은 오염물질이 하천으로 흘러가기 때문입니다.",
  explanation: "배출 전에 오염물질을 줄여야 합니다.", review_tip: "두 보기의 차이를 설명해보세요.",
};
const session = {
  id: 10, subject: "사회", topic: "자연환경과 인간", school_level: "고등학교", grade: "1학년",
  checked_count: 2, total_count: 5, stage: "생각 수정", answer_count: 4,
  last_question: "개발이 필요한 경우 어떤 조건을 고려해야 하나요?",
  last_activity_at: "2026-10-25T03:00:00", state: "paused", can_resume: true, can_restart: true,
};
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));

test("wrong choice shows reason, correct answer and explanation separately", () => {
  const html = render(QuizReview, { item: wrong });
  for (const text of ["내가 고른 답 · 1번", "정답 · 2번", wrong.wrong_reason, wrong.explanation, "다시 생각하기"]) {
    assert.ok(html.includes(text));
  }
});
test("correct choice has explanation but no wrong-answer section", () => {
  const html = render(QuizReview, { item: { ...wrong, is_correct: true, wrong_reason: null } });
  assert.ok(html.includes("정답이에요") && html.includes(wrong.explanation));
  assert.ok(!html.includes("내가 고른 답"));
});
test("no explanation is rendered before grading", () => {
  assert.equal(render(QuizReview, { item: null }), "");
});
test("stored content is escaped instead of executed as markup", () => {
  const html = render(QuizReview, { item: { ...wrong, selected_answer: "<script>alert(1)</script>" } });
  assert.ok(html.includes("&lt;script&gt;") && !html.includes("<script>"));
});
test("interrupted card shows evidence count, last question and both actions", () => {
  const html = render(InterruptedSessions, { sessions: [session], suggestedId: 10 });
  for (const text of ["2/5", "내 답변 4회", "생각 수정", session.last_question, "지난 대화 보기", "이어서 학습", "처음부터 다시", "최근 열었던 학습"]) {
    assert.ok(html.includes(text), text);
  }
  assert.ok(!html.includes("40%"));
});
test("unavailable rooms disable restart and resume without hiding history", () => {
  const html = render(InterruptedSessions, { sessions: [{ ...session, can_resume: false, can_restart: false }] });
  assert.equal((html.match(/disabled=""/g) || []).length, 2);
  assert.ok(html.includes("기록만 볼 수 있어요") && html.includes("지난 대화 보기"));
});
test("empty history has no misleading progress card", () => {
  assert.equal(render(InterruptedSessions, { sessions: [] }), "");
});

test("only unavailable sessions expose explicit record deletion", () => {
  const unavailable = render(InterruptedSessions, { sessions: [{ ...session, can_resume: false, can_restart: false, can_delete: true }] });
  assert.ok(unavailable.includes("기록 삭제"));
  assert.ok(!render(InterruptedSessions, { sessions: [{ ...session, can_delete: false }] }).includes("기록 삭제"));
  const busy = render(InterruptedSessions, { sessions: [{ ...session, can_delete: true }], loading: true });
  assert.ok(busy.includes('class="resume-delete" disabled=""'));
});
