/**
 * Единственное место, где живёт токен.
 * Компоненты и страницы не читают localStorage напрямую — только через useAuth.
 */

const TOKEN_KEY = "shelfie.token";

export const tokenStore = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
  },
};

/** Событие «сервер ответил 401»: провайдер сессии реагирует и уводит на вход. */
export const UNAUTHORIZED_EVENT = "shelfie:unauthorized";

export function notifyUnauthorized(): void {
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

/** Возврат после входа: только внутренние пути, чтобы нельзя было увести на чужой сайт. */
export function safeNextPath(value: string | null, fallback = "/"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return fallback;
  }
  return value;
}
