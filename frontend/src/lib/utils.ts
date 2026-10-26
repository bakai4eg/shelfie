/** Утилиты без зависимостей: классы и даты. */

export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

/** 7.5 → «7,5» — так средний рейтинг читается привычнее. */
export function formatRating(value: number): string {
  return value.toFixed(1).replace(".", ",");
}
