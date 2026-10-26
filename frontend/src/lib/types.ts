/** Типы ответов API. Источник истины — docs/api.md. */

export type Role = "user" | "moderator" | "admin";
export type ItemType = "book" | "movie" | "series";
export type ShelfStatus = "watching" | "finished" | "planned" | "dropped";
export type ItemSource = "local" | "tmdb" | "openlibrary" | "google_books";
export type ListTheme = "classic" | "noir" | "pastel";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface User {
  id: number;
  login: string;
  email: string;
  role: Role;
}

export interface CatalogItem {
  id: number;
  type: ItemType;
  title: string;
  original_title: string | null;
  year: number | null;
  country: string | null;
  genres: string[];
  poster_url: string | null;
  rating_avg: number;
  ratings_count: number;
  is_local: boolean;
  source: ItemSource;
}

export interface UserStats {
  books_read: number;
  movies_watched: number;
  series_watched: number;
  ratings_count: number;
  rating_avg: number;
  reviews_count: number;
  followers: number;
  following: number;
}

export interface PublicProfile {
  login: string;
  avatar_url: string | null;
  bio: string | null;
  registered_at: string;
  stats: UserStats;
  is_following: boolean;
}
