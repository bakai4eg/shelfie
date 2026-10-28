import { createContext, useContext } from "react";

import type { LoginPayload, RegisterPayload, User } from "@/lib/types";

export type AuthStatus = "loading" | "authenticated" | "guest";

export interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  clearSession: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

/** Хук вместо прямых обращений к токену: остальной код не знает, как устроена сессия. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth вызван вне AuthProvider");
  }
  return value;
}
