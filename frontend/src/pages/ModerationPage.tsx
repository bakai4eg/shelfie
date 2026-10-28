import { useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import { moderationApi, type ReportResolvePayload } from "@/features/moderation/api";
import { REPORT_REASON_LABELS } from "@/lib/constants";
import type { Report } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const TARGET_TYPE_LABELS: Record<string, string> = {
  review: "Рецензия",
  item: "Карточка каталога",
  user: "Пользователь",
};

const DECISION_LABELS: Record<string, string> = {
  hidden: "Объект скрыт",
  deleted: "Объект удалён",
  rejected: "Жалоба отклонена",
};

export default function ModerationPage() {
  const [activeTab, setActiveTab] = useState<"open" | "resolved">("open");
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Резолюция в процессе
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolutionReasons, setResolutionReasons] = useState<Record<number, string>>({});

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    moderationApi
      .listReports({ status: activeTab }, controller.signal)
      .then(setReports)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить жалобы");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [activeTab, reloadKey]);

  const handleResolve = async (
    reportId: number,
    decision: ReportResolvePayload["decision"],
  ) => {
    setResolvingId(reportId);
    try {
      const reason = resolutionReasons[reportId]?.trim() || undefined;
      await moderationApi.resolveReport(reportId, { decision, reason });
      setReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось применить решение");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-shelf-900">Модерация</h1>
          <p className="mt-1 text-shelf-600">
            Очередь жалоб пользователей на материалы и поведение.
          </p>
        </div>
        {!loading && (
          <p className="text-sm text-shelf-500">
            {reports.length}{" "}
            {reports.length === 1
              ? "жалоба"
              : reports.length >= 2 && reports.length <= 4
              ? "жалобы"
              : "жалоб"}
          </p>
        )}
      </header>

      {/* Переключение вкладок */}
      <div className="mt-8 flex gap-2 border-b border-shelf-200 pb-4">
        <button
          type="button"
          onClick={() => setActiveTab("open")}
          className={cn(
            "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "open"
              ? "bg-accent-600 text-white shadow-sm"
              : "bg-white text-shelf-700 ring-1 ring-shelf-200 hover:bg-shelf-100",
          )}
        >
          Открытые жалобы
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("resolved")}
          className={cn(
            "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "resolved"
              ? "bg-accent-600 text-white shadow-sm"
              : "bg-white text-shelf-700 ring-1 ring-shelf-200 hover:bg-shelf-100",
          )}
        >
          Решённые
        </button>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-medium text-red-800">Ошибка загрузки</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
          <Button className="mt-4" onClick={() => setReloadKey((k) => k + 1)}>
            Повторить
          </Button>
        </div>
      )}

      {/* Загрузка */}
      {loading && !error && (
        <div className="mt-12 text-center text-sm text-shelf-500">Загрузка очереди жалоб...</div>
      )}

      {/* Пустое состояние */}
      {!loading && !error && reports.length === 0 && (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-12 text-center">
          <p className="text-lg font-medium text-shelf-900">
            {activeTab === "open" ? "Нет открытых жалоб" : "Нет решённых жалоб"}
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-shelf-600">
            {activeTab === "open"
              ? "Все поступившие жалобы успешно обработаны модераторами."
              : "В архиве пока нет обработанных жалоб."}
          </p>
        </div>
      )}

      {/* Список жалоб */}
      {!loading && !error && reports.length > 0 && (
        <div className="mt-8 space-y-4">
          {reports.map((report) => {
            const isResolving = resolvingId === report.id;
            const targetName = TARGET_TYPE_LABELS[report.target_type] ?? report.target_type;
            const reasonName =
              REPORT_REASON_LABELS[report.reason as keyof typeof REPORT_REASON_LABELS] ??
              report.reason;

            return (
              <article
                key={report.id}
                className="rounded-2xl bg-white p-6 ring-1 ring-shelf-200"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-lg bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
                      {reasonName}
                    </span>
                    <span className="rounded-lg bg-shelf-100 px-2.5 py-1 text-xs font-medium text-shelf-700">
                      Цель: {targetName} #{report.target_id}
                    </span>
                  </div>
                  <span className="text-xs text-shelf-500">{formatDate(report.created_at)}</span>
                </div>

                <div className="mt-3 text-sm text-shelf-700">
                  <p>
                    <span className="text-shelf-500">Заявитель:</span>{" "}
                    <span className="font-medium text-shelf-900">@{report.reporter_login}</span>
                  </p>
                  {report.comment && (
                    <div className="mt-2 rounded-xl bg-shelf-50 p-3 text-xs text-shelf-800">
                      <span className="font-semibold text-shelf-600">Комментарий заявителя:</span>{" "}
                      {report.comment}
                    </div>
                  )}
                </div>

                {report.status === "open" ? (
                  <div className="mt-5 space-y-3 border-t border-shelf-100 pt-4">
                    <input
                      type="text"
                      placeholder="Причина решения (необязательно)"
                      value={resolutionReasons[report.id] ?? ""}
                      onChange={(e) =>
                        setResolutionReasons({
                          ...resolutionReasons,
                          [report.id]: e.target.value,
                        })
                      }
                      className="w-full rounded-xl border border-shelf-300 px-3 py-1.5 text-xs text-shelf-900 placeholder:text-shelf-400 focus:border-accent-600 focus:outline-2 focus:outline-accent-600"
                    />

                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        disabled={isResolving}
                        onClick={() => handleResolve(report.id, "hidden")}
                      >
                        Скрыть объект
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={isResolving}
                        onClick={() => handleResolve(report.id, "deleted")}
                        className="text-red-600 hover:bg-red-50"
                      >
                        Удалить объект
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        disabled={isResolving}
                        onClick={() => handleResolve(report.id, "rejected")}
                      >
                        Отклонить жалобу
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 border-t border-shelf-100 pt-3 text-xs text-shelf-600">
                    <p>
                      <span className="font-semibold text-shelf-800">Решение:</span>{" "}
                      {DECISION_LABELS[report.resolution ?? ""] ?? report.resolution}
                    </p>
                    {report.resolution_reason && (
                      <p className="mt-1">
                        <span className="font-semibold text-shelf-800">Обоснование:</span>{" "}
                        {report.resolution_reason}
                      </p>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
