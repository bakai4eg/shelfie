import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Button from "@/components/ui/Button";
import { localCardsApi } from "@/features/localCards/api";
import { ITEM_TYPE_LABELS } from "@/lib/constants";
import type { LocalCard, ModerationStatus, Page } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 12;

const STATUS_META: Record<
  ModerationStatus,
  { label: string; className: string }
> = {
  pending: {
    label: "На проверке",
    className: "bg-amber-50 text-amber-800 ring-amber-200",
  },
  approved: {
    label: "Одобрена",
    className: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  },
  hidden: {
    label: "Скрыта модератором",
    className: "bg-red-50 text-red-800 ring-red-200",
  },
};

export default function MyCardsPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<LocalCard> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    localCardsApi
      .mine(page, PAGE_SIZE, controller.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить карточки");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [page, reloadKey]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-shelf-900">Мои карточки</h1>
          <p className="mt-1 max-w-xl text-shelf-600">
            Кыргызские фильмы и книги, которых нет в международных каталогах.
            После проверки модератором они появятся в общем каталоге.
          </p>
        </div>
        <Link to="/cards/new" className={buttonClass("primary")}>
          + Добавить карточку
        </Link>
      </header>

      {error && (
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-medium text-red-800">Ошибка загрузки</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
          <Button className="mt-4" onClick={() => setReloadKey((key) => key + 1)}>
            Повторить
          </Button>
        </div>
      )}

      {loading && !error && (
        <p className="mt-12 text-center text-sm text-shelf-500">Загрузка карточек...</p>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-10 text-center sm:p-12">
          <p className="text-lg font-medium text-shelf-900">Пока нет своих карточек</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-shelf-600">
            Добавьте фильм или книгу, которой ещё нет в каталоге. Мы покажем её
            модератору, а вы сможете поправить данные, пока идёт проверка.
          </p>
          <Link to="/cards/new" className={buttonClass("primary", "mt-6")}>
            Создать карточку
          </Link>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="mt-8 space-y-4">
          {items.map((card) => {
            const meta = [card.year, ITEM_TYPE_LABELS[card.type], card.country]
              .filter(Boolean)
              .join(" · ");
            const status = STATUS_META[card.moderation_status];

            return (
              <article
                key={card.id}
                className="flex flex-col gap-4 rounded-2xl bg-white p-4 ring-1 ring-shelf-200 sm:flex-row"
              >
                <Link
                  to={`/catalog/${card.id}`}
                  className="relative aspect-[2/3] w-20 flex-shrink-0 overflow-hidden rounded-xl bg-shelf-100 ring-1 ring-shelf-200 sm:w-24"
                >
                  {card.poster_url ? (
                    <img
                      src={card.poster_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="flex h-full items-center justify-center p-2 text-center text-xs text-shelf-400">
                      {ITEM_TYPE_LABELS[card.type]}
                    </span>
                  )}
                </Link>

                <div className="flex min-w-0 flex-1 flex-col justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <Link
                          to={`/catalog/${card.id}`}
                          className="line-clamp-2 text-base font-semibold text-shelf-900 hover:text-accent-600"
                        >
                          {card.title}
                        </Link>
                        {card.original_title && (
                          <p className="mt-0.5 line-clamp-1 text-xs italic text-shelf-500">
                            {card.original_title}
                          </p>
                        )}
                      </div>
                      <span
                        className={cn(
                          "inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1",
                          status.className,
                        )}
                      >
                        {status.label}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-shelf-500">{meta}</p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Link
                      to={`/catalog/${card.id}`}
                      className={buttonClass("secondary", "px-3 py-1.5 text-xs")}
                    >
                      Открыть
                    </Link>
                    {card.moderation_status === "pending" && (
                      <Link
                        to={`/cards/${card.id}/edit`}
                        className={buttonClass("ghost", "px-3 py-1.5 text-xs")}
                      >
                        Исправить
                      </Link>
                    )}
                  </div>
                </div>
              </article>
            );
          })}

          {lastPage > 1 && (
            <div className="flex items-center justify-between gap-3 pt-2">
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Назад
              </Button>
              <span className="text-sm text-shelf-500">
                Страница {page} из {lastPage}
              </span>
              <Button
                variant="secondary"
                disabled={page >= lastPage}
                onClick={() => setPage((value) => Math.min(lastPage, value + 1))}
              >
                Вперёд
              </Button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
