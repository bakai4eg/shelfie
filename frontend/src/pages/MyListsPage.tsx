import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { listsApi } from "@/features/lists/api";
import { LIST_THEMES } from "@/features/lists/themes";
import { LIST_THEME_LABELS } from "@/lib/constants";
import type { ListSummary, ListTheme } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ThemePicker({
  value,
  onChange,
}: {
  value: ListTheme;
  onChange: (theme: ListTheme) => void;
}) {
  return (
    <fieldset>
      <legend className="block text-sm font-medium text-shelf-800">Тема оформления</legend>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {(Object.keys(LIST_THEMES) as ListTheme[]).map((theme) => (
          <button
            key={theme}
            type="button"
            onClick={() => onChange(theme)}
            aria-pressed={value === theme}
            className={cn(
              "overflow-hidden rounded-xl text-left text-sm ring-1 ring-shelf-300 transition",
              value === theme && "ring-2 ring-accent-600",
            )}
          >
            <span className={cn("block h-10", LIST_THEMES[theme].swatch)} />
            <span className="block bg-white px-2 py-1.5 font-medium text-shelf-800">
              {LIST_THEME_LABELS[theme]}
            </span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function MyListsPage() {
  const navigate = useNavigate();
  const [lists, setLists] = useState<ListSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [theme, setTheme] = useState<ListTheme>("classic");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | undefined>();

  useEffect(() => {
    const controller = new AbortController();
    listsApi
      .mine(controller.signal)
      .then(setLists)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить списки");
      });
    return () => controller.abort();
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setFormError("Введите название");
      return;
    }
    setCreating(true);
    setFormError(undefined);
    try {
      const created = await listsApi.create({ title: title.trim(), theme });
      navigate(`/me/lists/${created.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Не удалось создать список");
      setCreating(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-shelf-900">Мои списки</h1>
      <p className="mt-1 max-w-xl text-shelf-600">
        Собирайте подборки, пишите заметки к каждой карточке и делитесь ими по ссылке.
      </p>

      <form
        onSubmit={(event) => void onCreate(event)}
        className="mt-6 grid gap-4 rounded-2xl bg-white p-4 ring-1 ring-shelf-200 sm:grid-cols-[1fr_auto]"
      >
        <div className="space-y-4">
          <Field
            label="Название нового списка"
            value={title}
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            error={formError}
            placeholder="Например, «Что посмотреть зимой»"
          />
          <ThemePicker value={theme} onChange={setTheme} />
        </div>
        <Button type="submit" disabled={creating} className="self-end">
          {creating ? "Создаём…" : "Создать список"}
        </Button>
      </form>

      {error ? (
        <p className="mt-8 text-red-700" role="alert">
          {error}
        </p>
      ) : lists === null ? (
        <p className="mt-8 text-sm text-shelf-500" role="status">
          Загружаем…
        </p>
      ) : lists.length === 0 ? (
        <p className="mt-8 text-shelf-600">Списков пока нет — создайте первый выше.</p>
      ) : (
        <ul className="mt-8 grid gap-3 sm:grid-cols-2">
          {lists.map((list) => (
            <li key={list.id} className="overflow-hidden rounded-2xl bg-white ring-1 ring-shelf-200">
              <div className={cn("h-2", LIST_THEMES[list.theme].swatch)} />
              <div className="p-4">
                <Link
                  to={`/me/lists/${list.id}`}
                  className="text-lg font-semibold text-shelf-900 hover:text-accent-700"
                >
                  {list.title}
                </Link>
                <p className="mt-1 text-sm text-shelf-500">
                  Карточек: {list.items_count} · {LIST_THEME_LABELS[list.theme]} ·{" "}
                  {list.is_public ? "публичный" : "приватный"}
                </p>
                {list.is_public ? (
                  <Link to={`/lists/${list.id}`} className="mt-2 inline-block text-sm text-accent-600">
                    Открыть витрину →
                  </Link>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
