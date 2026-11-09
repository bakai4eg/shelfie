import { api } from "@/lib/api";
import type { AdminSummary, AdminUser, AuditEntry, Page, Role } from "@/lib/types";

export interface UsersQuery {
  q?: string;
  role?: Role;
  is_blocked?: boolean;
  page?: number;
  size?: number;
}

export interface AuditQuery {
  action?: string;
  actor?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
}

function qs(query: object): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const text = params.toString();
  return text ? `?${text}` : "";
}

/** Контракт — docs/api.md, раздел 11. */
export const adminApi = {
  summary: (signal?: AbortSignal) => api.get<AdminSummary>("/admin/summary", { signal }),

  users: (query: UsersQuery, signal?: AbortSignal) =>
    api.get<Page<AdminUser>>(`/admin/users${qs(query)}`, { signal }),

  setRole: (userId: number, role: "user" | "moderator") =>
    api.patch<AdminUser>(`/admin/users/${userId}/role`, { role }),

  block: (userId: number) => api.post<AdminUser>(`/admin/users/${userId}/block`),

  unblock: (userId: number) => api.post<AdminUser>(`/admin/users/${userId}/unblock`),

  remove: (userId: number) => api.delete<void>(`/admin/users/${userId}`),

  audit: (query: AuditQuery, signal?: AbortSignal) =>
    api.get<Page<AuditEntry>>(`/admin/audit${qs(query)}`, { signal }),
};
