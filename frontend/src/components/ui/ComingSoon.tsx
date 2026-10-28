import { Link } from "react-router-dom";

import { buttonClass } from "@/lib/ui";

interface ComingSoonProps {
  title: string;
  description?: string;
}

export default function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <section className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent-600">
        Shelfie
      </p>
      <h1 className="mt-3 text-3xl font-semibold text-shelf-900">{title}</h1>
      <p className="mt-3 text-shelf-700">
        {description ?? "Этот раздел пока недоступен."}
      </p>
      <Link to="/catalog" className={buttonClass("primary", "mt-8 px-5 py-2.5")}>
        В каталог
      </Link>
    </section>
  );
}
