"""Константы, заданные ТЗ. Меняются только вместе с ТЗ."""

from typing import Final

# --- Роли (ТЗ 4.6.1) ---
ROLE_USER: Final = "user"
ROLE_MODERATOR: Final = "moderator"
ROLE_ADMIN: Final = "admin"

# Чем больше число, тем больше прав
ROLE_LEVEL: Final[dict[str, int]] = {
    ROLE_USER: 1,
    ROLE_MODERATOR: 2,
    ROLE_ADMIN: 3,
}

# --- Типы контента (ТЗ 4.3.1) ---
ITEM_BOOK: Final = "book"
ITEM_MOVIE: Final = "movie"
ITEM_SERIES: Final = "series"
ITEM_TYPES: Final = (ITEM_BOOK, ITEM_MOVIE, ITEM_SERIES)

# --- Источники карточек (ТЗ 4.3.2, 4.3.3) ---
SOURCE_LOCAL: Final = "local"
SOURCE_TMDB: Final = "tmdb"
SOURCE_OPENLIBRARY: Final = "openlibrary"
SOURCE_GOOGLE_BOOKS: Final = "google_books"

# --- Проверка карточек (ТЗ 4.3.3) ---
MODERATION_PENDING: Final = "pending"
MODERATION_APPROVED: Final = "approved"
MODERATION_HIDDEN: Final = "hidden"

# --- Статусы полки (ТЗ 4.4.1) ---
STATUS_WATCHING: Final = "watching"
STATUS_FINISHED: Final = "finished"
STATUS_PLANNED: Final = "planned"
STATUS_DROPPED: Final = "dropped"
SHELF_STATUSES: Final = (STATUS_WATCHING, STATUS_FINISHED, STATUS_PLANNED, STATUS_DROPPED)

# --- Оценки (ТЗ 4.4.2) ---
RATING_MIN: Final = 1
RATING_MAX: Final = 10

# --- Списки (ТЗ 4.4.3) ---
LIST_NOTE_MAX_LENGTH: Final = 500
LIST_THEMES: Final = ("classic", "noir", "pastel")

# --- Социальный модуль (ТЗ 4.5) ---
REVIEW_BODY_MAX_LENGTH: Final = 10_000
COMMENT_MAX_LENGTH: Final = 1_000

# --- Жалобы (ТЗ 4.6.2) ---
REPORT_REASONS: Final = ("spam", "insult", "false_info", "copyright", "other")
REPORT_TARGET_TYPES: Final = ("review", "comment", "card", "profile")
REPORT_RESOLUTIONS: Final = ("reject", "hide", "delete")

# --- Профиль (ТЗ 4.2.3, 4.2.4) ---
BIO_MAX_LENGTH: Final = 500
LOGIN_MIN_LENGTH: Final = 3
LOGIN_MAX_LENGTH: Final = 32
PASSWORD_MIN_LENGTH: Final = 8

# --- Файлы ---
ALLOWED_IMAGE_TYPES: Final = ("image/jpeg", "image/png", "image/webp")
