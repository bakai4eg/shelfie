/** Значения, продублированные из ТЗ и бэкенда. Меняются вместе с ТЗ. */

import type { Role } from "@/lib/types";

export const REPO_URL = "https://github.com/bakai4eg/shelfie";
export const TASK_URL = (taskId: string) =>
  `${REPO_URL}/blob/main/tasks/${taskId}.md`;

export const ITEM_TYPE_LABELS = {
  book: "Книга",
  movie: "Фильм",
  series: "Сериал",
} as const;

export const SHELF_STATUS_LABELS = {
  watching: "Читаю / Смотрю",
  finished: "Прочитано / Просмотрено",
  planned: "Запланировано",
  dropped: "Брошено",
} as const;

export const ROLE_LABELS = {
  user: "Пользователь",
  moderator: "Модератор",
  admin: "Администратор",
} as const;

/** Уровни ролей повторяют backend/app/core/constants.py: больше — значит сильнее. */
export const ROLE_LEVEL: Record<Role, number> = {
  user: 1,
  moderator: 2,
  admin: 3,
};

export const LIST_THEME_LABELS = {
  classic: "Классика",
  noir: "Нуар",
  pastel: "Пастель",
} as const;

export const REPORT_REASON_LABELS = {
  spam: "Спам",
  insult: "Оскорбление",
  false_info: "Недостоверные сведения",
  copyright: "Нарушение авторских прав",
  other: "Иное",
} as const;

export const RATING_MIN = 1;
export const RATING_MAX = 10;
export const LOGIN_MIN_LENGTH = 3;
export const LOGIN_MAX_LENGTH = 32;
export const LOGIN_PATTERN = /^[A-Za-z0-9_]+$/;
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;
export const LIST_NOTE_MAX_LENGTH = 500;
export const COMMENT_MAX_LENGTH = 1000;
