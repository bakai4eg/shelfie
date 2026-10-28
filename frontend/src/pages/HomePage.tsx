import { Link } from "react-router-dom";

import { useAuth } from "@/features/auth/context";
import { buttonClass } from "@/lib/ui";

const FEATURES = [
  {
    title: "Один учёт вместо трёх сервисов",
    text: "Книги, фильмы и сериалы на одной полке: статусы, оценки, рецензии и статистика в одном профиле.",
  },
  {
    title: "Кыргызский контент — не сноска",
    text: "Локальные карточки кыргызских фильмов и книг, которые сообщество добавляет под присмотром модераторов.",
  },
  {
    title: "Витрины с характером",
    text: "Публичные подборки с личными заметками и темами оформления — не просто список, а вещь, которой хочется поделиться.",
  },
];

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div>
      <section className="mx-auto max-w-6xl px-4 pb-14 pt-16 sm:pt-24">
        <p className="text-xs font-medium uppercase tracking-widest text-accent-600">
          Книги · Фильмы · Сериалы
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-shelf-900 sm:text-5xl">
          Полка для книг, фильмов и сериалов — и люди, с которыми интересно смотреть.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-shelf-700">
          Shelfie объединяет учёт медиа-контента, рецензии и социальную ленту. Отмечайте, что читаете и
          смотрите, ставьте оценки, собирайте оформленные подборки и находите кыргызские фильмы и книги,
          которых нет в больших каталогах.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/catalog" className={buttonClass("primary", "px-5 py-2.5")}>
            Открыть каталог
          </Link>
          {user ? (
            <Link to={`/u/${user.login}`} className={buttonClass("secondary", "px-5 py-2.5")}>
              Мой профиль
            </Link>
          ) : (
            <Link to="/register" className={buttonClass("secondary", "px-5 py-2.5")}>
              Создать аккаунт
            </Link>
          )}
        </div>
      </section>

      <section className="border-y border-shelf-200 bg-white/60">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-12 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="rounded-2xl bg-shelf-50 p-6 ring-1 ring-shelf-200">
              <h2 className="text-base font-semibold text-shelf-900">{feature.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-shelf-700">{feature.text}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
