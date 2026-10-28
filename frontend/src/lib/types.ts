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
  avatar_url: string | null;
}

export interface LoginPayload {
  /** Логин или e-mail — бэкенд принимает и то, и другое. */
  login: string;
  password: string;
}

export interface RegisterPayload {
  login: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
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

export type CatalogSort = "relevance" | "year_desc" | "rating_desc" | "title_asc";

export interface CatalogFilters {
  types: ItemType[];
  sources: ItemSource[];
  genres: string[];
  countries: string[];
  year_min: number | null;
  year_max: number | null;
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

export interface ReviewPreview {
  id: number;
  title: string;
  rating: number | null;
  created_at: string;
}

export interface ListPreview {
  id: number;
  title: string;
  theme: ListTheme;
  items_count: number;
}
