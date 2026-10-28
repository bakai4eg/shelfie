import { api } from "@/lib/api";
import type { FollowState, UserShort } from "@/lib/types";

export const socialApi = {
  follow: (login: string) =>
    api.post<FollowState>(`/users/${encodeURIComponent(login)}/follow`),

  unfollow: (login: string) =>
    api.delete<FollowState>(`/users/${encodeURIComponent(login)}/follow`),

  followers: (login: string, signal?: AbortSignal) =>
    api.get<UserShort[]>(`/users/${encodeURIComponent(login)}/followers`, { signal }),

  following: (login: string, signal?: AbortSignal) =>
    api.get<UserShort[]>(`/users/${encodeURIComponent(login)}/following`, { signal }),
};
