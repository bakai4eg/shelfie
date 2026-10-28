import { useCallback, useEffect, useId, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import GuestNotice from "@/components/ui/GuestNotice";
import { useAuth } from "@/features/auth/context";
import { fetchItem } from "@/features/catalog/api";
import { libraryApi } from "@/features/library/api";
import { moderationApi, type ReportCreatePayload } from "@/features/moderation/api";
import { reviewsApi } from "@/features/reviews/api";
import { ITEM_TYPE_LABELS, REPORT_REASON_LABELS, SHELF_STATUS_LABELS } from "@/lib/constants";
import type { CatalogItem, Review, ShelfEntry, ShelfStatus } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { cn, formatDate, formatRating } from "@/lib/utils";

const SHELF_KEYS: ShelfStatus[] = ["watching", "finished", "planned", "dropped"];

export default function ItemPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const id = Number(itemId);
  const { user } = useAuth();

  const [item, setItem] = useState<CatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Полка и личная оценка
  const [shelfEntry, setShelfEntry] = useState<ShelfEntry | null>(null);
  const [userRating, setUserRating] = useState<number | null>(null);
  const [finishedAt, setFinishedAt] = useState<string>("");
  const [shelfSaving, setShelfSaving] = useState(false);

  // Рецензии
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [reviewFormOpen, setReviewFormOpen] = useState(false);
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewBody, setReviewBody] = useState("");
  const [reviewRating, setReviewRating] = useState<number | "">("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Жалоба (модалка)
  const [reportTarget, setReportTarget] = useState<{
    type: "item" | "review";
    id: number;
    title?: string;
  } | null>(null);
  const [reportReason, setReportReason] = useState<ReportCreatePayload["reason"]>("spam");
  const [reportComment, setReportComment] = useState("");
  const [reportSubmitting, setReportSubmitting] = useState(false);
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const reportCommentId = useId();

  // Загрузка карточки
  useEffect(() => {
    if (!id || Number.isNaN(id)) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setNotFound(false);
    setError(null);

    fetchItem(id, controller.signal)
      .then((data) => {
        setItem(data);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) {
          setNotFound(true);
        } else {
          setError(err instanceof Error ? err.message : "Не удалось загрузить карточку");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [id]);

  // Загрузка рецензий
  const loadReviews = useCallback(() => {
    if (!id || Number.isNaN(id)) return;
    setReviewsLoading(true);
    reviewsApi
      .listForItem(id, 1, 50)
      .then((res) => {
        setReviews(res.items);
      })
      .catch(() => undefined)
      .finally(() => setReviewsLoading(false));
  }, [id]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  // Загрузка пользовательской полки и оценки
  useEffect(() => {
    if (!user || !id || Number.isNaN(id)) {
      setShelfEntry(null);
      setUserRating(null);
      return;
    }

    libraryApi
      .list()
      .then((entries) => {
        const found = entries.find((e) => e.item_id === id);
        if (found) {
          setShelfEntry(found);
          setUserRating(found.user_rating);
          if (found.finished_at) {
            setFinishedAt(found.finished_at);
          }
        } else {
          setShelfEntry(null);
        }
      })
      .catch(() => undefined);
  }, [user, id]);

  // Пользовательская рецензия
  const myReview = user
    ? reviews.find((r) => r.user_login.toLowerCase() === user.login.toLowerCase())
    : undefined;

  // Инициализация формы редактирования рецензии
  const handleStartEditReview = () => {
    if (myReview) {
      setReviewTitle(myReview.title);
      setReviewBody(myReview.body);
      setReviewRating(myReview.rating ?? "");
    } else {
      setReviewTitle("");
      setReviewBody("");
      setReviewRating(userRating ?? "");
    }
    setReviewError(null);
    setReviewFormOpen(true);
  };

  const handleShelfChange = async (status: ShelfStatus) => {
    if (!id || shelfSaving) return;
    setShelfSaving(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      const finishDate = status === "finished" ? finishedAt || today : null;
      if (status === "finished" && !finishedAt) {
        setFinishedAt(today);
      }
      const updated = await libraryApi.upsertShelf(id, {
        status,
        finished_at: finishDate,
      });
      setShelfEntry(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось обновить полку");
    } finally {
      setShelfSaving(false);
    }
  };

  const handleFinishedAtChange = async (dateVal: string) => {
    setFinishedAt(dateVal);
    if (!id || !shelfEntry || shelfEntry.status !== "finished") return;
    try {
      const updated = await libraryApi.upsertShelf(id, {
        status: "finished",
        finished_at: dateVal || null,
      });
      setShelfEntry(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось сохранить дату завершения");
    }
  };

  const handleRemoveFromShelf = async () => {
    if (!id || !shelfEntry) return;
    setShelfSaving(true);
    try {
      await libraryApi.deleteShelf(id);
      setShelfEntry(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось убрать с полки");
    } finally {
      setShelfSaving(false);
    }
  };

  const handleSetRating = async (val: number) => {
    if (!id) return;
    try {
      const res = await libraryApi.setRating(id, val);
      setUserRating(res.value);
      if (item) {
        setItem({
          ...item,
          rating_avg: res.rating_avg ?? 0,
          ratings_count: res.ratings_count,
        });
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось поставить оценку");
    }
  };

  const handleDeleteRating = async () => {
    if (!id) return;
    try {
      const res = await libraryApi.deleteRating(id);
      setUserRating(null);
      if (item) {
        setItem({
          ...item,
          rating_avg: res.rating_avg ?? 0,
          ratings_count: res.ratings_count,
        });
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить оценку");
    }
  };

  const handleSaveReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    if (!reviewTitle.trim() || !reviewBody.trim()) {
      setReviewError("Заполните заголовок и текст рецензии");
      return;
    }
    setReviewSubmitting(true);
    setReviewError(null);
    try {
      const numericRating = reviewRating === "" ? null : Number(reviewRating);
      if (myReview) {
        await reviewsApi.update(myReview.id, {
          title: reviewTitle.trim(),
          body: reviewBody.trim(),
          rating: numericRating,
        });
      } else {
        await reviewsApi.create(id, {
          title: reviewTitle.trim(),
          body: reviewBody.trim(),
          rating: numericRating,
        });
      }
      setReviewFormOpen(false);
      loadReviews();
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Не удалось сохранить рецензию");
    } finally {
      setReviewSubmitting(false);
    }
  };

  const handleDeleteReview = async () => {
    if (!myReview || !window.confirm("Удалить вашу рецензию?")) return;
    try {
      await reviewsApi.delete(myReview.id);
      loadReviews();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить рецензию");
    }
  };

  const handleOpenReport = (type: "item" | "review", targetId: number, title?: string) => {
    setReportTarget({ type, id: targetId, title });
    setReportReason("spam");
    setReportComment("");
    setReportMessage(null);
    setReportError(null);
  };

  const handleSubmitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportTarget) return;
    setReportSubmitting(true);
    setReportError(null);
    try {
      await moderationApi.createReport({
        target_type: reportTarget.type,
        target_id: reportTarget.id,
        reason: reportReason,
        comment: reportComment.trim() || null,
      });
      setReportMessage("Жалоба отправлена модераторам");
      setTimeout(() => {
        setReportTarget(null);
        setReportMessage(null);
      }, 1500);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : "Не удалось отправить жалобу");
    } finally {
      setReportSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-16 text-center text-shelf-600">
        Загрузка карточки...
      </div>
    );
  }

  if (notFound || !item) {
    return (
      <section className="mx-auto max-w-xl px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-shelf-900">Карточка не найдена</h1>
        <p className="mt-2 text-shelf-600">
          Возможно, она была удалена, скрыта модератором или ещё не добавлена в каталог.
        </p>
        <Link to="/catalog" className={buttonClass("primary", "mt-6")}>
          ← В каталог
        </Link>
      </section>
    );
  }

  if (error) {
    return (
      <section className="mx-auto max-w-xl px-4 py-20 text-center">
        <p className="text-red-600">{error}</p>
        <Link to="/catalog" className={buttonClass("secondary", "mt-6")}>
          ← В каталог
        </Link>
      </section>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-6">
        <Link
          to="/catalog"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-shelf-600 hover:text-shelf-900"
        >
          ← В каталог
        </Link>
      </div>

      {/* Карточка: обложка + данные */}
      <div className="grid gap-8 rounded-3xl bg-white p-6 ring-1 ring-shelf-200 md:grid-cols-[280px_1fr] md:p-8">
        {/* Обложка */}
        <div className="relative aspect-[2/3] overflow-hidden rounded-2xl bg-shelf-100 ring-1 ring-shelf-200">
          {item.poster_url ? (
            <img
              src={item.poster_url}
              alt={item.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm font-medium text-shelf-500">
              {ITEM_TYPE_LABELS[item.type]}
            </div>
          )}
          {item.is_local && (
            <span className="absolute left-3 top-3 rounded-full bg-accent-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
              Кыргызстан
            </span>
          )}
        </div>

        {/* Данные карточки */}
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex rounded-lg bg-shelf-100 px-2.5 py-1 text-xs font-medium text-shelf-700">
              {ITEM_TYPE_LABELS[item.type]}
            </span>
            {user && (
              <button
                type="button"
                onClick={() => handleOpenReport("item", item.id, item.title)}
                className="text-xs text-shelf-500 hover:text-red-600"
              >
                Пожаловаться
              </button>
            )}
          </div>

          <h1 className="mt-2 text-2xl font-bold text-shelf-900 sm:text-3xl">
            {item.title}
          </h1>

          {item.original_title && (
            <p className="mt-1 text-sm italic text-shelf-500">{item.original_title}</p>
          )}

          {/* Мета: год, страна, жанры */}
          <div className="mt-4 space-y-1 text-sm text-shelf-600">
            {item.year && (
              <p>
                <span className="text-shelf-400">Год выпуска:</span> {item.year}
              </p>
            )}
            {item.country && (
              <p>
                <span className="text-shelf-400">Страна:</span> {item.country}
              </p>
            )}
            {item.genres && item.genres.length > 0 && (
              <p>
                <span className="text-shelf-400">Жанры:</span> {item.genres.join(", ")}
              </p>
            )}
          </div>

          {/* Рейтинг платформы */}
          <div className="mt-6 flex items-baseline gap-3 rounded-2xl bg-shelf-50 p-4 ring-1 ring-shelf-200">
            {item.ratings_count > 0 ? (
              <>
                <span className="text-2xl font-bold text-accent-600">
                  ★ {formatRating(item.rating_avg)}
                </span>
                <span className="text-sm text-shelf-500">
                  {item.ratings_count}{" "}
                  {item.ratings_count === 1
                    ? "оценка"
                    : item.ratings_count >= 2 && item.ratings_count <= 4
                    ? "оценки"
                    : "оценок"}
                </span>
              </>
            ) : (
              <span className="text-sm font-medium text-shelf-500">
                Пока нет оценок платформы
              </span>
            )}
          </div>

          {/* Описание */}
          {item.description ? (
            <p className="mt-6 whitespace-pre-line text-sm leading-relaxed text-shelf-700">
              {item.description}
            </p>
          ) : (
            <p className="mt-6 text-sm italic text-shelf-400">Описание отсутствует.</p>
          )}
        </div>
      </div>

      {/* Блок действий пользователя (ТЗ 4.2.2) */}
      <div className="mt-8 rounded-3xl bg-white p-6 ring-1 ring-shelf-200 md:p-8">
        {!user ? (
          <GuestNotice action="добавить на полку, поставить оценку или написать рецензию" />
        ) : (
          <div className="space-y-8">
            {/* Полки */}
            <div>
              <h2 className="text-lg font-semibold text-shelf-900">Моя полка</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {SHELF_KEYS.map((key) => {
                  const active = shelfEntry?.status === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      disabled={shelfSaving}
                      onClick={() => handleShelfChange(key)}
                      className={cn(
                        "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-accent-600 text-white"
                          : "bg-shelf-100 text-shelf-700 hover:bg-shelf-200",
                      )}
                    >
                      {SHELF_STATUS_LABELS[key]}
                    </button>
                  );
                })}
                {shelfEntry && (
                  <button
                    type="button"
                    disabled={shelfSaving}
                    onClick={handleRemoveFromShelf}
                    className="rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Убрать с полки
                  </button>
                )}
              </div>

              {/* Поле даты завершения при статусе finished */}
              {shelfEntry?.status === "finished" && (
                <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
                  <label htmlFor="finished-date-input" className="font-medium text-shelf-700">
                    Дата завершения:
                  </label>
                  <input
                    id="finished-date-input"
                    type="date"
                    value={finishedAt}
                    onChange={(e) => handleFinishedAtChange(e.target.value)}
                    className="rounded-xl border border-shelf-300 px-3 py-1.5 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                  />
                </div>
              )}
            </div>

            <hr className="border-shelf-200" />

            {/* Оценка */}
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-shelf-900">
                  Моя оценка: {userRating ? `${userRating} / 10` : "ещё не выставлена"}
                </h2>
                {userRating !== null && (
                  <button
                    type="button"
                    onClick={handleDeleteRating}
                    className="text-xs font-medium text-red-600 hover:underline"
                  >
                    Снять оценку
                  </button>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5 sm:gap-2">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => {
                  const active = userRating === num;
                  return (
                    <button
                      key={num}
                      type="button"
                      onClick={() => handleSetRating(num)}
                      className={cn(
                        "flex h-9 w-9 items-center justify-center rounded-xl text-sm font-semibold transition-colors",
                        active
                          ? "bg-accent-600 text-white ring-2 ring-accent-400"
                          : "bg-shelf-100 text-shelf-700 hover:bg-accent-100 hover:text-accent-700",
                      )}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>
            </div>

            <hr className="border-shelf-200" />

            {/* Блок рецензии пользователя */}
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-shelf-900">Моя рецензия</h2>
                {!reviewFormOpen && (
                  <Button
                    variant="secondary"
                    onClick={handleStartEditReview}
                  >
                    {myReview ? "Редактировать рецензию" : "Написать рецензию"}
                  </Button>
                )}
              </div>

              {myReview && !reviewFormOpen && (
                <div className="mt-4 rounded-2xl bg-shelf-50 p-5 ring-1 ring-shelf-200">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold text-shelf-900">{myReview.title}</h3>
                    {myReview.rating && (
                      <span className="text-sm font-bold text-accent-600">
                        ★ {myReview.rating} / 10
                      </span>
                    )}
                  </div>
                  <p className="mt-2 whitespace-pre-line text-sm text-shelf-700">{myReview.body}</p>
                  <div className="mt-4 flex items-center justify-between text-xs text-shelf-500">
                    <span>{formatDate(myReview.created_at)}</span>
                    <button
                      type="button"
                      onClick={handleDeleteReview}
                      className="font-medium text-red-600 hover:underline"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              )}

              {reviewFormOpen && (
                <form onSubmit={handleSaveReview} className="mt-4 space-y-4 rounded-2xl bg-shelf-50 p-5 ring-1 ring-shelf-200">
                  {reviewError && (
                    <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
                      {reviewError}
                    </div>
                  )}
                  <div>
                    <label htmlFor="review-title-input" className="mb-1 block text-sm font-medium text-shelf-800">
                      Заголовок рецензии
                    </label>
                    <input
                      id="review-title-input"
                      type="text"
                      maxLength={200}
                      required
                      value={reviewTitle}
                      onChange={(e) => setReviewTitle(e.target.value)}
                      placeholder="Краткое резюме впечатлений"
                      className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                    />
                  </div>

                  <div>
                    <label htmlFor="review-rating-select" className="mb-1 block text-sm font-medium text-shelf-800">
                      Оценка в рецензии (необязательно)
                    </label>
                    <select
                      id="review-rating-select"
                      value={reviewRating}
                      onChange={(e) =>
                        setReviewRating(e.target.value === "" ? "" : Number(e.target.value))
                      }
                      className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                    >
                      <option value="">Без оценки</option>
                      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                        <option key={num} value={num}>
                          {num} из 10
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="review-body-input" className="mb-1 block text-sm font-medium text-shelf-800">
                      Текст рецензии
                    </label>
                    <textarea
                      id="review-body-input"
                      rows={5}
                      required
                      value={reviewBody}
                      onChange={(e) => setReviewBody(e.target.value)}
                      placeholder="Поделитесь своими впечатлениями подробнее..."
                      className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                    />
                  </div>

                  <div className="flex gap-3">
                    <Button type="submit" disabled={reviewSubmitting}>
                      {reviewSubmitting
                        ? "Сохранение..."
                        : myReview
                        ? "Сохранить изменения"
                        : "Опубликовать рецензию"}
                    </Button>
                    <Button
                      variant="ghost"
                      type="button"
                      disabled={reviewSubmitting}
                      onClick={() => setReviewFormOpen(false)}
                    >
                      Отмена
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Список публичных рецензий */}
      <section className="mt-10">
        <h2 className="text-2xl font-bold text-shelf-900">
          Рецензии {reviews.length > 0 && `(${reviews.length})`}
        </h2>

        {reviewsLoading ? (
          <p className="mt-4 text-sm text-shelf-500">Загрузка рецензий...</p>
        ) : reviews.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-shelf-300 p-8 text-center text-sm text-shelf-500">
            Пока нет рецензий. Будьте первым!
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {reviews.map((r) => {
              const isMine = user && r.user_login.toLowerCase() === user.login.toLowerCase();
              return (
                <article
                  key={r.id}
                  className="rounded-2xl bg-white p-6 ring-1 ring-shelf-200 transition-shadow hover:shadow-sm"
                >
                  <header className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <Link to={`/u/${r.user_login}`} className="flex items-center gap-2 group">
                        <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-shelf-100 ring-1 ring-shelf-200">
                          {r.user_avatar_url ? (
                            <img
                              src={r.user_avatar_url}
                              alt=""
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <span className="text-sm font-semibold uppercase text-shelf-600">
                              {r.user_login.slice(0, 2)}
                            </span>
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-shelf-900 group-hover:text-accent-600">
                            {r.user_login}
                          </p>
                          <p className="text-xs text-shelf-500">{formatDate(r.created_at)}</p>
                        </div>
                      </Link>
                    </div>

                    <div className="flex items-center gap-3">
                      {r.rating && (
                        <span className="rounded-lg bg-accent-50 px-2 py-0.5 text-xs font-bold text-accent-700">
                          ★ {r.rating} / 10
                        </span>
                      )}
                      {user && !isMine && (
                        <button
                          type="button"
                          onClick={() => handleOpenReport("review", r.id, r.title)}
                          className="text-xs text-shelf-400 hover:text-red-600"
                        >
                          Пожаловаться
                        </button>
                      )}
                      {isMine && (
                        <span className="rounded bg-shelf-100 px-2 py-0.5 text-xs text-shelf-600">
                          Ваша рецензия
                        </span>
                      )}
                    </div>
                  </header>

                  <h3 className="mt-4 font-semibold text-shelf-900">{r.title}</h3>
                  <p className="mt-2 whitespace-pre-line text-sm text-shelf-700">{r.body}</p>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Модальное окно жалобы */}
      {reportTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-shelf-900">
              Пожаловаться на {reportTarget.type === "item" ? "карточку" : "рецензию"}
            </h3>
            {reportTarget.title && (
              <p className="mt-1 line-clamp-1 text-xs text-shelf-500">«{reportTarget.title}»</p>
            )}

            {reportMessage ? (
              <div className="mt-4 rounded-xl bg-emerald-50 p-4 text-center text-sm font-medium text-emerald-800">
                {reportMessage}
              </div>
            ) : (
              <form onSubmit={handleSubmitReport} className="mt-4 space-y-4">
                {reportError && (
                  <div className="rounded-xl bg-red-50 p-3 text-xs text-red-700">
                    {reportError}
                  </div>
                )}

                <div>
                  <label htmlFor="report-reason-select" className="mb-1 block text-sm font-medium text-shelf-800">
                    Причина жалобы
                  </label>
                  <select
                    id="report-reason-select"
                    value={reportReason}
                    onChange={(e) =>
                      setReportReason(e.target.value as ReportCreatePayload["reason"])
                    }
                    className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                  >
                    {Object.entries(REPORT_REASON_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor={reportCommentId} className="mb-1 block text-sm font-medium text-shelf-800">
                    Комментарий (необязательно)
                  </label>
                  <textarea
                    id={reportCommentId}
                    rows={3}
                    maxLength={1000}
                    value={reportComment}
                    onChange={(e) => setReportComment(e.target.value)}
                    placeholder="Опишите подробности нарушения..."
                    className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    variant="ghost"
                    type="button"
                    disabled={reportSubmitting}
                    onClick={() => setReportTarget(null)}
                  >
                    Отмена
                  </Button>
                  <Button type="submit" disabled={reportSubmitting}>
                    {reportSubmitting ? "Отправка..." : "Отправить"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
