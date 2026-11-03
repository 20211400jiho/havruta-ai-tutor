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
    learning_goal: "인간과 자연환경은 어떤 관계일까요? 수식 확인: $y=ax$", checked_count: count, total_count: 5,
    completion_ready: count === 5, progress_message: count === 4 ? "마지막 정리만 남았어요." : `${count}/5 확인`,
    stage: stages[Math.min(count, 4)], objectives: stages.map((stage, index) => ({ stage, description: `${stage}을 자신의 말로 설명하기`, status: index < count ? "ai_checked" : "not_checked", evidence_quote: index < count ? `${stage}을 내 말로 설명했습니다.` : null })),
  });
  const old = {
    id: 10, room_id: 1, user_id: 1, subject: "사회", topic: "자연환경과 인간", school_level: "고등학교", grade: "1학년", unit_code: "10통사1-03",
    state: "paused", stage: "생각 수정", checked_count: 2, total_count: 5, answer_count: 4,
    can_resume: true, can_restart: true, last_activity_at: "2026-10-25T03:00:00", last_question: question,
    messages: [
      { id: 1, sender_type: "ai", content: String.raw`수식 표시 테스트: $y=ax$, $a\neq0$, $y=-3x$, $\frac{y}{x}=a$, $x^2+2x+1$, $2x-3=7$. 블록: \[x_1+x_2+x_3+x_4+x_5+x_6+x_7+x_8+x_9+x_{10}+x_{11}+x_{12}=100\]` },
      { id: 2, sender_type: "user", content: String.raw`학생 답변: \(y=-3x\) 한글 English
두 번째 줄. <script>window.__unsafe=true</script>` },
      { id: 3, sender_type: "ai", content: question, response_meta: { stage: "생각 수정", dialogue_state: { stage: "생각 수정" }, sources: [{ source_id: "fixture-math", subject: "수학", excerpt: String.raw`수식 표시 확인: $y=ax$` }] } },
    ], learning_report: report(2),
  };
  const fresh = { ...old, id: 11, checked_count: 0, answer_count: 0, state: "questioning", stage: "개념 설명", learning_report: report(0),
    messages: [{ id: 4, sender_type: "ai", content: "자연환경과 인간은 어떤 관계일까요?", response_meta: { stage: "개념 설명" } }] };
  let restarted = false;
  let deletedUnavailable = false;
  const unavailable = { ...old, id: 12, topic: "이용 종료된 학습", can_resume: false, can_restart: false, can_delete: true };
  let messageSequence = 20;
  const questions = [
    { id: 101, question: String.raw`하천 오염을 줄이기 위해 물을 어떻게 처리해야 할까요? (수식 표시 확인: $\frac{y}{x}=a$)`, options: ["처리 없이 배출 (표시 확인: $x^2$)", "오염물질을 제거한 후 배출", "숲의 면적 측정", "홍수량 측정"] },
    { id: 102, question: "개발 사업을 판단할 때 무엇을 함께 고려해야 하나요?", options: ["일자리 수만 고려", "경제적 이익과 환경·주민의 영향", "편리함만 고려", "홍보 자료만 참고"] },
  ];
  let result = null;
  const quizSummary = () => ({ id: 40, title: "자연환경과 인간 복습 퀴즈", subject: "사회", total_questions: 2, best_score: result?.score ?? null, attempt_count: result ? 1 : 0, created_at: "2026-10-25T03:00:00Z" });
  const payload = (session) => ({ session, response_meta: { stage: session.stage } });
  window.fetch = async (input, options = {}) => {
    const path = new URL(input, location.href).pathname;
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(options.body) : null;
    window.__calls.push({ path, method, body });
    if ((path.endsWith("/pause") && window.__failPause)
        || (path.endsWith("/restart") && window.__failRestart)
        || (path.endsWith("/submit") && window.__failSubmit)
        || (path.endsWith("/messages") && window.__failHelp)) {
      return new Response(JSON.stringify({ detail: "테스트용 일시 오류" }), { status: 503 });
    }
    let data;
    if (path === "/auth/me") data = { id: 1, name: "테스트 학생", email: "fixture@example.com", grade: "고등학교 1학년", role: "student" };
    else if (path === "/dashboard/me") data = { summary: { completed_sessions: 0 }, recent_records: [] };
    else if (path === "/sessions") data = { sessions: [...(restarted ? [fresh, old] : [old]), ...(!deletedUnavailable ? [unavailable] : [])] };
    else if (path === "/sessions/12" && method === "DELETE") {
      if (window.__failDelete) return new Response(JSON.stringify({ detail: "삭제 테스트 오류" }), { status: 503 });
      deletedUnavailable = true;
      data = { deleted_session_id: 12, message: "이용할 수 없는 학습의 대화와 진행 기록을 삭제했습니다." };
    }
    else if (path === "/sessions/10/resume") {
      old.state = window.__completeOnResume ? "finished" : "questioning";
      if (window.__completeOnResume) old.learning_report = report(5);
      data = { ...payload(old), ...(window.__completeOnResume ? {completion:{note_id:80,record_id:90,goals_completed:true,learning_report:report(5),scope:{subject:"사회",schoolLevel:"고등학교",grade:"1학년",unitCode:"10통사1-03"}}} : {}) };
    }
    else if (path === "/sessions/10/pause") { old.state = "paused"; data = { ...payload(old), message: "대화와 진행 상태를 저장했습니다." }; }
    else if (path === "/sessions/10/restart") { restarted = true; old.state = "paused"; data = { ...payload(fresh), restarted_from_session_id: 10 }; }
    else if (path === "/sessions/10") data = payload(old);
    else if (path === "/sessions/11/messages") {
      if (window.__failCompletion) return new Response(JSON.stringify({detail:"완료 저장 테스트 오류"}),{status:503});
      const complete = fresh.checked_count === 4;
      fresh.checked_count = complete ? 5 : 4;
      fresh.learning_report = report(fresh.checked_count);
      fresh.state = complete ? "finished" : "questioning";
      data = {message:{id:messageSequence++,sender_type:"ai",content:complete?"오늘의 학습목표를 모두 확인했어요.":"마지막으로 핵심을 정리해볼까요?"},learning_report:fresh.learning_report,session_state:fresh.state,
        completion:complete?{note_id:80,record_id:90,goals_completed:true,learning_report:report(5),scope:{subject:"사회",schoolLevel:"고등학교",grade:"1학년",unitCode:"10통사1-03"}}:null};
    }
    else if (path === "/sessions/10/messages") {
      if (window.__delayHelp) await new Promise((resolve) => { window.__releaseHelp = resolve; });
      if (body.help_action !== "hint") throw new Error("Only the hint option is exposed by this UI");
      const meta = {
        stage: "생각 수정", ai_provider: "openai", help_action: body.help_action, sources: [],
        hint: { level: 1, trigger: "requested", keywords: ["개발의 이익", "주변의 영향"], text: "영향을 받는 사람이나 환경을 떠올려보세요." },
      };
      const message = { id: messageSequence++, sender_type: "ai", response_meta: meta,
        content: "정답 대신 생각을 시작할 단서를 줄게요. 개발로 달라지는 대상은 누구일까요?" };
      old.messages.push({ id: messageSequence++, sender_type: "user", content: body.content, response_meta: { help_action: body.help_action } }, message);
      data = { message, response_meta: meta, learning_report: report(2), feedback: { assessment: "unassessed", level: "힌트 단계", strengths: "도움 요청은 학습목표를 자동으로 체크하지 않아요." } };
    }
    else if (path === "/notes") data = { notes: [{ id: 80, title: "수학 수식 복습", subject: "수학" }] };
    else if (path === "/notes/80") data = { note: { id: 80, title: "수학 수식 복습", subject: "수학", sections: [
      { title: "핵심 개념과 나의 설명", items: [String.raw`마지막 설명: 비율은 $\frac{y}{x}=a$입니다.`] },
      { title: "학습 개요", items: ["이번 대화의 학습목표: $y=ax$ 설명하기"] },
    ] } };
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
    else if (path === "/rag/catalog") data = {name:new URL(input,location.href).searchParams.get("subject"),curriculum_year:"2022",school_levels:[{name:"고등학교",grades:[{name:"1학년",units:[{code:"10통사1-03",title:"자연환경과 인간"}]}]}]};
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
  const screenshot = async (name, width, height, dark = false, targetSelector = null) => {
    await cdp("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 600 });
    await evaluate(`document.documentElement.setAttribute('data-theme', '${dark ? "dark" : "light"}'); window.scrollTo(0, 0); document.fonts.ready.then(() => true)`);
    if (targetSelector) await evaluate(`document.querySelector(${JSON.stringify(targetSelector)}).scrollIntoView({block: 'end', behavior: 'instant'})`);
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
  assert.equal(await evaluate("document.querySelectorAll('.resume-delete').length"), 1);
  await evaluate("window.confirm = () => false; document.querySelector('.resume-delete').click()");
  assert.equal(await evaluate("window.__calls.filter(call => call.method === 'DELETE').length"), 0);
  await evaluate("window.confirm = () => true; window.__failDelete = true; document.querySelector('.resume-delete').click()");
  await wait("document.querySelector('.study-error')");
  assert.equal(await evaluate("document.querySelectorAll('.resume-delete').length"), 1, "Failed deletion keeps the card");
  await evaluate("window.__failDelete = false; localStorage.setItem('havruta_active_session', '12')");
  await click("기록 삭제");
  await wait("!document.querySelector('.resume-delete')");
  assert.ok(await evaluate("!localStorage.getItem('havruta_active_session')"));
  assert.equal(await evaluate("document.querySelectorAll('.resume-session').length"), 1, "Other learning remains");
  assert.ok(await evaluate("!document.querySelector('.study-chat-container')"), "Must not silently auto-resume");
  assert.ok(await evaluate("document.querySelector('.resume-session').textContent.includes('2/5')"));
  await evaluate("document.querySelector('.resume-history summary').click()");
  await wait("document.querySelector('.resume-history ol')");
  assert.ok(await evaluate("document.querySelectorAll('.resume-history .katex').length >= 8"), "Saved transcript preview must render equations too");
  await screenshot("resume-desktop", 1280, 1100);
  await screenshot("resume-mobile-dark", 390, 1000, true);
  await click("이어서 학습");
  await wait("document.querySelector('.study-chat-container')");
  await evaluate("[...document.querySelectorAll('.evidence-panel summary')].find(e => e.textContent.includes('참고한 학습 자료')).click()");
  assert.ok(await evaluate("Boolean(document.querySelector('.evidence-list .katex'))"), "Reference excerpts render math");
  assert.ok(await evaluate("document.querySelector('.learning-report-count').textContent.includes('2개 AI 확인')"));
  await wait("document.querySelectorAll('.message-row.ai .bubble .katex').length === 7");
  assert.equal(await evaluate("document.querySelectorAll('.message-row.user .katex').length"), 1);
  assert.ok(await evaluate(`['ai', 'user'].every(role => {
    const bubble = document.querySelector('.message-row.' + role + ' .bubble');
    const style = getComputedStyle(bubble);
    const text = getComputedStyle(bubble.querySelector('.math-text'));
    return style.paddingTop === '12px' && style.paddingBottom === '12px'
      && style.paddingLeft === '16px' && style.paddingRight === '16px'
      && Math.abs(parseFloat(style.lineHeight) / parseFloat(style.fontSize) - 1.5) < .01
      && text.lineHeight === style.lineHeight;
  })`), "Both chat bubbles have comfortable padding and normal inherited line spacing");
  assert.ok(await evaluate("!window.__unsafe && !document.querySelector('.bubble script')"));
  await evaluate("document.querySelector('.learning-report-summary').click()");
  assert.ok(await evaluate("Boolean(document.querySelector('.learning-report .katex'))"));
  await evaluate("document.querySelector('.learning-report-summary').click(); document.querySelector('.chat-messages').scrollTop = 0");
  await screenshot("math-desktop", 1280, 1100, false, ".chat-messages");
  await screenshot("math-mobile-dark", 390, 1000, true, ".chat-messages");
  assert.ok(await evaluate("document.documentElement.scrollWidth <= innerWidth + 1"));
  assert.ok(await evaluate("document.querySelector('.math-text-display').scrollWidth > document.querySelector('.math-text-display').clientWidth"), "Long display equation must scroll inside its container");
  assert.ok(await evaluate("[...document.querySelectorAll('.katex .mord')].some(e => getComputedStyle(e).fontFamily.includes('KaTeX'))"));
  await evaluate(`(() => {
    const input = document.querySelector('.chat-input-bar textarea');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(input, '작성 중인 나의 설명입니다.');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    window.__delayHelp = true;
  })()`);
  assert.equal(await evaluate("document.querySelectorAll('.study-help-actions button').length"), 1);
  assert.equal(await evaluate("document.querySelector('.study-help-actions button').textContent.trim()"), "힌트");
  await click("힌트");
  await wait("typeof window.__releaseHelp === 'function'");
  assert.ok(await evaluate("[...document.querySelectorAll('.study-help-actions button')].every(button => button.disabled)"));
  await evaluate("document.querySelector('.study-help-actions button').click()");
  assert.equal(await evaluate("window.__calls.filter(call => call.path.endsWith('/messages')).length"), 1);
  assert.equal(await evaluate("document.querySelector('.chat-input-bar textarea').value"), "작성 중인 나의 설명입니다.");
  await evaluate("window.__delayHelp = false; window.__releaseHelp()");
  await wait("document.querySelector('.tutor-hint') && !document.querySelector('.study-help-actions button').disabled");
  assert.ok(await evaluate("!document.querySelector('.feedback-strip').textContent.includes('AI의 잠정 피드백') && !document.querySelector('.feedback-strip').textContent.includes('정답률이 아닙니다')"));
  assert.ok(await evaluate("document.querySelector('.feedback-strip').textContent.includes('도움 요청은 학습목표를 자동으로 체크하지 않아요.')"), "Keep the feedback itself while removing the disclaimer badge");
  assert.equal(await evaluate("window.__calls.find(call => call.path.endsWith('/messages')).body.help_action"), "hint");
  assert.equal(await evaluate("document.querySelector('.chat-input-bar textarea').value"), "작성 중인 나의 설명입니다.");
  assert.ok(await evaluate("document.querySelector('.learning-report-count').textContent.includes('2개 AI 확인')"));
  await screenshot("help-shortcuts-desktop", 1280, 1100, false, ".chat-input-bar");
  await screenshot("help-shortcuts-mobile-dark", 390, 1000, true, ".chat-input-bar");
  assert.ok(await evaluate("document.documentElement.scrollWidth <= innerWidth + 1"));
  await evaluate("window.__failHelp = true");
  await click("힌트");
  await wait("document.querySelector('.study-error')");
  assert.equal(await evaluate("document.querySelector('.chat-input-bar textarea').value"), "작성 중인 나의 설명입니다.");
  assert.equal(await evaluate("document.querySelectorAll('.message-row').length"), 5);
  await evaluate("window.__failHelp = false");
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
  const fillAnswer = async (value) => {
    await evaluate(`(() => { const input=document.querySelector('.chat-input-bar textarea'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(input,${JSON.stringify(value)}); input.dispatchEvent(new Event('input',{bubbles:true})); })()`);
    await wait("!document.querySelector('.send-btn').disabled");
    await evaluate("document.querySelector('.send-btn').click()");
  };
  await fillAnswer("확인된 내용을 설명했습니다.");
  await wait("document.querySelector('.learning-report-count').textContent.includes('4개 AI 확인')");
  assert.ok(await evaluate("document.querySelector('.learning-report-guidance').textContent.includes('마지막 정리')"));
  await evaluate("window.__failCompletion=true");
  await fillAnswer("오늘 배운 핵심을 정리합니다.");
  await wait("document.querySelector('.study-error')");
  assert.ok(await evaluate("!document.querySelector('.study-ending') && document.querySelector('.chat-input-bar textarea').value==='오늘 배운 핵심을 정리합니다.'"));
  await evaluate("window.__failCompletion=false");
  await fillAnswer("오늘 배운 핵심을 정리합니다.");
  await wait("document.querySelector('.study-ending')");
  assert.ok(await evaluate("document.querySelector('.study-ending').textContent.includes('5/5') && !document.querySelector('.chat-input-bar')"));
  assert.equal(await evaluate("window.__calls.filter(call=>call.path.endsWith('/finish')).length"),0,"Auto completion must not issue a second finish request");
  assert.ok(await evaluate("!localStorage.getItem('havruta_active_session')"));
  await screenshot("ending-desktop",1280,1100,false);
  await screenshot("ending-mobile-dark",390,1000,true);
  assert.ok(await evaluate("document.documentElement.scrollWidth<=innerWidth+1"));
  await click("복습 퀴즈 풀기");
  await wait("document.querySelector('[aria-label=\"퀴즈 과목\"]')");
  assert.equal(await evaluate("document.querySelector('[aria-label=\"퀴즈 과목\"]').value"),"사회");
  await wait("document.querySelector('[aria-label=\"단원\"]')");
  assert.equal(await evaluate("document.querySelector('[aria-label=\"단원\"]').value"),"10통사1-03");
  await click("혼자 학습하기");
  await wait("document.querySelector('.resume-session')");
  await evaluate("window.__completeOnResume=true");
  await click("이어서 학습");
  await wait("document.querySelector('.study-ending')");
  await click("정리노트 보기");
  await wait("document.querySelector('.note-paper')");
  assert.ok(await evaluate("Boolean(document.querySelector('.note-takeaway .katex'))"));
  await click("퀴즈");
  await wait("document.querySelector('.btn-quiz-start')");
  await click("풀기 ➔");
  await wait("document.querySelectorAll('.quiz-question-block').length === 2");
  assert.ok(await evaluate("Boolean(document.querySelector('.quiz-question-block h3 .katex')) && Boolean(document.querySelector('.quiz-option .katex'))"), "Quiz questions and choices render equations");
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
  await click("정리노트");
  await wait("document.querySelector('.note-open')");
  await evaluate("document.querySelector('.note-open').click()");
  await wait("document.querySelector('.note-takeaway .katex')");
  await screenshot("math-note-mobile", 390, 1000, false);
  assert.ok(await evaluate("document.documentElement.scrollWidth <= innerWidth + 1"));
  assert.deepEqual(exceptions, []);
  console.log(JSON.stringify({ status: "passed", mockedApi: true, noProductionWrites: true,
    checks: ["resume choice instead of auto-open", "saved transcript preview", "resume preserves 2/5", "pause saves without finishing", "restart begins at 0/5", "no early answer leak", "wrong-answer explanation", "wrong-only filter", "restore last answer without resubmitting", "retry clears previous choices", "pause error retains chat", "restart error retains progress", "submit error retains choices", "no mobile horizontal overflow", "hint shortcut", "help preserves draft", "help never auto-checks goals", "help buttons disable while pending", "no duplicate help request", "help error preserves draft and rolls back optimistic message", "single hint option"],
    mathChecks: ["six equations in AI chat", "student math", "four delimiters (SSR)", "math in learning report and note", "HTML inert", "KaTeX font loaded", "long equation scrolls without page overflow"],
    screenshots: output }, null, 2));
} finally {
  socket?.close(); chrome?.kill(); await vite.close();
}
