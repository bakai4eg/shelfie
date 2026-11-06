import { api } from "@/lib/api";
import type { ListDetail, ListSummary, ListTheme } from "@/lib/types";

export interface ListFields {
  title: string;
  description: string | null;
  is_public: boolean;
  theme: ListTheme;
}

/** Контракт — docs/api.md, раздел 6. */
export const listsApi = {
  mine: (signal?: AbortSignal) => api.get<ListSummary[]>("/me/lists", { signal }),

  create: (payload: Partial<ListFields> & { title: string }) =>
    api.post<ListDetail>("/me/lists", payload),

  get: (listId: number, signal?: AbortSignal) =>
    api.get<ListDetail>(`/me/lists/${listId}`, { signal }),

  update: (listId: number, payload: Partial<ListFields>) =>
    api.patch<ListDetail>(`/me/lists/${listId}`, payload),

  remove: (listId: number) => api.delete<void>(`/me/lists/${listId}`),

  addItem: (listId: number, itemId: number, note?: string) =>
    api.post<ListDetail>(`/me/lists/${listId}/items`, { item_id: itemId, note: note || null }),

  setNote: (listId: number, itemId: number, note: string) =>
    api.patch<ListDetail>(`/me/lists/${listId}/items/${itemId}`, { note: note || null }),

  removeItem: (listId: number, itemId: number) =>
    api.delete<ListDetail>(`/me/lists/${listId}/items/${itemId}`),

  setOrder: (listId: number, itemIds: number[]) =>
    api.put<ListDetail>(`/me/lists/${listId}/order`, { item_ids: itemIds }),

  /** Публичная витрина: гость без токена. */
  publicList: (listId: number, signal?: AbortSignal) =>
    api.get<ListDetail>(`/public/lists/${listId}`, { signal, anonymous: true }),
};
