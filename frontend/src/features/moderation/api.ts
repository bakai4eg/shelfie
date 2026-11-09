import { api } from "@/lib/api";
import type { ModerationCard, Report } from "@/lib/types";

export interface ReportCreatePayload {
  target_type: "review" | "comment" | "card" | "profile";
  target_id: number;
  reason: "spam" | "insult" | "false_info" | "copyright" | "other";
  comment?: string | null;
}

export interface ReportResolvePayload {
  decision: "reject" | "hide" | "delete";
  reason?: string | null;
}

export const moderationApi = {
  createReport: (payload: ReportCreatePayload) =>
    api.post<Report>("/reports", payload),

  myReports: (signal?: AbortSignal) =>
    api.get<Report[]>("/me/reports", { signal }),

  listReports: (
    params?: { status?: string; target_type?: string },
    signal?: AbortSignal,
  ) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.target_type) qs.set("target_type", params.target_type);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return api.get<Report[]>(`/moderation/reports${query}`, { signal });
  },

  resolveReport: (reportId: number, payload: ReportResolvePayload) =>
    api.post<Report>(`/moderation/reports/${reportId}/resolve`, payload),

  hideContent: (type: "review" | "card", id: number, reason: string) =>
    api.post<void>(`/moderation/content/${type}/${id}/hide`, { reason }),

  deleteContent: (type: "review" | "card", id: number, reason: string) =>
    api.post<void>(`/moderation/content/${type}/${id}/delete`, { reason }),

  pendingCards: (signal?: AbortSignal) =>
    api.get<ModerationCard[]>("/moderation/cards", { signal }),

  approveCard: (itemId: number) => api.post<void>(`/moderation/cards/${itemId}/approve`),

  rejectCard: (itemId: number, reason: string) =>
    api.post<void>(`/moderation/cards/${itemId}/reject`, { reason }),
};
