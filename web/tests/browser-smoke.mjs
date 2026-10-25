// Run from web/: node tests/browser-smoke.mjs
// Isolated headless profile + in-browser API fixtures: no accounts or production writes.
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { createServer } from "vite";

function installFixtures() {
  localStorage.setItem("havruta_token", "local-ui-fixture-not-a-real-token");
  localStorage.setItem("havruta_active_session", "10");
  localStorage.setItem("havruta_theme", "light");
  window.confirm = () => true;
  window.__calls = [];
  const stages = ["개념 설명", "근거 확인", "생각 수정", "적용", "최종 정리"];
  const question = "개발이 필요한 경우 어떤 조건을 함께 고려해야 할까요?";
  const report = (count) => ({
    learning_goal: "인간과 자연환경은 어떤 관계일까요?", checked_count: count, total_count: 5,
    stage: stages[count], objectives: stages.map((stage, index) => ({ stage, description: `${stage}을 자신의 말로 설명하기`, status: index < count ? "ai_checked" : "not_checked" })),
  });
  const old = {
    id: 10, room_id: 1, user_id: 1, subject: "사회", topic: "자연환경과 인간", school_level: "고등학교", grade: "1학년", unit_code: "10통사1-03",
    state: "paused", stage: "생각 수정", checked_count: 2, total_count: 5, answer_count: 4,
    can_resume: true, can_restart: true, last_activity_at: "2026-10-25T03:00:00", last_question: question,
    messages: [
      { id: 1, sender_type: "ai", content: "자연환경과 인간은 어떤 관계일까요?" },
      { id: 2, sender_type: "user", content: "댐은 물을 공급하지만 생태계와 주민에게 피해를 줄 수도 있습니다." },
      { id: 3, sender_type: "ai", content: question, response_meta: { stage: "생각 수정", dialogue_state: { stage: "생각 수정" } } },
    ], learning_report: report(2),
  };
  const fresh = { ...old, id: 11, checked_count: 0, answer_count: 0, state: "questioning", stage: "개념 설명", learning_report: report(0),
    messages: [{ id: 4, sender_type: "ai", content: "자연환경과 인간은 어떤 관계일까요?", response_meta: { stage: "개념 설명" } }] };
  let restarted = false;
  const questions = [
    { id: 101, question: "하천 오염을 줄이기 위해 물을 어떻게 처리해야 할까요?", options: ["처리 없이 배출", "오염물질을 제거한 후 배출", "숲의 면적 측정", "홍수량 측정"] },
    { id: 102, question: "개발 사업을 판단할 때 무엇을 함께 고려해야 하나요?", options: ["일자리 수만 고려", "경제적 이익과 환경·주민의 영향", "편리함만 고려", "홍보 자료만 참고"] },
  ];
  let result = null;
  const quizSummary = () => ({ id: 40, title: "자연환경과 인간 복습 퀴즈", subject: "사회", total_questions: 2, best_score: result?.score ?? null, attempt_count: result ? 1 : 0, created_at: "2026-10-25T03:00:00Z" });
  const payload = (session) => ({ session, response_meta: { stage: session.stage } });
  window.fetch = async (input, options = {}) => {
    const path = new URL(input, location.href).pathname;
    const method = options.method || "GET";
    window.__calls.push({ path, method });
    if ((path.endsWith("/pause") && window.__failPause)
        || (path.endsWith("/restart") && window.__failRestart)
        || (path.endsWith("/submit") && window.__failSubmit)) {
      return new Response(JSON.stringify({ detail: "테스트용 일시 오류" }), { status: 503 });
    }
    let data;
    if (path === "/auth/me") data = { id: 1, name: "테스트 학생", email: "fixture@example.com", grade: "고등학교 1학년", role: "student" };
    else if (path === "/dashboard/me") data = { summary: { completed_sessions: 0 }, recent_records: [] };
    else if (path === "/sessions") data = { sessions: restarted ? [fresh, old] : [old] };
    else if (path === "/sessions/10/resume") { old.state = "questioning"; data = payload(old); }
    else if (path === "/sessions/10/pause") { old.state = "paused"; data = { ...payload(old), message: "대화와 진행 상태를 저장했습니다." }; }
    else if (path === "/sessions/10/restart") { restarted = true; old.state = "paused"; data = { ...payload(fresh), restarted_from_session_id: 10 }; }
    else if (path === "/sessions/10") data = payload(old);
    else if (path === "/quizzes") data = { quizzes: [quizSummary()] };
    else if (path === "/quizzes/40") data = { quiz: { ...quizSummary(), questions } };
    else if (path === "/quizzes/40/submit") {
      const answers = JSON.parse(options.body).answers;
      result = {
        attempt_id: 1, score: 50, correct_count: 1, total_questions: 2,
        results: questions.map((item, index) => ({
          question_id: item.id, selected_index: answers[index], selected_answer: item.options[answers[index]],
          correct_index: 1, correct_answer: item.options[1], is_correct: answers[index] === 1,
          wrong_reason: "처리 없이 배출하면 물속의 오염물질이 하천으로 흘러갑니다.",
          explanation: index ? "경제적 이익과 환경·주민에게 미치는 영향을 함께 고려해야 합니다." : "오염물질을 제거한 뒤 배출해야 하천의 수질과 생물을 보호할 수 있습니다.",
          review_tip: "문제의 핵심 조건을 찾고 정답인 이유를 자신의 말로 설명해보세요.",
        })),
      }; data = result;
    } else if (path === "/quizzes/40/review") data = result;
    else if (path === "/rag/catalog") data = { curriculum_year: "2022", subjects: [] };
    else if (path === "/rag/status") data = { subject: "사회", available: true };
    else throw new Error(`Unmocked API request: ${method} ${path}`);
    return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
  };
}

const output = await mkdtemp("/private/tmp/havruta-review-smoke-");
const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
let chrome;
let socket;
try {
  await vite.listen();
  const address = vite.httpServer.address();
  chrome = spawn(process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--remote-debugging-port=0", `--user-data-dir=${output}/browser-profile`, "about:blank",
  ], { stdio: "ignore" });
  let debugPort;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { debugPort = (await readFile(`${output}/browser-profile/DevToolsActivePort`, "utf8")).split("\n")[0]; break; }
    catch { await delay(100); }
  }
  assert.ok(debugPort, "Headless Chrome did not start");
  const pages = await (await fetch(`http://127.0.0.1:${debugPort}/json/list`)).json();
  socket = new WebSocket(pages.find((page) => page.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
  const pending = new Map();
  const exceptions = [];
  let nextId = 0;
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id) { const item = pending.get(message.id); pending.delete(message.id); message.error ? item.reject(message.error) : item.resolve(message.result); }
    else if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
  });
  const cdp = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const response = await cdp("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    assert.ok(!response.exceptionDetails, JSON.stringify(response.exceptionDetails));
    return response.result.value;
  };
  const wait = async (expression) => {
    for (let attempt = 0; attempt < 100; attempt++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(100); }
    throw new Error(`Timed out waiting for ${expression}`);
  };
  const click = async (text) => {
    await wait(`[...document.querySelectorAll('button')].some(button => button.textContent.trim() === ${JSON.stringify(text)} && !button.disabled)`);
    await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim() === ${JSON.stringify(text)}).click()`);
  };
  const screenshot = async (name, width, height, dark = false) => {
    await cdp("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 600 });
    await evaluate(`document.documentElement.setAttribute('data-theme', '${dark ? "dark" : "light"}'); window.scrollTo(0, 0); document.fonts.ready.then(() => true)`);
    await delay(150);
    const capture = await cdp("Page.captureScreenshot", { format: "png" });
    await writeFile(`${output}/${name}.png`, Buffer.from(capture.data, "base64"));
  };
  await cdp("Page.enable"); await cdp("Runtime.enable");
  await cdp("Page.addScriptToEvaluateOnNewDocument", { source: `(${installFixtures.toString()})();` });
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 1100, deviceScaleFactor: 1, mobile: false });
  await cdp("Page.navigate", { url: `http://127.0.0.1:${address.port}` });
  await wait("document.querySelector('.notebook-home')");
  await click("혼자 학습하기");
  await wait("document.querySelector('.resume-session')");
  assert.ok(await evaluate("!document.querySelector('.study-chat-container')"), "Must not silently auto-resume");
  assert.ok(await evaluate("document.querySelector('.resume-session').textContent.includes('2/5')"));
  await evaluate("document.querySelector('.resume-history summary').click()");
  await wait("document.querySelector('.resume-history ol')");
  await screenshot("resume-desktop", 1280, 1100);
  await screenshot("resume-mobile-dark", 390, 1000, true);
  await click("이어서 학습");
  await wait("document.querySelector('.study-chat-container')");
  assert.ok(await evaluate("document.querySelector('.learning-report-count').textContent.includes('2개 AI 확인')"));
  await evaluate("window.__failPause = true");
  await click("저장하고 나가기");
  await wait("document.querySelector('.study-error')");
  assert.ok(await evaluate("Boolean(document.querySelector('.study-chat-container'))"));
  await evaluate("window.__failPause = false");
  await click("저장하고 나가기");
  await wait("document.querySelector('.study-saved-notice')");
  await evaluate("window.__failRestart = true");
  await click("처음부터 다시");
  await wait("document.querySelector('.study-error')");
  assert.ok(await evaluate("document.querySelector('.resume-session').textContent.includes('2/5')"));
  await evaluate("window.__failRestart = false");
  await click("처음부터 다시");
  await wait("document.querySelector('.study-chat-container')");
  assert.ok(await evaluate("document.querySelector('.learning-report-count').textContent.includes('0개 AI 확인')"));
  assert.equal(await evaluate("document.querySelectorAll('.message-row').length"), 1);
  await click("퀴즈");
  await wait("document.querySelector('.btn-quiz-start')");
  await click("풀기 ➔");
  await wait("document.querySelectorAll('.quiz-question-block').length === 2");
  assert.equal(await evaluate("document.querySelectorAll('.quiz-review').length"), 0);
  await evaluate("document.querySelectorAll('.quiz-question-block')[0].querySelectorAll('.quiz-option')[0].click()");
  await evaluate("document.querySelectorAll('.quiz-question-block')[1].querySelectorAll('.quiz-option')[1].click()");
  await evaluate("window.__failSubmit = true");
  await click("채점하기");
  await wait("document.querySelector('.study-error')");
  assert.equal(await evaluate("document.querySelectorAll('.quiz-option[aria-pressed=true]').length"), 2);
  await evaluate("window.__failSubmit = false");
  await click("채점하기");
  await wait("document.querySelector('.quiz-review')");
  assert.ok(await evaluate("document.querySelector('.quiz-wrong-reason').textContent.includes('오염물질')"));
  await screenshot("quiz-desktop", 1280, 1200);
  await screenshot("quiz-mobile-dark", 390, 1000, true);
  assert.equal(await evaluate("getComputedStyle(document.querySelector('.quiz-option:disabled')).opacity"), "1", "Graded options must remain legible");
  assert.ok(await evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile page must not overflow horizontally");
  await evaluate("document.querySelector('.quiz-review-toolbar input').click()");
  await wait("document.querySelectorAll('.quiz-question-block').length === 1");
  await click("← 목록으로");
  const submittedCalls = await evaluate("window.__calls.filter(call => call.path.endsWith('/submit')).length");
  await click("지난 답안·해설");
  await wait("document.querySelector('.quiz-review')");
  assert.equal(await evaluate("window.__calls.filter(call => call.path.endsWith('/submit')).length"), submittedCalls);
  await click("다시 풀기");
  await wait("!document.querySelector('.quiz-review')");
  assert.equal(await evaluate("document.querySelectorAll('.quiz-option[aria-pressed=true]').length"), 0);
  assert.deepEqual(exceptions, []);
  console.log(JSON.stringify({ status: "passed", mockedApi: true, noProductionWrites: true,
    checks: ["resume choice instead of auto-open", "saved transcript preview", "resume preserves 2/5", "pause saves without finishing", "restart begins at 0/5", "no early answer leak", "wrong-answer explanation", "wrong-only filter", "restore last answer without resubmitting", "retry clears previous choices", "pause error retains chat", "restart error retains progress", "submit error retains choices", "no mobile horizontal overflow"],
    screenshots: output }, null, 2));
} finally {
  socket?.close(); chrome?.kill(); await vite.close();
}
