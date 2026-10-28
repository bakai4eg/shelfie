import { api } from "@/lib/api";
import type { Page, Review } from "@/lib/types";

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
};
