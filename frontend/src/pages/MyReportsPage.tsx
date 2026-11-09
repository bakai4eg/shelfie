import { useEffect, useState } from "react";

import { moderationApi } from "@/features/moderation/api";
import { REPORT_REASON_LABELS } from "@/lib/constants";
import type { Report } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const TARGETS: Record<string, string> = {
  review: "Рецензия",
  card: "Карточка",
  profile: "Профиль",
  comment: "Комментарий",
};

const STATUS_META: Record<string, { label: string; className: string }> = {
  open: { label: "На рассмотрении", className: "bg-amber-50 text-amber-800 ring-amber-200" },
  resolved: { label: "Принято решение", className: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  closed: { label: "Отклонена", className: "bg-shelf-100 text-shelf-700 ring-shelf-200" },
};

const RESOLUTIONS: Record<string, string> = {
  hide: "Материал скрыт",
  delete: "Материал удалён",
  reject: "Жалоба отклонена",
};

export default function MyReportsPage() {
  const [reports, setReports] = useState<Report[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    moderationApi
      .myReports(controller.signal)
      .then(setReports)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить жалобы");
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-shelf-900">Мои жалобы</h1>
      <p className="mt-1 text-shelf-600">Что вы отправляли модераторам и чем это закончилось.</p>

      {error ? (
        <p className="mt-8 text-red-700" role="alert">
          {error}
        </p>
      ) : reports === null ? (
        <p className="mt-8 text-sm text-shelf-500" role="status">
          Загружаем…
        </p>
      ) : reports.length === 0 ? (
        <p className="mt-8 text-shelf-600">Вы пока не отправляли жалоб.</p>
      ) : (
        <ul className="mt-8 space-y-3">
          {reports.map((report) => {
            const meta = STATUS_META[report.status] ?? STATUS_META.open;
            return (
              <li key={report.id} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-shelf-900">
                    {TARGETS[report.target_type] ?? report.target_type}
                    {report.target_title ? `: «${report.target_title}»` : " (удалён)"}
                  </p>
                  <span className={cn("rounded-lg px-2.5 py-1 text-xs font-medium ring-1", meta.className)}>
                    {meta.label}
                  </span>
                </div>
                <p className="mt-1 text-sm text-shelf-600">
                  {REPORT_REASON_LABELS[report.reason as keyof typeof REPORT_REASON_LABELS] ?? report.reason}
                  {" · "}
                  {formatDate(report.created_at)}
                </p>
                {report.comment ? <p className="mt-2 text-sm text-shelf-800">{report.comment}</p> : null}
                {report.resolution ? (
                  <p className="mt-2 text-xs text-shelf-600">
                    <span className="font-semibold">{RESOLUTIONS[report.resolution] ?? report.resolution}</span>
                    {report.resolution_reason ? `. ${report.resolution_reason}` : ""}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
