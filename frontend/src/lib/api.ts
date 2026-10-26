/** Базовый URL API. В dev по умолчанию идём через прокси Vite на /api. */
import { notifyUnauthorized, tokenStore } from "@/lib/auth";

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Публичные запросы не подставляют токен. */
  anonymous?: boolean;
  /** Для входа/регистрации: 401 — это ошибка формы, а не истёкшая сессия. */
  skipAuthRedirect?: boolean;
};

/** FastAPI отвечает `detail` строкой или списком ошибок валидации. */
function extractDetail(payload: unknown): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return "Что-то пошло не так";
  }

  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    return typeof first?.msg === "string" ? first.msg : "Проверьте введённые данные";
  }
  return "Что-то пошло не так";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, anonymous, skipAuthRedirect, headers, ...rest } = options;
  const token = anonymous ? null : tokenStore.get();

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    // 401 обрабатывается в AuthProvider: чистим токен и уводим на вход
    if (response.status === 401) {
      tokenStore.clear();
      if (!skipAuthRedirect) {
        notifyUnauthorized();
      }
    }
    throw new ApiError(response.status, extractDetail(payload));
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE", body }),
};
