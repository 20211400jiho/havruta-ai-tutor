import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import "./MathText.css";

const remarkPlugins = [remarkMath];
const rehypePlugins = [[rehypeKatex, { trust: false, throwOnError: false, maxExpand: 200, maxSize: 20 }]];

const escaped = (text, index) => {
  let count = 0;
  while (index > 0 && text[--index] === "\\") count++;
  return count % 2 === 1;
};

// Parse delimiters only for display. Keep source text, backslashes, HTML and
// Markdown outside math untouched; code examples must not become equations.
function splitMath(text) {
  const parts = [];
  let start = 0;
  for (let i = 0; i < text.length;) {
    if (text[i] === "`" && !escaped(text, i)) {
      const run = text.slice(i).match(/^`+/)[0];
      const end = text.indexOf(run, i + run.length);
      i = end < 0 ? text.length : end + run.length;
      continue;
    }
    if (escaped(text, i)) { i++; continue; }
    const open = text.startsWith("$$", i) ? "$$"
      : text.startsWith("\\[", i) ? "\\["
        : text.startsWith("\\(", i) ? "\\("
          : text[i] === "$" ? "$" : null;
    if (!open) { i++; continue; }
    const close = open === "\\[" ? "\\]" : open === "\\(" ? "\\)" : open;
    let end = text.indexOf(close, i + open.length);
    while (end >= 0 && (escaped(text, end) || (open === "$" && (text[end + 1] === "$" || text[end - 1] === "$")))) {
      end = text.indexOf(close, end + close.length);
    }
    const value = end < 0 ? "" : text.slice(i + open.length, end);
    if (!value.trim() || (open === "$" && /\n/.test(value))) { i += open.length; continue; }
    if (i > start) parts.push({ text: text.slice(start, i) });
    parts.push({ math: value, display: open === "$$" || open === "\\[", raw: text.slice(i, end + close.length) });
    i = end + close.length;
    start = i;
  }
  if (start < text.length) parts.push({ text: text.slice(start) });
  return parts;
}

export default function MathText({ text, className = "" }) {
  const value = typeof text === "string" ? text : "메시지를 표시할 수 없습니다.";
  return <span className={`math-text ${className}`.trim()}>{splitMath(value).map((part, index) => {
    if (part.text !== undefined) return <span key={index}>{part.text}</span>;
    // Only the extracted equation is parsed as Markdown, never user prose/HTML.
    const markdown = part.display ? `$$\n${part.math}\n$$` : `$${part.math}$`;
    return <span key={index} className={part.display ? "math-text-display" : "math-text-inline"}>
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}
        skipHtml components={{ p: ({ children }) => <span>{children}</span> }}>{markdown}</ReactMarkdown>
    </span>;
  })}</span>;
}
