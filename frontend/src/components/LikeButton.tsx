import { useState } from "react";
import { Link } from "react-router-dom";

import { engagementApi } from "@/features/reviews/api";
import { useAuth } from "@/features/auth/context";
import { cn } from "@/lib/utils";

/**
 * Кнопка лайка с оптимистичным обновлением (ТЗ 4.5.3): счётчик меняется сразу,
 * а при ошибке сервера возвращается прежнее значение.
 */
export default function LikeButton({
  targetType,
  targetId,
  count,
  liked,
}: {
  targetType: "review" | "comment";
  targetId: number;
  count: number;
  liked: boolean;
}) {
  const { user } = useAuth();
  const [state, setState] = useState({ count, liked });
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!user) {
    return (
      <Link
        to="/login"
        title="Войдите, чтобы поставить лайк"
        className="inline-flex items-center gap-1 text-sm text-shelf-500 hover:text-accent-700"
      >
        <span aria-hidden>♡</span> {state.count}
      </Link>
    );
  }

  async function toggle() {
    if (busy) return;
    const before = state;
    setBusy(true);
    setFailed(false);
    setState({ count: before.count + (before.liked ? -1 : 1), liked: !before.liked });
    try {
      const result = before.liked
        ? await engagementApi.unlike(targetType, targetId)
        : await engagementApi.like(targetType, targetId);
      setState({ count: result.likes_count, liked: result.liked_by_me });
    } catch {
      setState(before);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={() => void toggle()}
      aria-pressed={state.liked}
      aria-label={state.liked ? "Убрать лайк" : "Поставить лайк"}
      className={cn(
        "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm transition-colors",
        state.liked ? "bg-accent-600/10 font-medium text-accent-700" : "text-shelf-600 hover:bg-shelf-100",
      )}
    >
      <span aria-hidden>{state.liked ? "♥" : "♡"}</span>
      {state.count}
      {failed ? <span className="ml-1 text-xs text-red-600">не вышло</span> : null}
    </button>
  );
}
