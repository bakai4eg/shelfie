import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { fetchItem } from "@/features/catalog/api";
import { localCardsApi, type LocalCardInput } from "@/features/localCards/api";
import { ITEM_TYPE_LABELS } from "@/lib/constants";
import type { ItemType, LocalCard } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { cn } from "@/lib/utils";

const ITEM_TYPES: ItemType[] = ["movie", "book", "series"];

const CONTROL_CLASS =
  "w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 " +
  "placeholder:text-shelf-400 focus:border-accent-600 focus:outline-2 " +
  "focus:outline-offset-2 focus:outline-accent-600";

export default function LocalCardFormPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const navigate = useNavigate();
  const editId = itemId ? Number(itemId) : null;
  const isEdit = editId !== null && !Number.isNaN(editId);

  const [loading, setLoading] = useState(isEdit);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [type, setType] = useState<ItemType>("movie");
  const [title, setTitle] = useState("");
  const [originalTitle, setOriginalTitle] = useState("");
  const [year, setYear] = useState("");
  const [country, setCountry] = useState("Кыргызстан");
  const [genresText, setGenresText] = useState("");
  const [description, setDescription] = useState("");
  const [isLocal, setIsLocal] = useState(true);

  const [posterFile, setPosterFile] = useState<File | null>(null);
  const [posterPreview, setPosterPreview] = useState<string | null>(null);
  const [existingPoster, setExistingPoster] = useState<string | null>(null);
  const [removePoster, setRemovePoster] = useState(false);

  const [duplicates, setDuplicates] = useState<LocalCard[]>([]);
  const [duplicatesLoading, setDuplicatesLoading] = useState(false);
  const checkSeq = useRef(0);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isEdit || editId === null) return;

    const controller = new AbortController();
    setLoading(true);
    fetchItem(editId, controller.signal)
      .then((item) => {
        setType(item.type);
        setTitle(item.title);
        setOriginalTitle(item.original_title ?? "");
        setYear(item.year ? String(item.year) : "");
        setCountry(item.country ?? "");
        setGenresText(item.genres.join(", "));
        setDescription(item.description ?? "");
        setIsLocal(item.is_local);
        setExistingPoster(item.poster_url);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        if (
          err &&
          typeof err === "object" &&
          "status" in err &&
          (err as { status: number }).status === 404
        ) {
          setNotFound(true);
        } else {
          setLoadError(
            err instanceof Error ? err.message : "Не удалось загрузить карточку",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [editId, isEdit]);

  useEffect(() => {
    if (!posterFile) {
      setPosterPreview(null);
      return;
    }
    const url = URL.createObjectURL(posterFile);
    setPosterPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [posterFile]);

  const parsedYear = year.trim() ? Number(year) : null;

  const checkDuplicates = async () => {
    const needle = title.trim();
    if (needle.length < 2) {
      setDuplicates([]);
      return;
    }

    const seq = ++checkSeq.current;
    setDuplicatesLoading(true);
    try {
      const found = await localCardsApi.duplicates(needle, parsedYear);
      if (seq === checkSeq.current) {
        setDuplicates(found);
      }
    } catch {
      if (seq === checkSeq.current) {
        setDuplicates([]);
      }
    } finally {
      if (seq === checkSeq.current) {
        setDuplicatesLoading(false);
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Укажите название карточки");
      return;
    }
    if (year.trim() && (!Number.isInteger(parsedYear) || (parsedYear ?? -1) < 0)) {
      setError("Год должен быть целым неотрицательным числом");
      return;
    }

    const genres = genresText
      .split(/[,;]/)
      .map((genre) => genre.trim())
      .filter(Boolean);

    if (genres.length > 20) {
      setError("Укажите не больше 20 жанров");
      return;
    }

    const input: LocalCardInput = {
      type,
      title: title.trim(),
      original_title: originalTitle.trim() || null,
      year: parsedYear,
      country: country.trim() || null,
      genres,
      description: description.trim() || null,
      is_local: isLocal,
    };

    setSubmitting(true);
    try {
      if (isEdit && editId !== null) {
        await localCardsApi.update(
          editId,
          input,
          posterFile,
          removePoster && !posterFile,
        );
      } else {
        await localCardsApi.create(input, posterFile);
      }
      navigate("/my/cards");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить карточку");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center text-shelf-600">
        Загрузка карточки...
      </div>
    );
  }

  if (notFound) {
    return (
      <section className="mx-auto max-w-xl px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-shelf-900">Карточка не найдена</h1>
        <p className="mt-2 text-shelf-600">
          Возможно, её уже проверили или она принадлежит другому пользователю.
        </p>
        <Link to="/my/cards" className={buttonClass("secondary", "mt-6")}>
          ← Мои карточки
        </Link>
      </section>
    );
  }

  const shownPoster = posterPreview ?? (removePoster ? null : existingPoster);

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <header>
        <Link
          to="/my/cards"
          className="text-sm font-medium text-shelf-600 hover:text-shelf-900"
        >
          ← Мои карточки
        </Link>
        <h1 className="mt-3 text-3xl font-semibold text-shelf-900">
          {isEdit ? "Исправить карточку" : "Новая карточка"}
        </h1>
        <p className="mt-1 text-shelf-600">
          Карточка уйдёт модератору на проверку. Пока она на проверке, данные можно
          исправлять.
        </p>
      </header>

      {loadError && (
        <div className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {loadError}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="mt-8 space-y-6 rounded-3xl bg-white p-5 ring-1 ring-shelf-200 sm:p-8"
      >
        {error && (
          <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label
              htmlFor="local-card-type"
              className="block text-sm font-medium text-shelf-800"
            >
              Тип
            </label>
            <select
              id="local-card-type"
              value={type}
              onChange={(event) => setType(event.target.value as ItemType)}
              className={CONTROL_CLASS}
            >
              {ITEM_TYPES.map((itemType) => (
                <option key={itemType} value={itemType}>
                  {ITEM_TYPE_LABELS[itemType]}
                </option>
              ))}
            </select>
          </div>

          <Field
            label="Год"
            type="number"
            min={0}
            max={3000}
            inputMode="numeric"
            placeholder="2010"
            value={year}
            onChange={(event) => setYear(event.target.value)}
            onBlur={() => void checkDuplicates()}
          />
        </div>

        <div>
          <Field
            label="Название"
            required
            maxLength={500}
            placeholder="Например, «Манас. Великий поход»"
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
              setDuplicates([]);
            }}
            onBlur={() => void checkDuplicates()}
          />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void checkDuplicates()}
              disabled={duplicatesLoading || title.trim().length < 2}
              className="text-xs font-medium text-accent-700 hover:underline disabled:cursor-not-allowed disabled:text-shelf-400 disabled:no-underline"
            >
              {duplicatesLoading ? "Проверяем совпадения..." : "Проверить совпадения"}
            </button>
          </div>

          {duplicates.length > 0 && (
            <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">
                Похоже, такая карточка уже есть
              </p>
              <p className="mt-1 text-xs text-amber-800">
                Проверьте совпадения до сохранения — возможно, стоит дополнить
                существующую карточку.
              </p>
              <ul className="mt-3 space-y-2">
                {duplicates.map((card) => (
                  <li key={card.id}>
                    <Link
                      to={`/catalog/${card.id}`}
                      className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm text-amber-900 hover:text-accent-700"
                    >
                      <span className="font-medium">{card.title}</span>
                      <span className="text-xs text-amber-700">
                        {[card.year, ITEM_TYPE_LABELS[card.type], card.country]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                      <span className="text-xs underline">открыть</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <Field
          label="Оригинальное название"
          maxLength={500}
          placeholder="Manas"
          value={originalTitle}
          onChange={(event) => setOriginalTitle(event.target.value)}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label="Страна"
            maxLength={100}
            placeholder="Кыргызстан"
            value={country}
            onChange={(event) => setCountry(event.target.value)}
          />
          <Field
            label="Жанры"
            hint="Через запятую: эпос, история"
            value={genresText}
            onChange={(event) => setGenresText(event.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="local-card-description"
            className="block text-sm font-medium text-shelf-800"
          >
            Описание
          </label>
          <textarea
            id="local-card-description"
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Чем известна эта книга или фильм?"
            className={cn(CONTROL_CLASS, "resize-y")}
          />
        </div>

        <div className="space-y-2">
          <span className="block text-sm font-medium text-shelf-800">Обложка</span>
          <div className="flex flex-wrap items-start gap-4">
            <div className="relative aspect-[2/3] w-24 overflow-hidden rounded-xl bg-shelf-100 ring-1 ring-shelf-200">
              {shownPoster ? (
                <img src={shownPoster} alt="" className="h-full w-full object-cover" />
              ) : (
                <span className="flex h-full items-center justify-center p-2 text-center text-xs text-shelf-400">
                  Нет обложки
                </span>
              )}
            </div>

            <div className="min-w-0 flex-1 space-y-2">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setPosterFile(file);
                  if (file) setRemovePoster(false);
                }}
                className="block w-full text-sm text-shelf-700 file:mr-3 file:rounded-xl file:border-0 file:bg-shelf-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-shelf-50 hover:file:bg-shelf-800"
              />
              <p className="text-xs text-shelf-500">JPEG, PNG или WebP, до 5 МБ.</p>
              {(shownPoster || posterFile) && (
                <button
                  type="button"
                  onClick={() => {
                    setPosterFile(null);
                    setRemovePoster(true);
                  }}
                  className="text-xs font-medium text-red-600 hover:underline"
                >
                  Убрать обложку
                </button>
              )}
            </div>
          </div>
        </div>

        <label className="flex items-start gap-3 rounded-2xl bg-shelf-50 p-4 text-sm text-shelf-700 ring-1 ring-shelf-200">
          <input
            type="checkbox"
            checked={isLocal}
            onChange={(event) => setIsLocal(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-shelf-300 text-accent-600 focus:ring-accent-600"
          />
          <span>
            <span className="font-medium text-shelf-900">
              Кыргызстанский контент
            </span>
            <span className="mt-0.5 block text-xs text-shelf-500">
              Карточка попадёт в региональный фильтр каталога.
            </span>
          </span>
        </label>

        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Сохранение..."
              : isEdit
                ? "Сохранить изменения"
                : "Отправить на проверку"}
          </Button>
          <Button
            variant="ghost"
            type="button"
            disabled={submitting}
            onClick={() => navigate("/my/cards")}
          >
            Отмена
          </Button>
        </div>
      </form>
    </section>
  );
}
