import { useCallback, useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import { useAuth } from "@/features/auth/context";
import { adminApi } from "@/features/admin/api";
import { ROLE_LABELS } from "@/lib/constants";
import type { AdminSummary, AdminUser, AuditEntry, Page } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const PAGE_SIZE = 10;

const ACTION_LABELS: Record<string, string> = {
  "report.resolve": "Решение по жалобе",
  "content.hide": "Материал скрыт",
  "content.delete": "Материал удалён",
  "card.approve": "Карточка одобрена",
  "card.reject": "Карточка отклонена",
  "user.role": "Смена роли",
  "user.block": "Блокировка",
  "user.unblock": "Разблокировка",
  "user.delete": "Удаление пользователя",
};

const DETAIL_LABELS: Record<string, string> = {
  reason: "Причина",
  decision: "Решение",
  target: "Объект",
  title: "Название",
  login: "Логин",
  before: "Было",
  after: "Стало",
};

type Confirm =
  | { kind: "block" | "unblock" | "delete"; user: AdminUser }
  | { kind: "role"; user: AdminUser; role: "user" | "moderator" };

const CONFIRM_TEXT: Record<Confirm["kind"], (user: AdminUser) => string> = {
  block: (u) => `Заблокировать @${u.login}? Пользователь потеряет доступ и будет разлогинен на всех устройствах.`,
  unblock: (u) => `Разблокировать @${u.login}? Пользователь снова сможет войти.`,
  delete: (u) =>
    `Удалить @${u.login}? Будут удалены его рецензии, оценки, полки, списки, подписки, локальные карточки и загруженные файлы. Это нельзя отменить.`,
  role: (u) => `Изменить роль @${u.login}?`,
};

function SummaryCards({ summary }: { summary: AdminSummary | null }) {
  const items: [string, number | undefined][] = [
    ["Пользователей", summary?.users],
    ["Карточек", summary?.cards],
    ["Рецензий", summary?.reviews],
    ["Открытых жалоб", summary?.open_reports],
  ];
  return (
    <dl className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-2xl bg-white p-4 ring-1 ring-shelf-200">
          <dt className="text-sm text-shelf-600">{label}</dt>
          <dd className="mt-1 text-3xl font-semibold text-shelf-900">{value ?? "…"}</dd>
        </div>
      ))}
    </dl>
  );
}

function Pager({
  page,
  total,
  onPage,
}: {
  page: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const last = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="mt-3 flex items-center justify-between text-sm text-shelf-600">
      <span>Всего: {total}</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ←
        </Button>
        <span>
          {page} / {last}
        </span>
        <Button variant="secondary" disabled={page >= last} onClick={() => onPage(page + 1)}>
          →
        </Button>
      </div>
    </div>
  );
}

function UsersSection({ onChanged }: { onChanged: () => void }) {
  const { user: me } = useAuth();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [blocked, setBlocked] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<AdminUser> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    adminApi
      .users(
        {
          q: search,
          role: (role || undefined) as AdminUser["role"] | undefined,
          is_blocked: blocked === "" ? undefined : blocked === "yes",
          page,
          size: PAGE_SIZE,
        },
        controller.signal,
      )
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить пользователей");
      });
    return () => controller.abort();
  }, [search, role, blocked, page, reloadKey]);

  async function apply() {
    if (!confirm) return;
    setBusy(true);
    setError(null);
    try {
      if (confirm.kind === "block") await adminApi.block(confirm.user.id);
      else if (confirm.kind === "unblock") await adminApi.unblock(confirm.user.id);
      else if (confirm.kind === "delete") await adminApi.remove(confirm.user.id);
      else if (confirm.kind === "role") await adminApi.setRole(confirm.user.id, confirm.role);
      setConfirm(null);
      setReloadKey((key) => key + 1);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить действие");
      setConfirm(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-10" aria-labelledby="admin-users">
      <h2 id="admin-users" className="text-xl font-semibold text-shelf-900">
        Пользователи
      </h2>

      <form
        className="mt-3 flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setSearch(q.trim());
        }}
      >
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Логин или e-mail"
          aria-label="Поиск пользователей"
          className="min-w-0 flex-1 rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        />
        <select
          value={role}
          aria-label="Роль"
          onChange={(event) => {
            setPage(1);
            setRole(event.target.value);
          }}
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">Все роли</option>
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={blocked}
          aria-label="Блокировка"
          onChange={(event) => {
            setPage(1);
            setBlocked(event.target.value);
          }}
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">Любой статус</option>
          <option value="no">Активные</option>
          <option value="yes">Заблокированные</option>
        </select>
        <Button type="submit">Найти</Button>
      </form>

      {error ? (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-4 overflow-x-auto rounded-2xl bg-white ring-1 ring-shelf-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-shelf-100 text-xs uppercase text-shelf-600">
            <tr>
              <th className="px-4 py-3">Пользователь</th>
              <th className="px-4 py-3">Роль</th>
              <th className="px-4 py-3">Статус</th>
              <th className="px-4 py-3">Регистрация</th>
              <th className="px-4 py-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-shelf-100">
            {data === null ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-shelf-500">
                  Загружаем…
                </td>
              </tr>
            ) : data.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-shelf-500">
                  Никого не нашли.
                </td>
              </tr>
            ) : (
              data.items.map((u) => {
                const isMe = me?.id === u.id;
                const locked = isMe || u.role === "admin";
                return (
                  <tr key={u.id} className={cn(isMe && "bg-amber-50")}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-shelf-900">
                        @{u.login}
                        {isMe ? (
                          <span className="ml-2 rounded bg-amber-200 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                            это вы
                          </span>
                        ) : null}
                      </p>
                      <p className="text-xs text-shelf-500">{u.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      {locked ? (
                        ROLE_LABELS[u.role]
                      ) : (
                        <select
                          value={u.role}
                          aria-label={`Роль @${u.login}`}
                          onChange={(event) =>
                            setConfirm({
                              kind: "role",
                              user: u,
                              role: event.target.value as "user" | "moderator",
                            })
                          }
                          className="rounded-lg border border-shelf-300 bg-white px-2 py-1"
                        >
                          <option value="user">{ROLE_LABELS.user}</option>
                          <option value="moderator">{ROLE_LABELS.moderator}</option>
                        </select>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {u.is_blocked ? (
                        <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                          Заблокирован
                        </span>
                      ) : (
                        <span className="text-shelf-600">Активен</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-shelf-600">{formatDate(u.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      {locked ? (
                        <span className="text-xs text-shelf-400">защищено</span>
                      ) : (
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            onClick={() => setConfirm({ kind: u.is_blocked ? "unblock" : "block", user: u })}
                          >
                            {u.is_blocked ? "Разблокировать" : "Заблокировать"}
                          </Button>
                          <Button
                            variant="ghost"
                            className="text-red-700"
                            onClick={() => setConfirm({ kind: "delete", user: u })}
                          >
                            Удалить
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {data ? <Pager page={page} total={data.total} onPage={setPage} /> : null}

      {confirm ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="alertdialog"
          aria-modal="true"
          aria-label="Подтверждение"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-sm text-shelf-900">
              {confirm.kind === "role"
                ? `Назначить @${confirm.user.login} роль «${ROLE_LABELS[confirm.role]}»?`
                : CONFIRM_TEXT[confirm.kind](confirm.user)}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" disabled={busy} onClick={() => setConfirm(null)}>
                Отмена
              </Button>
              <Button
                disabled={busy}
                onClick={() => void apply()}
                className={confirm.kind === "delete" ? "bg-red-600 hover:bg-red-700" : undefined}
              >
                {busy ? "Выполняем…" : "Подтвердить"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const [open, setOpen] = useState(false);
  const details = Object.entries(entry.details ?? {});
  return (
    <>
      <tr className="align-top">
        <td className="whitespace-nowrap px-4 py-3 text-shelf-600">{formatDate(entry.created_at)}</td>
        <td className="px-4 py-3 font-medium text-shelf-900">@{entry.actor_login}</td>
        <td className="px-4 py-3">{ACTION_LABELS[entry.action] ?? entry.action}</td>
        <td className="px-4 py-3 text-shelf-600">
          {entry.target_type ? `${entry.target_type} #${entry.target_id}` : "—"}
        </td>
        <td className="px-4 py-3 text-right">
          {details.length > 0 ? (
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              className="text-xs text-accent-600 hover:underline"
            >
              {open ? "Скрыть" : "Детали"}
            </button>
          ) : null}
        </td>
      </tr>
      {open ? (
        <tr className="bg-shelf-50">
          <td colSpan={5} className="px-4 py-3 text-xs text-shelf-700">
            <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[auto_1fr]">
              {details.map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="font-semibold">{DETAIL_LABELS[key] ?? key}:</dt>
                  <dd className="break-words">{String(value ?? "—")}</dd>
                </div>
              ))}
            </dl>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function AuditSection() {
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [applied, setApplied] = useState({ action: "", actor: "", from: "", to: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<AuditEntry> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    adminApi
      .audit(
        {
          action: applied.action,
          actor: applied.actor,
          date_from: applied.from,
          date_to: applied.to,
          page,
          size: PAGE_SIZE,
        },
        controller.signal,
      )
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить журнал");
      });
    return () => controller.abort();
  }, [applied, page]);

  return (
    <section className="mt-12" aria-labelledby="admin-audit">
      <h2 id="admin-audit" className="text-xl font-semibold text-shelf-900">
        Журнал действий
      </h2>
      <p className="mt-1 text-sm text-shelf-600">Кто, что и когда сделал: модераторы и администраторы.</p>

      <form
        className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_auto_auto_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setApplied({ action, actor: actor.trim(), from, to });
        }}
      >
        <select
          value={action}
          aria-label="Действие"
          onChange={(event) => setAction(event.target.value)}
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">Все действия</option>
          {Object.entries(ACTION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <input
          value={actor}
          onChange={(event) => setActor(event.target.value)}
          placeholder="Автор (логин)"
          aria-label="Автор действия"
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        />
        <input
          type="date"
          value={from}
          aria-label="С даты"
          onChange={(event) => setFrom(event.target.value)}
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        />
        <input
          type="date"
          value={to}
          aria-label="По дату"
          onChange={(event) => setTo(event.target.value)}
          className="rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm"
        />
        <Button type="submit">Применить</Button>
      </form>

      {error ? (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-4 overflow-x-auto rounded-2xl bg-white ring-1 ring-shelf-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-shelf-100 text-xs uppercase text-shelf-600">
            <tr>
              <th className="px-4 py-3">Когда</th>
              <th className="px-4 py-3">Кто</th>
              <th className="px-4 py-3">Что</th>
              <th className="px-4 py-3">Объект</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-shelf-100">
            {data === null ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-shelf-500">
                  Загружаем…
                </td>
              </tr>
            ) : data.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-shelf-500">
                  Записей нет.
                </td>
              </tr>
            ) : (
              data.items.map((entry) => <AuditRow key={entry.id} entry={entry} />)
            )}
          </tbody>
        </table>
      </div>
      {data ? <Pager page={page} total={data.total} onPage={setPage} /> : null}
    </section>
  );
}

export default function AdminPage() {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(() => {
    adminApi
      .summary()
      .then(setSummary)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Не удалось загрузить сводку"),
      );
  }, []);

  useEffect(loadSummary, [loadSummary]);

  return (
    <section className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-shelf-900">Администрирование</h1>
      <p className="mt-1 text-shelf-600">Состояние системы, пользователи и история решений.</p>

      {error ? (
        <p className="mt-4 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      <SummaryCards summary={summary} />
      <UsersSection onChanged={loadSummary} />
      <AuditSection />
    </section>
  );
}
