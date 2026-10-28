import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import { useAuth } from "@/features/auth/context";
import { profileApi } from "@/features/profile/api";
import { socialApi } from "@/features/social/api";
import { ApiError } from "@/lib/api";
import type { ListPreview, PublicProfile, ReviewPreview, UserStats } from "@/lib/types";
import { buttonClass } from "@/lib/ui";
import { formatDate } from "@/lib/utils";

const STATS: { key: keyof UserStats; label: string }[] = [
  { key: "books_read", label: "Книг прочитано" },
  { key: "movies_watched", label: "Фильмов просмотрено" },
  { key: "series_watched", label: "Сериалов просмотрено" },
  { key: "ratings_count", label: "Оценок" },
  { key: "rating_avg", label: "Средняя оценка" },
  { key: "reviews_count", label: "Рецензий" },
  { key: "followers", label: "Подписчиков" },
  { key: "following", label: "Подписок" },
];

function statValue(key: keyof UserStats, stats: UserStats): string {
  if (key === "rating_avg") {
    return stats.ratings_count > 0 ? stats.rating_avg.toFixed(1) : "—";
  }
  return String(stats[key]);
}

function EmptyState({ text }: { text: string }) {
  return (
    <p className="mt-3 rounded-2xl border border-dashed border-shelf-300 px-4 py-8 text-center text-sm text-shelf-600">
      {text}
    </p>
  );
}

function ProfileSkeleton() {
  return (
    <div className="animate-pulse space-y-6" aria-hidden>
      <div className="flex gap-5">
        <div className="h-24 w-24 rounded-full bg-shelf-200" />
        <div className="flex-1 space-y-3 pt-2">
          <div className="h-5 w-40 rounded bg-shelf-200" />
          <div className="h-4 w-56 rounded bg-shelf-100" />
          <div className="h-4 w-72 rounded bg-shelf-100" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="h-20 rounded-2xl bg-shelf-100" />
        ))}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { login = "" } = useParams();
  const { user } = useAuth();

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [reviews, setReviews] = useState<ReviewPreview[]>([]);
  const [lists, setLists] = useState<ListPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [followLoading, setFollowLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setNotFound(false);

    profileApi
      .get(login, controller.signal)
      .then(async (data) => {
        setProfile(data);
        const [reviewsPage, listsPage] = await Promise.all([
          profileApi.reviews(login, controller.signal).catch(() => null),
          profileApi.lists(login, controller.signal).catch(() => null),
        ]);
        setReviews(reviewsPage?.items ?? []);
        setLists(listsPage?.items ?? []);
      })
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name === "AbortError") {
          return;
        }
        if (reason instanceof ApiError && reason.status === 404) {
          setNotFound(true);
          return;
        }
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить профиль");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [login, reloadKey]);

  const handleToggleFollow = async () => {
    if (!profile || followLoading) return;
    setFollowLoading(true);
    try {
      if (profile.is_following) {
        const res = await socialApi.unfollow(profile.login);
        setProfile({
          ...profile,
          is_following: false,
          stats: {
            ...profile.stats,
            followers: res.followers,
          },
        });
      } else {
        const res = await socialApi.follow(profile.login);
        setProfile({
          ...profile,
          is_following: true,
          stats: {
            ...profile.stats,
            followers: res.followers,
          },
        });
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось изменить статус подписки");
    } finally {
      setFollowLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="mx-auto max-w-5xl px-4 py-10">
        <ProfileSkeleton />
      </section>
    );
  }

  if (notFound) {
    return (
      <section className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-3xl font-semibold text-shelf-900">Профиль не найден</h1>
        <p className="mt-2 text-shelf-700">
          Пользователя <span className="font-medium">@{login}</span> нет на Shelfie.
        </p>
        <Link to="/catalog" className={buttonClass("secondary", "mt-6")}>
          Открыть каталог
        </Link>
      </section>
    );
  }

  if (error || !profile) {
    return (
      <section className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-semibold text-shelf-900">Не удалось открыть профиль</h1>
        <p className="mt-2 text-sm text-shelf-600">{error ?? "Попробуйте ещё раз"}</p>
        <Button className="mt-6" onClick={() => setReloadKey((key) => key + 1)}>
          Повторить
        </Button>
      </section>
    );
  }

  const isOwn = user?.login.toLowerCase() === profile.login.toLowerCase();

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <header className="flex flex-col gap-6 sm:flex-row sm:items-start">
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={`Аватар @${profile.login}`}
            className="h-24 w-24 rounded-full object-cover ring-2 ring-shelf-200"
          />
        ) : (
          <div
            className="flex h-24 w-24 items-center justify-center rounded-full bg-accent-600 text-3xl font-semibold text-white"
            aria-hidden
          >
            {profile.login.slice(0, 1).toUpperCase()}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-3xl font-semibold text-shelf-900">@{profile.login}</h1>
            {isOwn ? (
              <Link to="/settings" className={buttonClass("secondary")}>
                Редактировать профиль
              </Link>
            ) : user ? (
              <Button
                variant={profile.is_following ? "secondary" : "primary"}
                disabled={followLoading}
                onClick={handleToggleFollow}
              >
                {followLoading
                  ? "Обновление..."
                  : profile.is_following
                  ? "Отписаться"
                  : "Подписаться"}
              </Button>
            ) : (
              <Link
                to={`/login?next=${encodeURIComponent(`/u/${profile.login}`)}`}
                className={buttonClass("primary")}
              >
                Подписаться
              </Link>
            )}
          </div>

          <p className="mt-1 text-sm text-shelf-500">
            На Shelfie с {formatDate(profile.registered_at)}
          </p>
          <p className="mt-3 max-w-2xl text-shelf-700">
            {profile.bio ?? "Пользователь пока ничего о себе не рассказал."}
          </p>
        </div>
      </header>

      <section className="mt-8" aria-labelledby="profile-stats">
        <h2 id="profile-stats" className="sr-only">
          Статистика
        </h2>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {STATS.map((item) => (
            <div key={item.key} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
              <dt className="text-xs font-medium uppercase tracking-wide text-shelf-500">
                {item.label}
              </dt>
              <dd className="mt-1 text-2xl font-semibold text-shelf-900">
                {statValue(item.key, profile.stats)}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-10" aria-labelledby="profile-reviews">
        <h2 id="profile-reviews" className="text-xl font-semibold text-shelf-900">
          Рецензии
        </h2>
        {reviews.length === 0 ? (
          <EmptyState text="Пока нет рецензий." />
        ) : (
          <ul className="mt-3 space-y-3">
            {reviews.map((review) => (
              <li key={review.id} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
                <p className="font-medium text-shelf-900">{review.title}</p>
                <p className="mt-1 text-sm text-shelf-500">
                  {review.rating !== null ? `Оценка ${review.rating}/10 · ` : ""}
                  {formatDate(review.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10" aria-labelledby="profile-lists">
        <h2 id="profile-lists" className="text-xl font-semibold text-shelf-900">
          Публичные списки
        </h2>
        {lists.length === 0 ? (
          <EmptyState text="Публичные списки пока не созданы." />
        ) : (
          <ul className="mt-3 grid gap-3 sm:grid-cols-2">
            {lists.map((list) => (
              <li key={list.id} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
                <p className="font-medium text-shelf-900">{list.title}</p>
                <p className="mt-1 text-sm text-shelf-500">Карточек: {list.items_count}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
