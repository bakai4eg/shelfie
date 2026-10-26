import type { ReactNode } from "react";

import { TASK_URL } from "@/lib/constants";

interface ComingSoonProps {
  /** ID задачи из tasks/board.md — по нему открывается карточка на GitHub. */
  task: string;
  title: string;
  children?: ReactNode;
}

/**
 * Заглушка страницы: маршрут уже существует, экран не пустой,
 * и сразу видно, какая задача его наполняет.
 */
export default function ComingSoon({ task, title, children }: ComingSoonProps) {
  return (
    <section className="mx-auto max-w-2xl px-4 py-16">
      <p className="text-xs font-medium uppercase tracking-wider text-shelf-500">В разработке</p>
      <h1 className="mt-2 text-3xl font-semibold text-shelf-900">{title}</h1>
      <div className="mt-4 space-y-3 text-shelf-700">
        {children ?? <p>Экран появится в следующем этапе проекта.</p>}
      </div>
      <a
        href={TASK_URL(task)}
        target="_blank"
        rel="noreferrer"
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-shelf-900 px-4 py-2 text-sm font-medium text-shelf-50 transition-colors hover:bg-shelf-800"
      >
        Задача {task}
        <span aria-hidden>→</span>
      </a>
    </section>
  );
}
