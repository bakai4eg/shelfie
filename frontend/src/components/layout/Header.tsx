import { Link, NavLink } from "react-router-dom";

import { useAuth } from "@/features/auth/context";
import { ROLE_LEVEL } from "@/lib/constants";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/catalog", label: "Каталог" },
  { to: "/my/library", label: "Мои полки" },
  { to: "/feed", label: "Лента" },
];

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="Shelfie — на главную">
      <svg viewBox="0 0 64 64" className="h-8 w-8" aria-hidden>
        <rect width="64" height="64" rx="14" fill="currentColor" className="text-shelf-900" />
        <rect x="14" y="16" width="8" height="32" rx="2" fill="#e4d8c6" />
        <rect x="26" y="20" width="8" height="28" rx="2" fill="#bfa07c" />
        <rect x="38" y="18" width="8" height="30" rx="2" fill="#f2ece2" />
        <rect x="12" y="48" width="40" height="4" rx="2" fill="#c2410c" />
      </svg>
      <span className="text-lg font-semibold tracking-tight">Shelfie</span>
    </Link>
  );
}

export default function Header() {
  const { user, status, logout } = useAuth();

  const links = [...NAV];
  if (user && ROLE_LEVEL[user.role] >= ROLE_LEVEL.moderator) {
    links.push({ to: "/moderation", label: "Модерация" });
  }
  if (user?.role === "admin") {
    links.push({ to: "/admin", label: "Админка" });
  }

  return (
    <header className="sticky top-0 z-10 border-b border-shelf-200 bg-shelf-50/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Logo />

        <nav className="hidden items-center gap-1 sm:flex">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-lg px-3 py-1.5 text-sm transition-colors",
                  isActive ? "bg-shelf-200 font-medium text-shelf-900" : "text-shelf-700 hover:bg-shelf-100",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {status === "loading" ? (
            <span className="h-8 w-24 animate-pulse rounded-lg bg-shelf-200" aria-hidden />
          ) : user ? (
            <>
              <Link
                to={`/u/${user.login}`}
                className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium text-shelf-900 hover:bg-shelf-100"
                title="Мой профиль"
              >
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={`Аватар @${user.login}`}
                    className="h-7 w-7 rounded-full object-cover ring-1 ring-shelf-300"
                  />
                ) : (
                  <span
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-600 text-xs font-semibold text-white"
                    aria-hidden
                  >
                    {user.login.slice(0, 1).toUpperCase()}
                  </span>
                )}
                <span>{user.login}</span>
              </Link>
              <button
                type="button"
                onClick={() => void logout()}
                className="rounded-xl px-3.5 py-1.5 text-sm text-shelf-700 transition-colors hover:bg-shelf-100"
              >
                Выйти
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-3 py-1.5 text-sm text-shelf-700 hover:bg-shelf-100">
                Войти
              </Link>
              <Link
                to="/register"
                className="rounded-xl bg-shelf-900 px-3.5 py-1.5 text-sm font-medium text-shelf-50 transition-colors hover:bg-shelf-800"
              >
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
