import { Link } from "react-router-dom";

import { useAuth } from "@/features/auth/context";

interface GuestNoticeProps {
  /** Действие, для которого нужен вход: «добавить на полку», «поставить оценку». */
  action: string;
  /** Куда вернуть гостя после входа. По умолчанию — текущая страница. */
  next?: string;
}

/**
 * Гостю не показываем кнопки изменения данных, но объясняем, что они появятся
 * после входа (ТЗ 4.2.2). Авторизованному пользователю компонент не рисуется.
 */
export default function GuestNotice({ action, next }: GuestNoticeProps) {
  const { status } = useAuth();

  if (status !== "guest") {
    return null;
  }

  const target = next ?? (typeof window === "undefined" ? "/" : window.location.pathname);
  const loginTo = `/login?next=${encodeURIComponent(target)}`;

  return (
    <div className="rounded-xl border border-dashed border-shelf-300 bg-white/60 p-4 text-sm text-shelf-700">
      <Link to={loginTo} className="font-medium text-accent-600 hover:text-accent-700">
        Войдите
      </Link>{" "}
      или{" "}
      <Link
        to={`/register?next=${encodeURIComponent(target)}`}
        className="font-medium text-accent-600 hover:text-accent-700"
      >
        зарегистрируйтесь
      </Link>
      , чтобы {action}.
    </div>
  );
}
