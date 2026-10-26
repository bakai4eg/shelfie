import type { ReactNode } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/features/auth/context";
import { ROLE_LEVEL } from "@/lib/constants";
import type { Role } from "@/lib/types";

function loginPath(pathname: string, search: string): string {
  return `/login?next=${encodeURIComponent(`${pathname}${search}`)}`;
}

function SessionLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-sm text-shelf-500" role="status">
      Проверяем сессию…
    </div>
  );
}

/** Закрытый маршрут: гостя отправляем на вход и запоминаем, куда он шёл. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <SessionLoading />;
  }
  if (status === "guest") {
    return <Navigate to={loginPath(location.pathname, location.search)} replace />;
  }
  return <>{children}</>;
}

/** Маршрут для модераторов и админов: роль сравниваем по уровням, как на бэкенде. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <SessionLoading />;
  }
  if (!user) {
    return <Navigate to={loginPath(location.pathname, location.search)} replace />;
  }
  if (ROLE_LEVEL[user.role] < ROLE_LEVEL[role]) {
    return (
      <section className="mx-auto max-w-2xl px-4 py-16">
        <h1 className="text-2xl font-semibold text-shelf-900">Недостаточно прав</h1>
        <p className="mt-2 text-shelf-700">
          Этот раздел доступен только пользователям с ролью «{role === "admin" ? "администратор" : "модератор"}».
        </p>
        <Link to="/" className="mt-6 inline-block font-medium text-accent-600 hover:text-accent-700">
          Вернуться на главную →
        </Link>
      </section>
    );
  }
  return <>{children}</>;
}
