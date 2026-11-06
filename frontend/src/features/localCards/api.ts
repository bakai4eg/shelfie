import { api } from "@/lib/api";
import type { ItemType, LocalCard, Page } from "@/lib/types";

/** Поля формы локальной карточки. Обложка передаётся отдельным файлом. */
export interface LocalCardInput {
  type: ItemType;
  title: string;
  original_title?: string | null;
  year?: number | null;
  country?: string | null;
  genres?: string[];
  description?: string | null;
  is_local?: boolean;
}

function toFormData(
  input: LocalCardInput,
  poster?: File | null,
  removePoster = false,
): FormData {
  const body = new FormData();
  body.append("type", input.type);
  body.append("title", input.title);
  body.append("original_title", input.original_title ?? "");
  if (input.year !== undefined && input.year !== null) {
    body.append("year", String(input.year));
  }
  body.append("country", input.country ?? "");
  body.append("genres", (input.genres ?? []).join(", "));
  body.append("description", input.description ?? "");
  body.append("is_local", input.is_local === false ? "false" : "true");
  if (poster) {
    body.append("poster", poster);
  }
  if (removePoster) {
    body.append("remove_poster", "true");
  }
  return body;
}

export const localCardsApi = {
  create: (input: LocalCardInput, poster?: File | null) =>
    api.post<LocalCard>("/cards/local", toFormData(input, poster)),

  update: (
    itemId: number,
    input: LocalCardInput,
    poster?: File | null,
    removePoster = false,
  ) =>
    api.patch<LocalCard>(
      `/cards/local/${itemId}`,
      toFormData(input, poster, removePoster),
    ),

  mine: (page = 1, size = 20, signal?: AbortSignal) =>
    api.get<Page<LocalCard>>(`/cards/local/mine?page=${page}&size=${size}`, {
      signal,
    }),

  duplicates: (title: string, year?: number | null, signal?: AbortSignal) => {
    const params = new URLSearchParams({ title });
    if (year !== undefined && year !== null) {
      params.set("year", String(year));
    }
    return api.get<LocalCard[]>(`/cards/local/duplicates?${params.toString()}`, {
      signal,
    });
  },
};
