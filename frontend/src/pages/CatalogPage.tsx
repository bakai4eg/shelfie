import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import {
  CATALOG_PAGE_SIZE,
  fetchCatalog,
  fetchCatalogFilters,
  type CatalogQuery,
} from "@/features/catalog/api";
import { ITEM_TYPE_LABELS } from "@/lib/constants";
import type {
  CatalogFilters,
  CatalogItem,
  CatalogSort,
  ItemSource,
  Page,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const ITEM_TYPES = ["book", "movie", "series"] as const;
const ITEM_SOURCES = ["local", "tmdb", "openlibrary", "google_books"] as const;
const SORTS = ["relevance", "year_desc", "rating_desc", "title_asc"] as const;

const SORT_LABELS: Record<CatalogSort, string> = {
  relevance: "По релевантности",
  year_desc: "Сначала новые",
  rating_desc: "По рейтингу",
  title_asc: "По названию",
};

const SOURCE_LABELS: Record<ItemSource, string> = {
  local: "Локальная карточка",
  tmdb: "TMDB",
  openlibrary: "Open Library",
  google_books: "Google Books",
};

const CONTROL_CLASS =
  "w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 " +
  "focus:border-accent-600 focus:outline-2 focus:outline-offset-2 focus:outline-accent-600";

function pick<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : undefined;
}

function positiveInt(value: string | null): number | undefined {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : undefined;
}

function readQuery(params: URLSearchParams): CatalogQuery {
  return {
    q: params.get("q")?.trim() || undefined,
    type: pick(params.get("type"), ITEM_TYPES),
    year_from: positiveInt(params.get("year_from")),
    year_to: positiveInt(params.get("year_to")),
    genre: params.get("genre") || undefined,
    country: params.get("country") || undefined,
    source: pick(params.get("source"), ITEM_SOURCES),
    local_only: params.get("local_only") === "1",
    sort: pick(params.get("sort"), SORTS) ?? "relevance",
    page: positiveInt(params.get("page")) ?? 1,
    size: CATALOG_PAGE_SIZE,
  };
}

function CatalogCard({ item }: { item: CatalogItem }) {
  const meta = [item.year, ITEM_TYPE_LABELS[item.type], item.country].filter(Boolean).join(" · ");

  return (
    <Link
      to={`/catalog/${item.id}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-white ring-1 ring-shelf-200 transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
    >
      <div className="relative aspect-[2/3] overflow-hidden bg-shelf-100">
        {item.poster_url ? (
          <img
            src={item.poster_url}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-4 text-center text-sm font-medium text-shelf-500">
            {ITEM_TYPE_LABELS[item.type]}
          </div>
        )}
        {item.is_local && (
          <span className="absolute left-2 top-2 rounded-full bg-accent-600 px-2 py-0.5 text-xs font-medium text-white">
            Кыргызстан
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4">
        <h3 className="line-clamp-2 font-semibold text-shelf-900 group-hover:text-accent-700">
          {item.title}
        </h3>
        <p className="text-sm text-shelf-600">{meta}</p>
        {item.ratings_count > 0 && (
          <p className="mt-auto text-sm text-shelf-700">
            <span className="text-accent-600">★</span> {item.rating_avg.toFixed(1)}
            <span className="text-shelf-500"> ({item.ratings_count})</span>
          </p>
        )}
      </div>
    </Link>
  );
}

function CatalogSkeleton() {
  return (
    <div className="animate-pulse overflow-hidden rounded-2xl bg-white ring-1 ring-shelf-200">
      <div className="aspect-[2/3] bg-shelf-100" />
      <div className="space-y-2 p-4">
        <div className="h-4 w-4/5 rounded bg-shelf-100" />
        <div className="h-3 w-2/3 rounded bg-shelf-100" />
      </div>
    </div>
  );
}

export default function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => readQuery(params), [params]);

  const [data, setData] = useState<Page<CatalogItem> | null>(null);
  const [filters, setFilters] = useState<CatalogFilters | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [search, setSearch] = useState(query.q ?? "");
  const [yearFrom, setYearFrom] = useState(query.year_from?.toString() ?? "");
  const [yearTo, setYearTo] = useState(query.year_to?.toString() ?? "");

  const update = useCallback(
    (patch: Record<string, string | number | boolean | undefined>) => {
      setParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          Object.entries(patch).forEach(([key, value]) => {
            if (value === undefined || value === "" || value === false) {
              next.delete(key);
            } else {
              next.set(key, value === true ? "1" : String(value));
            }
          });
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  // URL — источник истины: назад/вперёд и сброс возвращают поля в исходное состояние.
  useEffect(() => setSearch(query.q ?? ""), [query.q]);
  useEffect(() => setYearFrom(query.year_from?.toString() ?? ""), [query.year_from]);
  useEffect(() => setYearTo(query.year_to?.toString() ?? ""), [query.year_to]);

  // Поиск с debounce: не дёргаем API на каждую букву.
  useEffect(() => {
    if (search === (query.q ?? "")) {
      return;
    }
    const timer = setTimeout(() => {
      update({ q: search.trim() || undefined, page: 1 });
    }, 350);
    return () => clearTimeout(timer);
  }, [search, query.q, update]);

  useEffect(() => {
    const currentFrom = query.year_from?.toString() ?? "";
    const currentTo = query.year_to?.toString() ?? "";
    if (yearFrom === currentFrom && yearTo === currentTo) {
      return;
    }
    const timer = setTimeout(() => {
      update({
        year_from: yearFrom || undefined,
        year_to: yearTo || undefined,
        page: 1,
      });
    }, 450);
    return () => clearTimeout(timer);
  }, [yearFrom, yearTo, query.year_from, query.year_to, update]);

  useEffect(() => {
    const controller = new AbortController();
    fetchCatalogFilters(controller.signal)
      .then(setFilters)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetchCatalog(query, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name === "AbortError") {
          return;
        }
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить каталог");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [query, reloadKey]);

  const reset = () => {
    setSearch("");
    setYearFrom("");
    setYearTo("");
    setParams(new URLSearchParams(), { replace: true });
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const page = query.page ?? 1;

  return (
    <section className="mx-auto max-w-6xl px-4 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-shelf-900">Каталог</h1>
          <p className="mt-1 text-shelf-600">
            Книги, фильмы и сериалы — включая кыргызские карточки.
          </p>
        </div>
        {data && !loading && (
          <p className="text-sm text-shelf-500">Найдено: {data.total}</p>
        )}
      </header>

      <div className="mt-6 space-y-4 rounded-2xl bg-white p-4 ring-1 ring-shelf-200 sm:p-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="sm:col-span-2">
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Поиск</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Название книги, фильма или сериала"
              className={CONTROL_CLASS}
            />
          </label>

          <label>
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Тип</span>
            <select
              value={query.type ?? ""}
              onChange={(event) => update({ type: event.target.value || undefined, page: 1 })}
              className={CONTROL_CLASS}
            >
              <option value="">Все типы</option>
              {ITEM_TYPES.map((type) => (
                <option key={type} value={type}>
                  {ITEM_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Сортировка</span>
            <select
              value={query.sort ?? "relevance"}
              onChange={(event) => update({ sort: event.target.value, page: 1 })}
              className={CONTROL_CLASS}
            >
              {SORTS.map((sort) => (
                <option key={sort} value={sort}>
                  {SORT_LABELS[sort]}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Жанр</span>
            <select
              value={query.genre ?? ""}
              onChange={(event) => update({ genre: event.target.value || undefined, page: 1 })}
              className={CONTROL_CLASS}
            >
              <option value="">Все жанры</option>
              {filters?.genres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Страна</span>
            <select
              value={query.country ?? ""}
              onChange={(event) => update({ country: event.target.value || undefined, page: 1 })}
              className={CONTROL_CLASS}
            >
              <option value="">Все страны</option>
              {filters?.countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1.5 block text-sm font-medium text-shelf-800">Источник</span>
            <select
              value={query.source ?? ""}
              onChange={(event) =>
                update({ source: pick(event.target.value, ITEM_SOURCES), page: 1 })
              }
              className={CONTROL_CLASS}
            >
              <option value="">Все источники</option>
              {ITEM_SOURCES.map((source) => (
                <option key={source} value={source}>
                  {SOURCE_LABELS[source]}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label>
              <span className="mb-1.5 block text-sm font-medium text-shelf-800">Год от</span>
              <input
                type="number"
                inputMode="numeric"
                min={filters?.year_min ?? 0}
                max={filters?.year_max ?? 3000}
                value={yearFrom}
                onChange={(event) => setYearFrom(event.target.value)}
                className={CONTROL_CLASS}
              />
            </label>
            <label>
              <span className="mb-1.5 block text-sm font-medium text-shelf-800">Год до</span>
              <input
                type="number"
                inputMode="numeric"
                min={filters?.year_min ?? 0}
                max={filters?.year_max ?? 3000}
                value={yearTo}
                onChange={(event) => setYearTo(event.target.value)}
                className={CONTROL_CLASS}
              />
            </label>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-shelf-800">
            <input
              type="checkbox"
              checked={query.local_only ?? false}
              onChange={(event) => update({ local_only: event.target.checked, page: 1 })}
              className="h-4 w-4 rounded border-shelf-300 text-accent-600 focus:ring-accent-600"
            />
            Только кыргызский контент
          </label>

          <Button variant="secondary" onClick={reset} disabled={params.toString() === ""}>
            Сбросить фильтры
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mt-10 rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-medium text-red-800">Не удалось загрузить каталог</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
          <Button className="mt-4" onClick={() => setReloadKey((key) => key + 1)}>
            Повторить
          </Button>
        </div>
      ) : loading && !data ? (
        <div className="mt-8 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, index) => (
            <CatalogSkeleton key={index} />
          ))}
        </div>
      ) : data && data.items.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-10 text-center">
          <p className="text-lg font-medium text-shelf-900">Ничего не нашлось</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-shelf-600">
            Попробуйте изменить фильтры — или создайте карточку: после проверки модератором она
            появится в каталоге.
          </p>
          <Button className="mt-5" onClick={reset}>
            Сбросить фильтры
          </Button>
        </div>
      ) : data ? (
        <>
          <div
            className={cn(
              "mt-8 grid grid-cols-2 gap-5 transition-opacity sm:grid-cols-3 lg:grid-cols-4",
              loading && "opacity-60",
            )}
          >
            {data.items.map((item) => (
              <CatalogCard key={item.id} item={item} />
            ))}
          </div>

          {totalPages > 1 && (
            <nav
              className="mt-8 flex items-center justify-center gap-4"
              aria-label="Страницы каталога"
            >
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => update({ page: page - 1 })}
              >
                ← Назад
              </Button>
              <span className="text-sm text-shelf-600">
                Страница {page} из {totalPages}
              </span>
              <Button
                variant="secondary"
                disabled={page >= totalPages}
                onClick={() => update({ page: page + 1 })}
              >
                Вперёд →
              </Button>
            </nav>
          )}
        </>
      ) : null}
    </section>
  );
}
