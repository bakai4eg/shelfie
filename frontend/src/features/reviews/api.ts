import { api } from "@/lib/api";
import type { CommentItem, FeedEvent, LikeState, Page, Review } from "@/lib/types";

export interface ReviewCreatePayload {
  title: string;
  body: string;
  rating?: number | null;
}

export interface ReviewUpdatePayload {
  title?: string;
  body?: string;
  rating?: number | null;
}

export const reviewsApi = {
  listForItem: (itemId: number, page = 1, size = 20, signal?: AbortSignal) =>
    api.get<Page<Review>>(`/catalog/${itemId}/reviews?page=${page}&size=${size}`, { signal }),

  create: (itemId: number, payload: ReviewCreatePayload) =>
    api.post<Review>(`/catalog/${itemId}/reviews`, payload),

  update: (reviewId: number, payload: ReviewUpdatePayload) =>
    api.patch<Review>(`/reviews/${reviewId}`, payload),

  delete: (reviewId: number) => api.delete<void>(`/reviews/${reviewId}`),

  get: (reviewId: number, signal?: AbortSignal) =>
    api.get<Review>(`/reviews/${reviewId}`, { signal }),
};

/** Комментарии, лайки и лента. Контракт — docs/api.md, разделы 7-8. */
export const engagementApi = {
  comments: (reviewId: number, page = 1, size = 20, signal?: AbortSignal) =>
    api.get<Page<CommentItem>>(`/reviews/${reviewId}/comments?page=${page}&size=${size}`, {
      signal,
    }),

  addComment: (reviewId: number, body: string) =>
    api.post<CommentItem>(`/reviews/${reviewId}/comments`, { body }),

  deleteComment: (commentId: number) => api.delete<void>(`/comments/${commentId}`),

  like: (target_type: "review" | "comment", target_id: number) =>
    api.post<LikeState>("/likes", { target_type, target_id }),

  unlike: (target_type: "review" | "comment", target_id: number) =>
    api.delete<LikeState>("/likes", { target_type, target_id }),

  feed: (page = 1, size = 20, signal?: AbortSignal) =>
    api.get<Page<FeedEvent>>(`/feed?page=${page}&size=${size}`, { signal }),
};
