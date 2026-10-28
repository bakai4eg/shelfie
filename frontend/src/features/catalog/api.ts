import { api } from "@/lib/api";
import type {
  CatalogFilters,
  CatalogItem,
  CatalogSort,
  ItemSource,
  ItemType,
  Page,
} from "@/lib/types";

/** Параметры поиска повторяют docs/api.md, раздел 3. */
export interface CatalogQuery {
  q?: string;
  type?: ItemType;
  year_from?: number;
  year_to?: number;
  genre?: string;
  country?: string;
  source?: ItemSource;
  local_only?: boolean;
  sort?: CatalogSort;
  page?: number;
  size?: number;
}

export const CATALOG_PAGE_SIZE = 20;

function toQueryString(query: CatalogQuery): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === "" || value === false) {
      return;
    }
    params.set(key, value === true ? "true" : String(value));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function fetchCatalog(
  query: CatalogQuery,
  signal?: AbortSignal,
): Promise<Page<CatalogItem>> {
  return api.get<Page<CatalogItem>>(`/catalog${toQueryString(query)}`, { signal });
}

export function fetchCatalogFilters(signal?: AbortSignal): Promise<CatalogFilters> {
  return api.get<CatalogFilters>("/catalog/filters", { signal });
}

export function fetchItem(itemId: number, signal?: AbortSignal): Promise<CatalogItem> {
  return api.get<CatalogItem>(`/catalog/${itemId}`, { signal });
}
