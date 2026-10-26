import { api } from "@/lib/api";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "@/lib/types";

/**
 * Запросы аутентификации. Вход и регистрация анонимны: старый токен не отправляем,
 * а 401 здесь — ошибка формы, а не истёкшая сессия, поэтому без глобального редиректа.
 */
export const authApi = {
  register: (payload: RegisterPayload) =>
    api.post<AuthResponse>("/auth/register", payload, {
      anonymous: true,
      skipAuthRedirect: true,
    }),

  login: (payload: LoginPayload) =>
    api.post<AuthResponse>("/auth/login", payload, {
      anonymous: true,
      skipAuthRedirect: true,
    }),

  logout: () => api.post<void>("/auth/logout", undefined, { skipAuthRedirect: true }),

  me: () => api.get<User>("/auth/me", { skipAuthRedirect: true }),
};
