import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import LikeButton from "@/components/LikeButton";
import ReportDialog, { type ReportTarget } from "@/components/ReportDialog";
import Button from "@/components/ui/Button";
import { useAuth } from "@/features/auth/context";
import { engagementApi, reviewsApi } from "@/features/reviews/api";
import { ApiError } from "@/lib/api";
import { COMMENT_MAX_LENGTH, ROLE_LEVEL } from "@/lib/constants";
import type { CommentItem, Page, Review } from "@/lib/types";
import { formatDate } from "@/lib/utils";

const PAGE_SIZE = 20;

function Avatar({ login, url }: { login: string; url: string | null }) {
  return url ? (
    <img src={url} alt="" className="h-8 w-8 rounded-full object-cover" />
  ) : (
    <span
      className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-600 text-xs font-semibold text-white"
      aria-hidden
    >
      {login.slice(0, 1).toUpperCase()}
    </span>
  );
}

export default function ReviewPage() {
  const { reviewId } = useParams();
  const id = Number(reviewId);
  const { user } = useAuth();

  const [review, setReview] = useState<Review | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [comments, setComments] = useState<Page<CommentItem> | null>(null);
  const [commentPage, setCommentPage] = useState(1);
  const [commentsError, setCommentsError] = useState<string | null>(null);

  const [body, setBody] = useState("");
  const [posting, setPosting] = useState(false);
  const [postError, setPostError] = useState<string | null>(null);
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) {
      setNotFound(true);
      return;
    }
    const controller = new AbortController();
    setReview(null);
    setNotFound(false);
    setError(null);
    reviewsApi
      .get(id, controller.signal)
      .then(setReview)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
        else setError(err instanceof Error ? err.message : "Не удалось загрузить рецензию");
      });
    return () => controller.abort();
  }, [id]);

  const loadComments = useCallback(
    (page: number, signal?: AbortSignal) =>
      engagementApi
        .comments(id, page, PAGE_SIZE, signal)
        .then(setComments)
        .catch((err: unknown) => {
          if (err instanceof Error && err.name === "AbortError") return;
          setCommentsError(err instanceof Error ? err.message : "Не удалось загрузить комментарии");
        }),
    [id],
  );

  useEffect(() => {
    if (!review) return;
    const controller = new AbortController();
    setCommentsError(null);
    void loadComments(commentPage, controller.signal);
    return () => controller.abort();
  }, [review, commentPage, loadComments]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = body.trim();
    if (!text) {
      setPostError("Напишите комментарий");
      return;
    }
    setPosting(true);
    setPostError(null);
    try {
      await engagementApi.addComment(id, text);
      setBody("");
      const lastPage = Math.max(1, Math.ceil(((comments?.total ?? 0) + 1) / PAGE_SIZE));
      if (lastPage === commentPage) await loadComments(commentPage);
      else setCommentPage(lastPage);
      setReview((current) =>
        current ? { ...current, comments_count: current.comments_count + 1 } : current,
      );
    } catch (err) {
      setPostError(err instanceof Error ? err.message : "Не удалось отправить комментарий");
    } finally {
      setPosting(false);
    }
  }

  async function remove(comment: CommentItem) {
    if (!window.confirm("Удалить комментарий?")) return;
    try {
      await engagementApi.deleteComment(comment.id);
      await loadComments(commentPage);
      setReview((current) =>
        current ? { ...current, comments_count: Math.max(0, current.comments_count - 1) } : current,
      );
    } catch (err) {
      setCommentsError(err instanceof Error ? err.message : "Не удалось удалить комментарий");
    }
  }

  if (notFound) {
    return (
      <section className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-2xl font-semibold text-shelf-900">Рецензия не найдена</h1>
        <p className="mt-2 text-shelf-700">Её могли удалить или скрыть модератор.</p>
        <Link to="/catalog" className="mt-6 inline-block font-medium text-accent-600">
          В каталог →
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
  if (!review) {
    return (
      <p className="mx-auto max-w-2xl px-4 py-16 text-sm text-shelf-500" role="status">
        Загружаем рецензию…
      </p>
    );
  }

  const isMine = user?.login.toLowerCase() === review.user_login.toLowerCase();
  const isModerator = user ? ROLE_LEVEL[user.role] >= ROLE_LEVEL.moderator : false;
  const total = comments?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <Link to={`/catalog/${review.item_id}`} className="text-sm text-shelf-600 hover:text-accent-700">
        ← {review.item_title ?? "К карточке"}
      </Link>

      <article className="mt-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200">
        {review.is_hidden ? (
          <p className="mb-4 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Рецензия скрыта модератором. Её видите только вы и модераторы.
          </p>
        ) : null}
        <header className="flex flex-wrap items-center justify-between gap-3">
          <Link to={`/u/${review.user_login}`} className="flex items-center gap-2 font-medium text-shelf-900">
            <Avatar login={review.user_login} url={review.user_avatar_url} />@{review.user_login}
          </Link>
          <div className="flex items-center gap-3 text-sm text-shelf-500">
            {review.rating ? <span>★ {review.rating} / 10</span> : null}
            <span>{formatDate(review.created_at)}</span>
          </div>
        </header>
        <h1 className="mt-4 text-2xl font-semibold text-shelf-900">{review.title}</h1>
        <p className="mt-3 whitespace-pre-line break-words text-shelf-800">{review.body}</p>

        <footer className="mt-5 flex flex-wrap items-center gap-3 border-t border-shelf-100 pt-4">
          {review.is_hidden ? (
            <span className="text-sm text-shelf-500">♡ {review.likes_count}</span>
          ) : (
            <LikeButton
              targetType="review"
              targetId={review.id}
              count={review.likes_count}
              liked={review.liked_by_me}
            />
          )}
          <span className="text-sm text-shelf-500">Комментариев: {review.comments_count}</span>
          {user && !isMine ? (
            <button
              type="button"
              onClick={() => setReportTarget({ type: "review", id: review.id, title: review.title })}
              className="ml-auto text-xs text-shelf-400 hover:text-red-600"
            >
              Пожаловаться
            </button>
          ) : null}
        </footer>
      </article>

      <section className="mt-8" aria-labelledby="comments-title">
        <h2 id="comments-title" className="text-xl font-semibold text-shelf-900">
          Комментарии
        </h2>

        {review.is_hidden ? (
          <p className="mt-3 text-sm text-shelf-500">У скрытой рецензии комментарии недоступны.</p>
        ) : user ? (
          <form onSubmit={(event) => void submit(event)} className="mt-4">
            <label htmlFor="new-comment" className="sr-only">
              Ваш комментарий
            </label>
            <textarea
              id="new-comment"
              value={body}
              rows={3}
              onChange={(event) => setBody(event.target.value)}
              aria-invalid={body.length > COMMENT_MAX_LENGTH}
              placeholder="Поделитесь мнением о рецензии"
              className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:outline-offset-2 focus:outline-accent-600"
            />
            <div className="mt-1 flex items-center justify-between">
              <span
                className={
                  body.length > COMMENT_MAX_LENGTH ? "text-xs font-medium text-red-600" : "text-xs text-shelf-500"
                }
              >
                {body.length} / {COMMENT_MAX_LENGTH}
              </span>
              <Button type="submit" disabled={posting || body.length > COMMENT_MAX_LENGTH}>
                {posting ? "Отправляем…" : "Отправить"}
              </Button>
            </div>
            {postError ? (
              <p className="mt-2 text-sm text-red-700" role="alert">
                {postError}
              </p>
            ) : null}
          </form>
        ) : (
          <p className="mt-4 rounded-xl bg-shelf-100 px-4 py-3 text-sm text-shelf-700">
            <Link to={`/login?next=${encodeURIComponent(`/reviews/${id}`)}`} className="font-medium text-accent-600">
              Войдите
            </Link>
            , чтобы оставить комментарий.
          </p>
        )}

        {commentsError ? (
          <p className="mt-4 text-sm text-red-700" role="alert">
            {commentsError}
          </p>
        ) : null}

        {!review.is_hidden && comments && comments.items.length === 0 ? (
          <p className="mt-6 text-shelf-600">Комментариев пока нет. Будьте первым.</p>
        ) : null}

        <ul className="mt-6 space-y-3">
          {comments?.items.map((comment) => {
            const own = user?.login.toLowerCase() === comment.user_login.toLowerCase();
            return (
              <li key={comment.id} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
                <div className="flex items-center justify-between gap-2">
                  <Link to={`/u/${comment.user_login}`} className="flex items-center gap-2 text-sm font-medium text-shelf-900">
                    <Avatar login={comment.user_login} url={comment.user_avatar_url} />@{comment.user_login}
                  </Link>
                  <span className="text-xs text-shelf-500">{formatDate(comment.created_at)}</span>
                </div>
                <p className="mt-2 whitespace-pre-line break-words text-sm text-shelf-800">{comment.body}</p>
                <div className="mt-3 flex items-center gap-3">
                  <LikeButton
                    targetType="comment"
                    targetId={comment.id}
                    count={comment.likes_count}
                    liked={comment.liked_by_me}
                  />
                  {own || isModerator ? (
                    <button
                      type="button"
                      onClick={() => void remove(comment)}
                      className="text-xs text-red-700 hover:underline"
                    >
                      Удалить
                    </button>
                  ) : null}
                  {user && !own ? (
                    <button
                      type="button"
                      onClick={() =>
                        setReportTarget({ type: "comment", id: comment.id, title: comment.body.slice(0, 60) })
                      }
                      className="ml-auto text-xs text-shelf-400 hover:text-red-600"
                    >
                      Пожаловаться
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>

        {lastPage > 1 ? (
          <div className="mt-4 flex items-center justify-between text-sm text-shelf-600">
            <Button variant="secondary" disabled={commentPage <= 1} onClick={() => setCommentPage((p) => p - 1)}>
              ←
            </Button>
            <span>
              {commentPage} / {lastPage}
            </span>
            <Button variant="secondary" disabled={commentPage >= lastPage} onClick={() => setCommentPage((p) => p + 1)}>
              →
            </Button>
          </div>
        ) : null}
      </section>

      {reportTarget ? <ReportDialog target={reportTarget} onClose={() => setReportTarget(null)} /> : null}
    </section>
  );
}
