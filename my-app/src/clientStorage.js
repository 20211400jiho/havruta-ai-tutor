const memoryValues = new Map();

export const TOKEN_KEY = "havruta_token";
export const THEME_KEY = "havruta_theme";

function browserStorage() {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getClientValue(key) {
  try {
    const value = browserStorage()?.getItem(key) ?? null;
    if (value !== null) memoryValues.set(key, value);
    return value ?? memoryValues.get(key) ?? null;
  } catch {
    return memoryValues.get(key) ?? null;
  }
}

export function setClientValue(key, value) {
  memoryValues.set(key, value);
  try {
    browserStorage()?.setItem(key, value);
  } catch {
    // 브라우저가 사이트 저장을 차단해도 현재 탭에서는 메모리 값을 사용한다.
  }
}

export function removeClientValue(key) {
  memoryValues.delete(key);
  try {
    browserStorage()?.removeItem(key);
  } catch {
    // 저장소가 차단된 환경에서도 로그아웃 흐름은 계속 진행한다.
  }
}

export function clearHavrutaClientState() {
  removeClientValue(TOKEN_KEY);
  removeClientValue(THEME_KEY);
}
