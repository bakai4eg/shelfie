import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import Button from "@/components/ui/Button";
import { engagementApi } from "@/features/reviews/api";
import { buttonClass } from "@/lib/ui";
import type { FeedEvent, Page } from "@/lib/types";
import { formatDate } from "@/lib/utils";

const PAGE_SIZE = 20;

function EventText({ event }: { event: FeedEvent }) {
  const item = event.item ? (
    <Link to={`/catalog/${event.item.id}`} className="font-medium text-accent-700 hover:underline">
      {event.item.title}
    </Link>
  ) : null;

  switch (event.event_type) {
    case "review_created":
      return (
        <>
          написал(а) рецензию{" "}
          {event.review ? (
            <Link to={`/reviews/${event.review.id}`} className="font-medium text-accent-700 hover:underline">
              «{event.review.title}»
            </Link>
          ) : null}
          {item ? <> на {item}</> : null}
        </>
      );
    case "item_finished":
      return <>завершил(а) {item}</>;
    case "rating_set":
      return (
        <>
          оценил(а) {item} на <span className="font-semibold">{event.value} / 10</span>
        </>
      );
    case "list_published":
      return (
        <>
          опубликовал(а) список{" "}
          {event.list ? (
            <Link to={`/lists/${event.list.id}`} className="font-medium text-accent-700 hover:underline">
              «{event.list.title}»
            </Link>
          ) : null}
        </>
      );
  }
}

/** Лента подписок (ТЗ 4.5.4): события в порядке убывания времени, подгрузка по кнопке и при прокрутке. */
export default function FeedPage() {
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sentinel = useRef<HTMLDivElement | null>(null);

  const load = useCallback((nextPage: number, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    engagementApi
      .feed(nextPage, PAGE_SIZE, signal)
      .then((result: Page<FeedEvent>) => {
        setEvents((current) => (nextPage === 1 ? result.items : [...current, ...result.items]));
        setTotal(result.total);
        setPage(nextPage);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить ленту");
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(1, controller.signal);
    return () => controller.abort();
  }, [load]);

  const hasMore = events.length < total;

  useEffect(() => {
    const node = sentinel.current;
    if (!node || !hasMore || loading || error) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) load(page + 1);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loading, error, page, load]);

  return (
    <section className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-shelf-900">Лента</h1>
      <p className="mt-1 text-shelf-600">Новые рецензии, оценки и списки людей, на которых вы подписаны.</p>

      {error ? (
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-5 text-center" role="alert">
          <p className="text-sm text-red-800">{error}</p>
          <Button className="mt-3" onClick={() => load(page === 1 && events.length === 0 ? 1 : page + 1)}>
            Повторить
          </Button>
        </div>
      ) : null}

      {!error && !loading && events.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-10 text-center">
          <p className="text-lg font-medium text-shelf-900">Пока тихо</p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-shelf-600">
            Подпишитесь на других пользователей в их профиле, и их активность появится здесь. Начните
            с рецензий в каталоге.
          </p>
          <Link to="/catalog" className={buttonClass("primary", "mt-5")}>
            В каталог
          </Link>
        </div>
      ) : null}

      <ul className="mt-8 space-y-3">
        {events.map((event) => (
          <li key={event.id} className="flex gap-3 rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
            {event.item?.poster_url ? (
              <img src={event.item.poster_url} alt="" className="h-16 w-11 shrink-0 rounded-lg object-cover" />
            ) : null}
            <div className="min-w-0 text-sm text-shelf-800">
              <p className="break-words">
                <Link to={`/u/${event.user.login}`} className="font-semibold text-shelf-900 hover:underline">
                  @{event.user.login}
                </Link>{" "}
                <EventText event={event} />
              </p>
              <p className="mt-1 text-xs text-shelf-500">{formatDate(event.created_at)}</p>
            </div>
          </li>
        ))}
      </ul>

      {loading ? (
        <p className="mt-6 text-center text-sm text-shelf-500" role="status">
          Загружаем…
        </p>
      ) : null}
      {hasMore && !loading && !error ? (
        <div ref={sentinel} className="mt-6 text-center">
          <Button variant="secondary" onClick={() => load(page + 1)}>
            Показать ещё
          </Button>
        </div>
      ) : null}
    </section>
  );
}
