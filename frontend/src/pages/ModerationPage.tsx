import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Button from "@/components/ui/Button";
import { moderationApi } from "@/features/moderation/api";
import { ITEM_TYPE_LABELS, REPORT_REASON_LABELS } from "@/lib/constants";
import type { ModerationCard, Report } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

type Tab = "open" | "resolved" | "cards";
type Decision = "reject" | "hide" | "delete";

const TARGET_LABELS: Record<string, string> = {
  review: "Рецензия",
  card: "Карточка",
  profile: "Профиль",
  comment: "Комментарий",
};

const DECISION_LABELS: Record<string, string> = {
  hide: "Материал скрыт",
  delete: "Материал удалён",
  reject: "Жалоба отклонена",
};

const DECISION_META: Record<
  Decision,
  { label: string; confirm: string; consequence: string; reasonRequired: boolean }
> = {
  reject: {
    label: "Отклонить",
    confirm: "Отклонить жалобу",
    consequence: "Материал останется на месте, жалоба закроется.",
    reasonRequired: false,
  },
  hide: {
    label: "Скрыть",
    confirm: "Скрыть материал",
    consequence: "Материал пропадёт из карточек и профилей, но останется в базе.",
    reasonRequired: true,
  },
  delete: {
    label: "Удалить",
    confirm: "Удалить материал",
    consequence:
      "Материал и связанные с ним данные будут удалены без возможности восстановления.",
    reasonRequired: true,
  },
};

function targetLink(report: Report): string | null {
  if (report.target_type === "card") return `/catalog/${report.target_id}`;
  if (report.target_type === "profile" && report.target_author) return `/u/${report.target_author}`;
  return null;
}

/** Панель подтверждения: решение нельзя применить без явного шага и причины. */
function ConfirmPanel({
  title,
  consequence,
  reasonRequired,
  confirmLabel,
  busy,
  danger,
  onConfirm,
  onCancel,
}: {
  title: string;
  consequence: string;
  reasonRequired: boolean;
  confirmLabel: string;
  busy: boolean;
  danger?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  const missing = reasonRequired && reason.trim().length === 0;

  return (
    <div className="mt-4 rounded-xl border border-shelf-200 bg-shelf-50 p-4">
      <p className="text-sm font-semibold text-shelf-900">{title}</p>
      <p className="mt-1 text-xs text-shelf-600">{consequence}</p>
      <label className="mt-3 block text-xs font-medium text-shelf-800">
        Причина {reasonRequired ? "(обязательно)" : "(необязательно)"}
        <input
          type="text"
          value={reason}
          maxLength={1000}
          onChange={(event) => setReason(event.target.value)}
          aria-invalid={missing}
          className="mt-1 w-full rounded-xl border border-shelf-300 bg-white px-3 py-1.5 text-sm"
        />
      </label>
      <div className="mt-3 flex gap-2">
        <Button
          disabled={busy || missing}
          onClick={() => onConfirm(reason.trim())}
          className={danger ? "bg-red-600 hover:bg-red-700" : undefined}
        >
          {busy ? "Применяем…" : confirmLabel}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </div>
  );
}

function ReportCard({ report, onDone }: { report: Report; onDone: () => void }) {
  const [pending, setPending] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const link = targetLink(report);

  async function apply(decision: Decision, reason: string) {
    setBusy(true);
    setError(null);
    try {
      await moderationApi.resolveReport(report.id, { decision, reason: reason || null });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось применить решение");
      setBusy(false);
    }
  }

  return (
    <article className="rounded-2xl bg-white p-5 ring-1 ring-shelf-200">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-lg bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
            {REPORT_REASON_LABELS[report.reason as keyof typeof REPORT_REASON_LABELS] ?? report.reason}
          </span>
          <span className="rounded-lg bg-shelf-100 px-2.5 py-1 text-xs font-medium text-shelf-700">
            {TARGET_LABELS[report.target_type] ?? report.target_type}
          </span>
        </div>
        <span className="text-xs text-shelf-500">{formatDate(report.created_at)}</span>
      </div>

      <div className="mt-3 rounded-xl bg-shelf-50 p-3 text-sm">
        <p className="font-medium text-shelf-900">
          {report.target_title ?? "Материал уже удалён"}
          {link ? (
            <Link to={link} className="ml-2 text-xs font-normal text-accent-600 hover:underline">
              открыть →
            </Link>
          ) : null}
        </p>
        {report.target_author ? (
          <p className="mt-0.5 text-xs text-shelf-600">Автор: @{report.target_author}</p>
        ) : null}
      </div>

      <p className="mt-3 text-sm text-shelf-700">
        <span className="text-shelf-500">Пожаловался:</span>{" "}
        <span className="font-medium text-shelf-900">@{report.reporter_login}</span>
      </p>
      {report.comment ? (
        <p className="mt-2 rounded-xl bg-shelf-50 p-3 text-xs text-shelf-800">
          <span className="font-semibold text-shelf-600">Пояснение:</span> {report.comment}
        </p>
      ) : null}

      {error ? (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {report.status === "open" ? (
        pending ? (
          <ConfirmPanel
            title={DECISION_META[pending].confirm}
            consequence={DECISION_META[pending].consequence}
            reasonRequired={DECISION_META[pending].reasonRequired}
            confirmLabel={DECISION_META[pending].confirm}
            danger={pending === "delete"}
            busy={busy}
            onConfirm={(reason) => void apply(pending, reason)}
            onCancel={() => setPending(null)}
          />
        ) : (
          <div className="mt-4 flex flex-wrap gap-2 border-t border-shelf-100 pt-4">
            <Button variant="ghost" onClick={() => setPending("reject")}>
              Отклонить
            </Button>
            <Button
              variant="secondary"
              onClick={() => setPending("hide")}
              disabled={report.target_type === "profile" || !report.target_title}
            >
              Скрыть
            </Button>
            <Button
              variant="secondary"
              className="text-red-700"
              onClick={() => setPending("delete")}
              disabled={report.target_type === "profile" || !report.target_title}
            >
              Удалить
            </Button>
          </div>
        )
      ) : (
        <div className="mt-4 border-t border-shelf-100 pt-3 text-xs text-shelf-600">
          <p>
            <span className="font-semibold text-shelf-800">Решение:</span>{" "}
            {DECISION_LABELS[report.resolution ?? ""] ?? report.resolution}
          </p>
          {report.resolution_reason ? (
            <p className="mt-1">
              <span className="font-semibold text-shelf-800">Причина:</span> {report.resolution_reason}
            </p>
          ) : null}
        </div>
      )}
    </article>
  );
}

function CardQueueItem({ card, onDone }: { card: ModerationCard; onDone: () => void }) {
  const [mode, setMode] = useState<"approve" | "reject" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось применить решение");
      setBusy(false);
    }
  }

  return (
    <article className="flex flex-col gap-4 rounded-2xl bg-white p-5 ring-1 ring-shelf-200 sm:flex-row">
      {card.poster_url ? (
        <img
          src={card.poster_url}
          alt={`Обложка: ${card.title}`}
          className="h-40 w-28 shrink-0 rounded-xl object-cover"
        />
      ) : (
        <span className="flex h-40 w-28 shrink-0 items-center justify-center rounded-xl bg-shelf-100 text-xs text-shelf-500">
          Нет обложки
        </span>
      )}
      <div className="min-w-0 flex-1">
        <h3 className="text-lg font-semibold text-shelf-900">{card.title}</h3>
        <p className="mt-1 text-sm text-shelf-600">
          {ITEM_TYPE_LABELS[card.type]}
          {card.year ? ` · ${card.year}` : ""}
          {card.country ? ` · ${card.country}` : ""}
          {card.genres.length ? ` · ${card.genres.join(", ")}` : ""}
        </p>
        <p className="mt-1 text-xs text-shelf-500">
          Автор: {card.author_login ? `@${card.author_login}` : "не указан"}
        </p>
        {card.description ? (
          <p className="mt-3 line-clamp-4 whitespace-pre-line text-sm text-shelf-800">
            {card.description}
          </p>
        ) : null}

        {error ? (
          <p className="mt-3 text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : null}

        {mode === "reject" ? (
          <ConfirmPanel
            title="Отклонить карточку"
            consequence="Карточка станет недоступна другим пользователям. Автор её не увидит в каталоге."
            reasonRequired
            confirmLabel="Отклонить карточку"
            danger
            busy={busy}
            onConfirm={(reason) => void run(() => moderationApi.rejectCard(card.id, reason))}
            onCancel={() => setMode(null)}
          />
        ) : mode === "approve" ? (
          <ConfirmPanel
            title="Подтвердить карточку"
            consequence="Карточка появится в общем каталоге и станет видна гостям."
            reasonRequired={false}
            confirmLabel="Подтвердить"
            busy={busy}
            onConfirm={() => void run(() => moderationApi.approveCard(card.id))}
            onCancel={() => setMode(null)}
          />
        ) : (
          <div className="mt-4 flex gap-2">
            <Button onClick={() => setMode("approve")}>Одобрить</Button>
            <Button variant="secondary" className="text-red-700" onClick={() => setMode("reject")}>
              Отклонить
            </Button>
          </div>
        )}
      </div>
    </article>
  );
}

export default function ModerationPage() {
  const [tab, setTab] = useState<Tab>("open");
  const [reports, setReports] = useState<Report[]>([]);
  const [cards, setCards] = useState<ModerationCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const load =
      tab === "cards"
        ? moderationApi.pendingCards(controller.signal).then(setCards)
        : moderationApi
            .listReports({ status: tab === "open" ? "open" : undefined }, controller.signal)
            .then((list) => setReports(tab === "open" ? list : list.filter((r) => r.status !== "open")));

    load
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить очередь");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tab, reloadKey]);

  const TABS: { key: Tab; label: string }[] = [
    { key: "open", label: "Открытые жалобы" },
    { key: "resolved", label: "Решённые" },
    { key: "cards", label: "Карточки на проверке" },
  ];

  const empty =
    !loading && !error && (tab === "cards" ? cards.length === 0 : reports.length === 0);

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-shelf-900">Модерация</h1>
      <p className="mt-1 text-shelf-600">
        Жалобы пользователей и локальные карточки, которые ждут проверки.
      </p>

      <div className="mt-8 flex flex-wrap gap-2 border-b border-shelf-200 pb-4">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            aria-pressed={tab === item.key}
            className={cn(
              "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
              tab === item.key
                ? "bg-accent-600 text-white shadow-sm"
                : "bg-white text-shelf-700 ring-1 ring-shelf-200 hover:bg-shelf-100",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-center" role="alert">
          <p className="font-medium text-red-800">Ошибка загрузки</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
          <Button className="mt-4" onClick={reload}>
            Повторить
          </Button>
        </div>
      ) : null}

      {loading && !error ? (
        <p className="mt-12 text-center text-sm text-shelf-500" role="status">
          Загружаем…
        </p>
      ) : null}

      {empty ? (
        <div className="mt-10 rounded-2xl border border-dashed border-shelf-300 p-12 text-center">
          <p className="text-lg font-medium text-shelf-900">
            {tab === "cards"
              ? "Нет карточек на проверке"
              : tab === "open"
                ? "Нет открытых жалоб"
                : "Решённых жалоб пока нет"}
          </p>
        </div>
      ) : null}

      {!loading && !error && tab !== "cards" && reports.length > 0 ? (
        <div className="mt-8 space-y-4">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} onDone={reload} />
          ))}
        </div>
      ) : null}

      {!loading && !error && tab === "cards" && cards.length > 0 ? (
        <div className="mt-8 space-y-4">
          {cards.map((card) => (
            <CardQueueItem key={card.id} card={card} onDone={reload} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
