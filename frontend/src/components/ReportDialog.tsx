import { useEffect, useId, useState, type FormEvent } from "react";

import Button from "@/components/ui/Button";
import { moderationApi, type ReportCreatePayload } from "@/features/moderation/api";
import { REPORT_REASON_LABELS } from "@/lib/constants";

export interface ReportTarget {
  type: ReportCreatePayload["target_type"];
  id: number;
  title?: string;
}

const TYPE_LABELS: Record<ReportTarget["type"], string> = {
  review: "рецензию",
  card: "карточку",
  profile: "профиль",
  comment: "комментарий",
};

const COMMENT_MAX = 1000;

/** Модалка «Пожаловаться» для рецензий, карточек и профилей (ТЗ 4.6.2). */
export default function ReportDialog({
  target,
  onClose,
}: {
  target: ReportTarget;
  onClose: () => void;
}) {
  const commentId = useId();
  const [reason, setReason] = useState<ReportCreatePayload["reason"]>("spam");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsComment = reason === "other";
  const missingComment = needsComment && comment.trim().length === 0;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (missingComment) {
      setError("Для причины «Иное» опишите, что не так");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await moderationApi.createReport({
        target_type: target.type,
        target_id: target.id,
        reason,
        comment: comment.trim() || null,
      });
      setDone(true);
      window.setTimeout(onClose, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить жалобу");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Жалоба"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-shelf-900">
          Пожаловаться на {TYPE_LABELS[target.type]}
        </h3>
        {target.title ? (
          <p className="mt-1 line-clamp-1 text-xs text-shelf-500">«{target.title}»</p>
        ) : null}

        {done ? (
          <div className="mt-4 rounded-xl bg-emerald-50 p-4 text-center text-sm font-medium text-emerald-800">
            Жалоба отправлена модераторам
          </div>
        ) : (
          <form onSubmit={(event) => void submit(event)} className="mt-4 space-y-4">
            {error ? (
              <div className="rounded-xl bg-red-50 p-3 text-xs text-red-700" role="alert">
                {error}
              </div>
            ) : null}

            <div>
              <label htmlFor="report-reason" className="mb-1 block text-sm font-medium text-shelf-800">
                Причина жалобы
              </label>
              <select
                id="report-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value as ReportCreatePayload["reason"])}
                className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900"
              >
                {Object.entries(REPORT_REASON_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={commentId} className="mb-1 block text-sm font-medium text-shelf-800">
                Пояснение {needsComment ? "(обязательно)" : "(необязательно)"}
              </label>
              <textarea
                id={commentId}
                rows={3}
                maxLength={COMMENT_MAX}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                aria-invalid={missingComment}
                placeholder="Опишите, что именно нарушено"
                className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900"
              />
              <p className="mt-1 text-right text-xs text-shelf-500">
                {comment.length} / {COMMENT_MAX}
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="ghost" disabled={submitting} onClick={onClose}>
                Отмена
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Отправка…" : "Отправить"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
