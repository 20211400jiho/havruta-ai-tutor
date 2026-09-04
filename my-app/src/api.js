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
  const controller = options.signal ? null : new AbortController();
  const timeoutId = controller ? window.setTimeout(() => controller.abort(), 70000) : null;
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: options.signal || controller?.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    if (error?.name === "AbortError") throw new Error("서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.", { cause: error });
    throw new Error("서버에 연결하지 못했습니다. 네트워크와 배포 상태를 확인해주세요.", { cause: error });
  } finally {
    if (timeoutId) window.clearTimeout(timeoutId);
  }
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
    const statusMessage = response.status >= 500 ? "서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요." : "요청을 처리하지 못했습니다.";
    throw new Error(typeof detail === "string" ? detail : statusMessage);
  }
  return data;
}
