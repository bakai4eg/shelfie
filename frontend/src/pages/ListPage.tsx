import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listsApi } from "@/features/lists/api";
import { LIST_THEMES } from "@/features/lists/themes";
import { ApiError } from "@/lib/api";
import { ITEM_TYPE_LABELS } from "@/lib/constants";
import type { ListDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Публичная витрина списка: открывается по постоянной ссылке без входа. */
export default function ListPage() {
  const { listId } = useParams();
  const id = Number(listId);
  const [list, setList] = useState<ListDetail | null>(null);
  const [error, setError] = useState<"notfound" | "other" | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) {
      setError("notfound");
      return;
    }
    const controller = new AbortController();
    setList(null);
    setError(null);
    listsApi
      .publicList(id, controller.signal)
      .then(setList)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof ApiError && err.status === 404 ? "notfound" : "other");
      });
    return () => controller.abort();
  }, [id]);

  async function share() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/lists/${id}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Скопируйте ссылку", `${window.location.origin}/lists/${id}`);
    }
  }

  if (error) {
    return (
      <section className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-2xl font-semibold text-shelf-900">
          {error === "notfound" ? "Подборка не найдена" : "Не удалось загрузить подборку"}
        </h1>
        <p className="mt-2 text-shelf-700">
          {error === "notfound"
            ? "Её могли удалить или закрыть для просмотра."
            : "Проверьте соединение и попробуйте ещё раз."}
        </p>
        <Link to="/catalog" className="mt-6 inline-block font-medium text-accent-600">
          В каталог →
        </Link>
      </section>
    );
  }

  if (!list) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-sm text-shelf-500" role="status">
        Загружаем подборку…
      </div>
    );
  }

  const theme = LIST_THEMES[list.theme];

  return (
    <div className={cn("min-h-[70vh]", theme.page)} data-theme={list.theme}>
      <section className="mx-auto max-w-3xl px-4 py-10">
        <header>
          <h1 className={theme.title}>{list.title}</h1>
          {list.description ? <p className={cn("mt-3 text-base", theme.lead)}>{list.description}</p> : null}
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <Link to={`/u/${list.owner.login}`} className="flex items-center gap-2 font-medium hover:underline">
              {list.owner.avatar_url ? (
                <img src={list.owner.avatar_url} alt="" className="h-7 w-7 rounded-full object-cover" />
              ) : (
                <span
                  className={cn("flex h-7 w-7 items-center justify-center text-xs font-semibold", theme.index)}
                  aria-hidden
                >
                  {list.owner.login.slice(0, 1).toUpperCase()}
                </span>
              )}
              @{list.owner.login}
            </Link>
            <span className={theme.meta}>Карточек: {list.items_count}</span>
            <button
              type="button"
              onClick={() => void share()}
              className={cn("ml-auto rounded-full px-3.5 py-1.5 text-sm font-medium", theme.chip)}
            >
              {copied ? "Ссылка скопирована ✓" : "Поделиться"}
            </button>
          </div>
        </header>

        {list.items.length === 0 ? (
          <p className={cn("mt-10", theme.meta)}>В подборке пока нет карточек.</p>
        ) : (
          <ol className="mt-8 space-y-4">
            {list.items.map((entry, index) => (
              <li key={entry.item.id} className={cn("flex gap-4 p-3 sm:p-4", theme.card)}>
                <Link to={`/catalog/${entry.item.id}`} className="shrink-0">
                  {entry.item.poster_url ? (
                    <img
                      src={entry.item.poster_url}
                      alt={`Обложка: ${entry.item.title}`}
                      className="h-28 w-20 rounded-lg object-cover sm:h-36 sm:w-24"
                      loading="lazy"
                    />
                  ) : (
                    <span
                      className={cn(
                        "flex h-28 w-20 items-center justify-center text-xs sm:h-36 sm:w-24",
                        theme.chip,
                      )}
                    >
                      Нет обложки
                    </span>
                  )}
                </Link>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2">
                    <span
                      className={cn(
                        "flex h-6 min-w-6 shrink-0 items-center justify-center px-1 text-xs font-semibold",
                        theme.index,
                      )}
                      aria-label={`Позиция ${index + 1}`}
                    >
                      {index + 1}
                    </span>
                    <Link
                      to={`/catalog/${entry.item.id}`}
                      className={cn("break-words text-lg leading-snug hover:underline", theme.cardTitle)}
                    >
                      {entry.item.title}
                    </Link>
                  </div>
                  <p className={cn("mt-1 text-xs", theme.meta)}>
                    {ITEM_TYPE_LABELS[entry.item.type]}
                    {entry.item.year ? ` · ${entry.item.year}` : ""}
                    {entry.item.rating_avg > 0 ? ` · ★ ${entry.item.rating_avg.toFixed(1)}` : ""}
                  </p>
                  {entry.note ? (
                    <p className={cn("mt-3 whitespace-pre-line break-words px-3 py-2 text-sm", theme.note)}>
                      {entry.note}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
