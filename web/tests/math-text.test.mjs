import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let vite, MathText, LearningReport;
before(async () => {
  vite = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: "custom" });
  MathText = (await vite.ssrLoadModule("/src/MathText.jsx")).default;
  LearningReport = (await vite.ssrLoadModule("/src/LearningReport.jsx")).default;
});
after(async () => { await vite?.close(); });
const render = (text) => renderToStaticMarkup(React.createElement(MathText, { text }));

for (const equation of ["y=ax", String.raw`a\neq0`, "y=-3x", String.raw`\frac{y}{x}=a`, "x^2+2x+1", "2x-3=7"]) {
  test(`renders math after a JSON round trip: ${equation}`, () => {
    const text = `한글 English $${equation}$ 다음 문장`;
    const decoded = JSON.parse(JSON.stringify({ content: text })).content;
    assert.equal(decoded, text);
    const html = render(decoded);
    assert.ok(html.includes('class="katex"'));
    assert.ok(html.includes(equation)); // TeX source retained in accessible MathML annotation.
    assert.ok(!html.includes('class="katex-error"'));
    assert.ok(html.includes("한글 English") && html.includes("다음 문장"));
  });
}
for (const text of ["$y=ax$", "$$y=ax$$", "$$\ny=ax\n$$", String.raw`\(y=ax\)`, String.raw`\[y=ax\]`]) {
  test(`supports delimiter ${JSON.stringify(text)}`, () => {
    assert.ok(render(text).includes('class="katex"'));
  });
}
test("preserves prose, Markdown, code, newlines and escaped dollars", () => {
  for (const text of ["한글 English\n두 번째 줄\n\n마지막", "**강조 아님** # 제목", "`$y=ax$`", "```tex\n$y=ax$\n```", String.raw`가격 \$10, 경로 C:\temp`, "$미완성", String.raw`\(미완성`]) {
    const html = render(text);
    assert.ok(!html.includes('class="katex"'));
    assert.ok(html.includes(text));
  }
});
test("raw HTML and dangerous URLs never become active elements", () => {
  const html = render('<script>alert(1)</script><img src=x onerror=alert(1)> [실행](javascript:alert(1))');
  assert.ok(!html.includes("<script") && !html.includes("<img") && !html.includes("<a "));
  assert.ok(html.includes("&lt;script&gt;"));
  const math = render(String.raw`$\href{javascript:alert(1)}{위험}$`);
  assert.ok(!math.includes('href="javascript:'));
});
test("invalid TeX does not crash the message", () => {
  const html = render(String.raw`앞 $\notARealCommand{x}$ 뒤`);
  assert.ok(html.includes("앞") && html.includes("뒤"));
});
test("learning report renders equations without changing confirmed goal count", () => {
  const report = { objectives: [{ stage: "개념 설명", status: "ai_checked", evidence_quote: "$y=ax$" }], first_explanation: "$y=-3x$", latest_explanation: String.raw`$\frac{y}{x}=a$`, has_comparison: true };
  const html = renderToStaticMarkup(React.createElement(LearningReport, { report, finished: true }));
  assert.equal((html.match(/class="katex"/g) || []).length, 3);
  assert.ok(html.includes("1개 AI 확인"));
});
