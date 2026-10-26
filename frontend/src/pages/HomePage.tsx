import { Link } from "react-router-dom";

import { buttonClass } from "@/lib/ui";
import { REPO_URL } from "@/lib/constants";

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
  return (
    <div>
      <section className="mx-auto max-w-6xl px-4 pb-14 pt-16 sm:pt-24">
        <p className="text-xs font-medium uppercase tracking-widest text-accent-600">
          ТКРПО · ПИ-1-24 · КГТУ им. И. Раззакова
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
          <a
            href={`${REPO_URL}/blob/main/docs/tz/tz.md`}
            target="_blank"
            rel="noreferrer"
            className={buttonClass("secondary", "px-5 py-2.5")}
          >
            Техническое задание
          </a>
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

      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="rounded-2xl border border-dashed border-shelf-300 p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-shelf-900">Проект в разработке</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-shelf-700">
            Каркас репозитория, документация и доска задач готовы. Экраны наполняются по этапам: от
            регистрации и профиля до модерации и ленты активности. Актуальный статус — на доске задач,
            архитектура и контракт API — в документации.
          </p>
          <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm font-medium">
            <a className="text-accent-600 hover:text-accent-700" href={`${REPO_URL}/blob/main/tasks/board.md`} target="_blank" rel="noreferrer">
              Доска задач →
            </a>
            <a className="text-accent-600 hover:text-accent-700" href={`${REPO_URL}/blob/main/docs/architecture.md`} target="_blank" rel="noreferrer">
              Архитектура →
            </a>
            <a className="text-accent-600 hover:text-accent-700" href={`${REPO_URL}/blob/main/docs/api.md`} target="_blank" rel="noreferrer">
              API →
            </a>
            <a className="text-accent-600 hover:text-accent-700" href={`${REPO_URL}/blob/main/CONTRIBUTING.md`} target="_blank" rel="noreferrer">
              Как запустить →
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
