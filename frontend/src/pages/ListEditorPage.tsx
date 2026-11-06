import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { fetchCatalog } from "@/features/catalog/api";
import { listsApi } from "@/features/lists/api";
import { ApiError } from "@/lib/api";
import { LIST_NOTE_MAX_LENGTH } from "@/lib/constants";
import type { CatalogItem, ListDetail, ListItemEntry } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { cn } from "@/lib/utils";
import { ThemePicker } from "@/pages/MyListsPage";

function NoteEditor({
  entry,
  onSave,
}: {
  entry: ListItemEntry;
  onSave: (note: string) => Promise<void>;
}) {
  const [value, setValue] = useState(entry.note ?? "");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const tooLong = value.length > LIST_NOTE_MAX_LENGTH;
  const dirty = value !== (entry.note ?? "");

  async function save() {
    if (tooLong || !dirty) return;
    setSaving(true);
    setSaveError(null);
    try {
      await onSave(value);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Не удалось сохранить заметку");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2">
      <label className="sr-only" htmlFor={`note-${entry.item.id}`}>
        Заметка к «{entry.item.title}»
      </label>
      <textarea
        id={`note-${entry.item.id}`}
        value={value}
        rows={2}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => void save()}
        aria-invalid={tooLong}
        placeholder="Заметка: почему эта карточка в списке"
        className={cn(
          "w-full rounded-xl border bg-white px-3 py-2 text-sm text-shelf-900 focus:outline-2 focus:outline-offset-2",
          tooLong
            ? "border-red-500 bg-red-50 focus:outline-red-500"
            : "border-shelf-300 focus:outline-accent-600",
        )}
      />
      <div className="mt-1 flex items-center justify-between text-xs">
        <span className={tooLong ? "font-medium text-red-600" : "text-shelf-500"}>
          {tooLong
            ? `Слишком длинная заметка: ${value.length} из ${LIST_NOTE_MAX_LENGTH}. Не сохранится.`
            : `${value.length} / ${LIST_NOTE_MAX_LENGTH}`}
        </span>
        <span className="text-shelf-500">
          {saving ? "Сохраняем…" : saveError ? <span className="text-red-600">{saveError}</span> : dirty && !tooLong ? "Сохранится при выходе из поля" : ""}
        </span>
      </div>
    </div>
  );
}

export default function ListEditorPage() {
  const { listId } = useParams();
  const id = Number(listId);
  const navigate = useNavigate();

  const [list, setList] = useState<ListDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CatalogItem[]>([]);
  const [searching, setSearching] = useState(false);

  const apply = useCallback((next: ListDetail) => {
    setList(next);
    setTitle(next.title);
    setDescription(next.description ?? "");
  }, []);

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) {
      setNotFound(true);
      return;
    }
    const controller = new AbortController();
    listsApi
      .get(id, controller.signal)
      .then(apply)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
        else setError(err instanceof Error ? err.message : "Не удалось загрузить список");
      });
    return () => controller.abort();
  }, [id, apply]);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    setSearching(true);
    const timer = window.setTimeout(() => {
      fetchCatalog({ q: query.trim(), size: 6 }, controller.signal)
        .then((page) => setResults(page.items))
        .catch(() => undefined)
        .finally(() => {
          if (!controller.signal.aborted) setSearching(false);
        });
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  /** Все действия идут через один обработчик: ошибка выводится одинаково. */
  async function run(action: () => Promise<ListDetail | void>) {
    setBanner(null);
    try {
      const next = await action();
      if (next) apply(next);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Что-то пошло не так");
      throw err;
    }
  }

  function move(from: number, to: number) {
    if (!list || to < 0 || to >= list.items.length || from === to) return;
    const items = [...list.items];
    const [moved] = items.splice(from, 1);
    items.splice(to, 0, moved);
    const previous = list;
    // сразу показываем новый порядок, на ошибке возвращаем прежний
    setList({ ...list, items: items.map((entry, position) => ({ ...entry, position })) });
    void run(() => listsApi.setOrder(list.id, items.map((entry) => entry.item.id))).catch(() =>
      setList(previous),
    );
  }

  async function saveMain() {
    if (!list) return;
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setBanner("Название не может быть пустым");
      return;
    }
    await run(() =>
      listsApi.update(list.id, { title: cleanTitle, description: description.trim() || null }),
    ).catch(() => undefined);
  }

  async function share() {
    const url = `${window.location.origin}/lists/${id}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Скопируйте ссылку", url);
    }
  }

  async function removeList() {
    if (!list || !window.confirm(`Удалить список «${list.title}»? Это нельзя отменить.`)) return;
    await run(async () => {
      await listsApi.remove(list.id);
      navigate("/me/lists");
    }).catch(() => undefined);
  }

  if (notFound) {
    return (
      <section className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-2xl font-semibold text-shelf-900">Список не найден</h1>
        <Link to="/me/lists" className="mt-6 inline-block font-medium text-accent-600">
          К моим спискам →
        </Link>
      </section>
    );
  }
  if (error) {
    return (
      <p className="mx-auto max-w-2xl px-4 py-16 text-red-700" role="alert">
        {error}
      </p>
    );
  }
  if (!list) {
    return (
      <p className="mx-auto max-w-2xl px-4 py-16 text-sm text-shelf-500" role="status">
        Загружаем список…
      </p>
    );
  }

  const inList = new Set(list.items.map((entry) => entry.item.id));

  return (
    <section className="mx-auto max-w-4xl px-4 py-10">
      <Link to="/me/lists" className="text-sm text-shelf-600 hover:text-accent-700">
        ← Мои списки
      </Link>
      <h1 className="mt-2 text-3xl font-semibold text-shelf-900">Редактор списка</h1>

      {banner ? (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200" role="alert">
          {banner}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 rounded-2xl bg-white p-4 ring-1 ring-shelf-200 sm:p-6 md:grid-cols-2">
        <div className="space-y-4">
          <Field label="Название" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
          <div className="space-y-1.5">
            <label htmlFor="list-description" className="block text-sm font-medium text-shelf-800">
              Описание
            </label>
            <textarea
              id="list-description"
              value={description}
              rows={3}
              maxLength={1000}
              onChange={(event) => setDescription(event.target.value)}
              className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:outline-offset-2 focus:outline-accent-600"
            />
          </div>
          <Button onClick={() => void saveMain()}>Сохранить название и описание</Button>
        </div>

        <div className="space-y-4">
          <ThemePicker
            value={list.theme}
            onChange={(theme) => void run(() => listsApi.update(list.id, { theme })).catch(() => undefined)}
          />
          <label className="flex items-start gap-3 text-sm text-shelf-800">
            <input
              type="checkbox"
              checked={list.is_public}
              onChange={(event) =>
                void run(() => listsApi.update(list.id, { is_public: event.target.checked })).catch(
                  () => undefined,
                )
              }
              className="mt-0.5 h-4 w-4 accent-[#c2410c]"
            />
            <span>
              Публичный список
              <span className="block text-xs text-shelf-500">
                Откроется по ссылке без входа. Приватный видите только вы.
              </span>
            </span>
          </label>
          {list.is_public ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => void share()}>
                {copied ? "Ссылка скопирована ✓" : "Поделиться"}
              </Button>
              <Link to={`/lists/${list.id}`} className={buttonClass("ghost")}>
                Открыть витрину
              </Link>
            </div>
          ) : null}
        </div>
      </div>

      <h2 className="mt-10 text-xl font-semibold text-shelf-900">Карточки ({list.items.length})</h2>
      <p className="mt-1 text-sm text-shelf-500">
        Меняйте порядок перетаскиванием или кнопками ↑ ↓ — он сохраняется сразу.
      </p>

      {list.items.length === 0 ? (
        <p className="mt-4 text-shelf-600">Пока пусто — найдите карточки ниже.</p>
      ) : (
        <ol className="mt-4 space-y-3">
          {list.items.map((entry, index) => (
            <li
              key={entry.item.id}
              draggable
              onDragStart={() => setDragIndex(index)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                if (dragIndex !== null) move(dragIndex, index);
                setDragIndex(null);
              }}
              onDragEnd={() => setDragIndex(null)}
              className={cn(
                "flex gap-3 rounded-2xl bg-white p-3 ring-1 ring-shelf-200",
                dragIndex === index && "opacity-50",
              )}
            >
              <span
                className="hidden cursor-grab select-none self-center px-1 text-xl text-shelf-400 sm:block"
                aria-hidden
                title="Потяните, чтобы изменить порядок"
              >
                ⋮⋮
              </span>
              {entry.item.poster_url ? (
                <img src={entry.item.poster_url} alt="" className="h-20 w-14 rounded-lg object-cover" />
              ) : (
                <span className="flex h-20 w-14 items-center justify-center rounded-lg bg-shelf-100 text-[10px] text-shelf-500">
                  нет
                </span>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="break-words font-medium text-shelf-900">
                    {index + 1}. {entry.item.title}
                    {entry.item.year ? <span className="text-shelf-500"> · {entry.item.year}</span> : null}
                  </p>
                  <div className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      onClick={() => move(index, index - 1)}
                      disabled={index === 0}
                      aria-label={`Выше: ${entry.item.title}`}
                      className="rounded-lg px-2 py-1 text-shelf-700 hover:bg-shelf-100 disabled:opacity-30"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => move(index, index + 1)}
                      disabled={index === list.items.length - 1}
                      aria-label={`Ниже: ${entry.item.title}`}
                      className="rounded-lg px-2 py-1 text-shelf-700 hover:bg-shelf-100 disabled:opacity-30"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void run(() => listsApi.removeItem(list.id, entry.item.id)).catch(() => undefined)
                      }
                      aria-label={`Убрать: ${entry.item.title}`}
                      className="rounded-lg px-2 py-1 text-red-700 hover:bg-red-50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <NoteEditor
                  key={`${entry.item.id}-${entry.note ?? ""}`}
                  entry={entry}
                  onSave={async (note) => {
                    await run(() => listsApi.setNote(list.id, entry.item.id, note));
                  }}
                />
              </div>
            </li>
          ))}
        </ol>
      )}

      <div className="mt-10 rounded-2xl bg-shelf-100 p-4 sm:p-6">
        <Field
          label="Добавить карточку из каталога"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Начните вводить название"
        />
        {searching ? <p className="mt-3 text-sm text-shelf-500">Ищем…</p> : null}
        {results.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {results.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-2">
                <span className="min-w-0 truncate text-sm text-shelf-900">
                  {item.title}
                  {item.year ? <span className="text-shelf-500"> · {item.year}</span> : null}
                </span>
                <Button
                  variant="secondary"
                  disabled={inList.has(item.id)}
                  onClick={() => void run(() => listsApi.addItem(list.id, item.id)).catch(() => undefined)}
                >
                  {inList.has(item.id) ? "Уже в списке" : "Добавить"}
                </Button>
              </li>
            ))}
          </ul>
        ) : query.trim().length >= 2 && !searching ? (
          <p className="mt-3 text-sm text-shelf-600">Ничего не найдено.</p>
        ) : null}
      </div>

      <div className="mt-10 border-t border-shelf-200 pt-6">
        <Button variant="ghost" className="text-red-700 hover:bg-red-50" onClick={() => void removeList()}>
          Удалить список
        </Button>
      </div>
    </section>
  );
}
