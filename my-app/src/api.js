import { getClientValue, removeClientValue, setClientValue, TOKEN_KEY } from "./clientStorage";

export const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function getToken() {
  return getClientValue(TOKEN_KEY);
}

export function setToken(token) {
  if (token) setClientValue(TOKEN_KEY, token);
  else removeClientValue(TOKEN_KEY);
}

export function getWebSocketUrl(roomId) {
  const configuredUrl = import.meta.env.VITE_WS_URL?.replace(/\/$/, "");
  const baseUrl = configuredUrl || API_URL.replace(/^http/, "ws");
  return `${baseUrl}/chat/ws/${roomId}`;
}

export async function api(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) {
      const message = detail.map((item) => {
        const field = item.loc?.at(-1);
        const labels = { email: "이메일", password: "비밀번호", name: "이름", grade: "학년" };
        return `${labels[field] || field || "입력값"}: ${item.msg}`;
      }).join("\n");
      throw new Error(message);
    }
    throw new Error(typeof detail === "string" ? detail : "요청을 처리하지 못했습니다.");
  }
  return data;
}
