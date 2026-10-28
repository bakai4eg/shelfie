import { api } from "@/lib/api";
import type { ListPreview, Page, PublicProfile, ReviewPreview } from "@/lib/types";

/** Публичные разделы профиля. Контракт — docs/api.md, раздел 2. */
export const profileApi = {
  get: (login: string, signal?: AbortSignal) =>
    api.get<PublicProfile>(`/users/${encodeURIComponent(login)}`, { signal }),

  reviews: (login: string, signal?: AbortSignal, page = 1, size = 20) =>
    api.get<Page<ReviewPreview>>(
      `/users/${encodeURIComponent(login)}/reviews?page=${page}&size=${size}`,
      { signal },
    ),

  lists: (login: string, signal?: AbortSignal, page = 1, size = 20) =>
    api.get<Page<ListPreview>>(
      `/users/${encodeURIComponent(login)}/lists?page=${page}&size=${size}`,
      { signal },
    ),
};
