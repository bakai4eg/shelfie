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

  updateBio: (bio: string) => api.patch<PublicProfile>("/me/profile", { bio }),

  uploadAvatar: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return api.post<{ avatar_url: string }>("/me/avatar", body);
  },

  deleteAvatar: () => api.delete<void>("/me/avatar"),

  changePassword: (current: string, next: string) =>
    api.put<void>("/me/password", { current_password: current, new_password: next }),
};
