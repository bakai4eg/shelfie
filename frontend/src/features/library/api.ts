import { api } from "@/lib/api";
import type { ItemType, RatingResult, ShelfEntry, ShelfStatus } from "@/lib/types";

export interface LibraryQuery {
  status?: ShelfStatus;
  type?: ItemType;
  sort?: "added_desc" | "rating_desc" | "title_asc";
}

function toQueryString(query: LibraryQuery = {}): string {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.type) params.set("type", query.type);
  if (query.sort) params.set("sort", query.sort);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const libraryApi = {
  list: (query?: LibraryQuery, signal?: AbortSignal) =>
    api.get<ShelfEntry[]>(`/me/library${toQueryString(query)}`, { signal }),

  upsertShelf: (
    itemId: number,
    payload: { status: ShelfStatus; finished_at?: string | null },
  ) => api.put<ShelfEntry>(`/me/library/${itemId}`, payload),

  deleteShelf: (itemId: number) => api.delete<void>(`/me/library/${itemId}`),

  setRating: (itemId: number, value: number) =>
    api.put<RatingResult>(`/me/ratings/${itemId}`, { value }),

  deleteRating: (itemId: number) => api.delete<RatingResult>(`/me/ratings/${itemId}`),
};
