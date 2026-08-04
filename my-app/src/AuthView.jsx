import { useState } from "react";
import { api, setToken } from "./api";
import "./AuthView.css";

export default function AuthView({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "", grade: "고등학교 1학년" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const normalized = {
        ...form,
        email: form.email.trim().toLowerCase(),
        name: form.name.trim(),
        grade: form.grade.trim() || null,
      };
      const payload = mode === "login"
        ? { email: normalized.email, password: normalized.password }
        : { ...normalized, role: "student" };
      const result = await api(`/auth/${mode === "login" ? "login" : "signup"}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setToken(result.access_token);
      onAuthenticated(result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand">AI Study</div>
        <h1>{mode === "login" ? "다시 만나서 반가워요" : "하브루타 학습 시작하기"}</h1>
        <p>AI와 질문하고 설명하며 수학 개념을 깊게 익혀보세요.</p>
        {mode === "signup" && (
          <>
            <input required autoComplete="name" placeholder="이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <input placeholder="학년" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
          </>
        )}
        <input required type="email" autoComplete="email" placeholder="이메일 (예: demo@havruta.com)" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input required minLength={8} type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="비밀번호 (8자 이상)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <div className="auth-error">{error}</div>}
        <button disabled={loading}>{loading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}</button>
        <button type="button" className="auth-switch" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
          {mode === "login" ? "계정이 없나요? 회원가입" : "이미 계정이 있나요? 로그인"}
        </button>
      </form>
    </main>
  );
}
