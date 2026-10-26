import { Link } from "react-router-dom";

import { buttonClass } from "@/lib/ui";

export default function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-6xl font-semibold text-shelf-300">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-shelf-900">Такой страницы нет</h1>
      <p className="mt-2 text-shelf-700">
        Возможно, ссылка устарела или карточку скрыли. Попробуйте начать с каталога.
      </p>
      <Link to="/catalog" className={buttonClass("primary", "mt-6 px-5 py-2.5")}>
        В каталог
      </Link>
    </section>
  );
}
