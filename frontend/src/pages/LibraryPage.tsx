import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Button from "@/components/ui/Button";
import { libraryApi, type LibraryQuery } from "@/features/library/api";
import { ITEM_TYPE_LABELS, SHELF_STATUS_LABELS } from "@/lib/constants";
import type { ItemType, ShelfEntry, ShelfStatus } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { cn, formatDate } from "@/lib/utils";

const STATUS_TABS: Array<{ key: ShelfStatus | "all"; label: string }> = [
  { key: "all", label: "Все" },
  { key: "watching", label: SHELF_STATUS_LABELS.watching },
  { key: "finished", label: SHELF_STATUS_LABELS.finished },
  { key: "planned", label: SHELF_STATUS_LABELS.planned },
  { key: "dropped", label: SHELF_STATUS_LABELS.dropped },
];

const ITEM_TYPES: Array<{ key: ItemType | "all"; label: string }> = [
  { key: "all", label: "Все типы" },
  { key: "book", label: "Книги" },
  { key: "movie", label: "Фильмы" },
  { key: "series", label: "Сериалы" },
];

const SORTS = [
  { key: "added_desc", label: "Сначала добавленные" },
  { key: "rating_desc", label: "По личной оценке" },
  { key: "title_asc", label: "По названию" },
] as const;

export default function LibraryPage() {
  const [selectedStatus, setSelectedStatus] = useState<ShelfStatus | "all">("all");
  const [selectedType, setSelectedType] = useState<ItemType | "all">("all");
  const [selectedSort, setSelectedSort] = useState<"added_desc" | "rating_desc" | "title_asc">("added_desc");

  const [entries, setEntries] = useState<ShelfEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const query: LibraryQuery = {
      status: selectedStatus === "all" ? undefined : selectedStatus,
      type: selectedType === "all" ? undefined : selectedType,
      sort: selectedSort,
    };

    libraryApi
      .list(query, controller.signal)
      .then(setEntries)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить полку");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [selectedStatus, selectedType, selectedSort, reloadKey]);

  const handleStatusChange = async (itemId: number, newStatus: ShelfStatus) => {
    try {
      const today = new Date().toISOString().slice(0, 10);
      await libraryApi.upsertShelf(itemId, {
        status: newStatus,
        finished_at: newStatus === "finished" ? today : null,
      });
      setReloadKey((k) => k + 1);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось обновить статус");
    }
  };

  const handleRemove = async (itemId: number) => {
    if (!window.confirm("Убрать произведение с полки?")) return;
    try {
      await libraryApi.deleteShelf(itemId);
      setEntries((prev) => prev.filter((e) => e.item_id !== itemId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось убрать с полки");
    }
  };

  return (
    <section className="mx-auto max-w-6xl px-4 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-shelf-900">Мои полки</h1>
          <p className="mt-1 text-shelf-600">
            Здесь собраны книги, фильмы и сериалы, которые вы читаете, смотрите и планируете.
          </p>
        </div>
        {!loading && (
          <p className="text-sm text-shelf-500">
            {entries.length}{" "}
            {entries.length === 1
              ? "произведение"
              : entries.length >= 2 && entries.length <= 4
              ? "произведения"
              : "произведений"}
          </p>
        )}
      </header>

      {/* Табы по статусу полок */}
      <div className="mt-8 flex flex-wrap gap-2 border-b border-shelf-200 pb-4">
        {STATUS_TABS.map((tab) => {
          const active = selectedStatus === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setSelectedStatus(tab.key)}
              className={cn(
                "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent-600 text-white shadow-sm"
                  : "bg-white text-shelf-700 ring-1 ring-shelf-200 hover:bg-shelf-100",
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Панель фильтров: тип и сортировка */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-shelf-700">
            <span className="font-medium text-shelf-900">Тип:</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as ItemType | "all")}
              className="rounded-xl border border-shelf-300 bg-white px-3 py-1.5 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
            >
              {ITEM_TYPES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm text-shelf-700">
          <span className="font-medium text-shelf-900">Сортировка:</span>
          <select
            value={selectedSort}
            onChange={(e) =>
              setSelectedSort(e.target.value as "added_desc" | "rating_desc" | "title_asc")
            }
            className="rounded-xl border border-shelf-300 bg-white px-3 py-1.5 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
          >
            {SORTS.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-medium text-red-800">Ошибка загрузки полок</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
          <Button className="mt-4" onClick={() => setReloadKey((k) => k + 1)}>
            Повторить
          </Button>
        </div>
      )}

      {/* Загрузка */}
      {loading && !error && (
        <div className="mt-12 text-center text-sm text-shelf-500">Загрузка полок...</div>
      )}

      {/* Пустое состояние */}
      {!loading && !error && entries.length === 0 && (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-12 text-center">
          <p className="text-lg font-medium text-shelf-900">На этой полке пока ничего нет</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-shelf-600">
            Перейдите в каталог, чтобы добавить книги, фильмы и сериалы.
          </p>
          <Link to="/catalog" className={buttonClass("primary", "mt-6")}>
            В каталог
          </Link>
        </div>
      )}

      {/* Сетка карточек */}
      {!loading && !error && entries.length > 0 && (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {entries.map((entry) => {
            const item = entry.item;
            const meta = [item.year, ITEM_TYPE_LABELS[item.type], item.country]
              .filter(Boolean)
              .join(" · ");

            return (
              <div
                key={entry.id}
                className="flex flex-col justify-between overflow-hidden rounded-2xl bg-white p-4 ring-1 ring-shelf-200"
              >
                <div className="flex gap-4">
                  <Link
                    to={`/catalog/${item.id}`}
                    className="relative aspect-[2/3] w-24 flex-shrink-0 overflow-hidden rounded-xl bg-shelf-100 ring-1 ring-shelf-200"
                  >
                    {item.poster_url ? (
                      <img
                        src={item.poster_url}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center p-2 text-center text-xs text-shelf-400">
                        {ITEM_TYPE_LABELS[item.type]}
                      </div>
                    )}
                  </Link>

                  <div className="flex flex-1 flex-col justify-between py-0.5">
                    <div>
                      <Link
                        to={`/catalog/${item.id}`}
                        className="line-clamp-2 text-base font-semibold text-shelf-900 hover:text-accent-600"
                      >
                        {item.title}
                      </Link>
                      <p className="mt-1 text-xs text-shelf-500">{meta}</p>
                    </div>

                    <div className="mt-3">
                      {entry.user_rating !== null ? (
                        <p className="text-xs font-semibold text-accent-700">
                          ★ Ваша оценка: {entry.user_rating}/10
                        </p>
                      ) : (
                        <p className="text-xs text-shelf-400">Без личной оценки</p>
                      )}
                      {entry.finished_at && (
                        <p className="mt-0.5 text-xs text-shelf-500">
                          Завершено: {formatDate(entry.finished_at)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-shelf-100 pt-3">
                  <select
                    value={entry.status}
                    onChange={(e) => handleStatusChange(item.id, e.target.value as ShelfStatus)}
                    aria-label="Статус на полке"
                    className="rounded-lg border border-shelf-300 bg-shelf-50 px-2.5 py-1 text-xs font-medium text-shelf-800 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                  >
                    {(Object.keys(SHELF_STATUS_LABELS) as ShelfStatus[]).map((status) => (
                      <option key={status} value={status}>
                        {SHELF_STATUS_LABELS[status]}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => handleRemove(item.id)}
                    className="text-xs font-medium text-red-600 hover:underline"
                  >
                    Убрать
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
