import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { authApi } from "@/features/auth/api";
import { AuthContext, type AuthStatus } from "@/features/auth/context";
import { UNAUTHORIZED_EVENT, tokenStore } from "@/lib/auth";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "@/lib/types";

/**
 * Сессия на клиенте: токен лежит в localStorage, пользователь — в контексте.
 * При загрузке страницы токен проверяется через /auth/me, поэтому F5 не разлогинивает.
 */
export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!tokenStore.get()) {
      setStatus("guest");
      return;
    }

    let alive = true;
    authApi
      .me()
      .then((current) => {
        if (!alive) return;
        setUser(current);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!alive) return;
        tokenStore.clear();
        setUser(null);
        setStatus("guest");
      });

    return () => {
      alive = false;
    };
  }, []);

  // Глобальный 401: токен уже очищен в api.ts, здесь сбрасываем состояние и уводим на вход
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setStatus("guest");
      if (location.pathname === "/login" || location.pathname === "/register") {
        return;
      }
      const next = encodeURIComponent(`${location.pathname}${location.search}`);
      navigate(`/login?next=${next}`, { replace: true, state: { expired: true } });
    };

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [location.pathname, location.search, navigate]);

  const saveSession = useCallback((response: AuthResponse): User => {
    tokenStore.set(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
    return response.user;
  }, []);

  const login = useCallback(
    async (payload: LoginPayload) => saveSession(await authApi.login(payload)),
    [saveSession],
  );

  const register = useCallback(
    async (payload: RegisterPayload) => saveSession(await authApi.register(payload)),
    [saveSession],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Сессия могла истечь или быть отозвана — выходим в любом случае
    } finally {
      tokenStore.clear();
      setUser(null);
      setStatus("guest");
      navigate("/", { replace: true });
    }
  }, [navigate]);

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
