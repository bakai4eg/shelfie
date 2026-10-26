# REST API

Контракт между фронтендом и бэкендом. Реализация — `backend/app/api/routes/`, схема в Swagger (`/docs`). Если нужно поменять путь или формат — сначала правим этот документ в том же PR, потом код.

## Общие правила

- Базовый префикс: `/api`.
- Аутентификация: `Authorization: Bearer <token>`.
- Даты — ISO 8601 UTC (`2026-11-01T12:30:00Z`).
- Пагинация: `?page=1&size=20` (max 100), ответ:

```json
{ "items": [], "total": 0, "page": 1, "size": 20 }
```

- Ошибки: `{"detail": "текст"}` (см. `docs/architecture.md`, п. 10).
- Уровни доступа в таблицах: 🌐 гость · 👤 пользователь · 🛡 модератор · 👑 админ.

## 1. Аутентификация (T1.1, T1.2)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| POST | `/auth/register` | 🌐 | Регистрация: `login`, `email`, `password` |
| POST | `/auth/login` | 🌐 | Вход по `login` **или** `email` + `password` |
| POST | `/auth/logout` | 👤 | Отзыв текущей сессии |
| GET | `/auth/me` | 👤 | Текущий пользователь + роль |

Регистрация и вход возвращают:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_at": "2026-11-02T12:00:00Z",
  "user": { "id": 1, "login": "bakai", "email": "b@example.com", "role": "user" }
}
```

Правила: логин 3–32 символа (`[a-zA-Z0-9_]`), пароль ≥ 8, e-mail валидный и уникальный, ответ 409 при занятом логине/e-mail, 401 при неверной паре.

## 2. Профили (T1.3, T1.4)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/users/{login}` | 🌐 | Публичный профиль: логин, аватар, био, дата регистрации, статистика |
| GET | `/users/{login}/reviews` | 🌐 | Публичные рецензии пользователя (пагинация) |
| GET | `/users/{login}/lists` | 🌐 | Публичные списки пользователя |
| PATCH | `/me/profile` | 👤 | `bio` (≤ 500), опционально `avatar_url` |
| POST | `/me/avatar` | 👤 | `multipart/form-data`, поле `file`; заменяет прежний аватар |
| DELETE | `/me/avatar` | 👤 | Удалить аватар |
| PUT | `/me/password` | 👤 | `current_password`, `new_password`; отзывает все сессии |

Ответ профиля:

```json
{
  "login": "bakai",
  "avatar_url": "/media/avatars/6f1c.jpg",
  "bio": "Смотрю кино, читаю Кыргызстан",
  "registered_at": "2026-10-20T08:00:00Z",
  "stats": {
    "books_read": 4, "movies_watched": 12, "series_watched": 3,
    "ratings_count": 19, "rating_avg": 7.8,
    "reviews_count": 5, "followers": 7, "following": 9
  },
  "is_following": false
}
```

## 3. Каталог (T2.1, T2.2, T3.4)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/catalog` | 🌐 | Поиск и фильтры (см. параметры ниже) |
| GET | `/catalog/filters` | 🌐 | Жанры, страны, годы, источники для панели фильтров |
| GET | `/catalog/{item_id}` | 🌐 | Карточка: рейтинг, счётчик оценок, кнопки полок, последние рецензии |

Параметры `GET /catalog`:

| Параметр | Тип | Описание |
| --- | --- | --- |
| `q` | string | Поиск по названию (и оригинальному названию) |
| `type` | enum | `book` \| `movie` \| `series` |
| `year_from`, `year_to` | int | Диапазон года выпуска |
| `genre` | string | Жанр |
| `country` | string | Страна производства/издания |
| `source` | enum | `local` \| `tmdb` \| `openlibrary` \| `google_books` |
| `local_only` | bool | Региональный фильтр «Кыргызстан» |
| `sort` | enum | `relevance` \| `year_desc` \| `rating_desc` \| `title_asc` |

Правило: при `q` поиск идёт по БД **и** внешним источникам; сбой источника не ломает ответ. `moderation_status = hidden` и чужие `pending` в выдачу не попадают.

## 4. Локальные карточки (T2.3)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| POST | `/cards/local` | 👤 | Создать карточку: тип, название, оригинальное название, год, страна, жанры, описание, обложка, `is_local` |
| GET | `/cards/local/mine` | 👤 | Мои карточки со статусом проверки |
| GET | `/cards/local/duplicates` | 👤 | `?title=&year=` — подсказка о совпадениях перед созданием |
| PATCH | `/cards/local/{item_id}` | 👤 | Правка своей карточки, пока она `pending` |

Созданная карточка всегда получает `source = local`, `moderation_status = pending` и видна только автору и модераторам.

## 5. Полки и оценки (T2.4, T3.3)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/me/library` | 👤 | `?status=&type=&sort=added_desc\|rating_desc\|title_asc` |
| PUT | `/me/library/{item_id}` | 👤 | Статус и дата завершения: `{"status": "finished", "finished_at": "2026-11-10"}` |
| DELETE | `/me/library/{item_id}` | 👤 | Убрать с полки |
| PUT | `/me/ratings/{item_id}` | 👤 | Оценка 1–10 |
| DELETE | `/me/ratings/{item_id}` | 👤 | Снять оценку |

Правила: `finished_at` обязателен при `finished`, иначе `null`; оценка не запрашивается для `planned`, но технически разрешена; `PUT` идемпотентен; 404 на скрытую карточку.

## 6. Списки и витрины (T3.2)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/me/lists` | 👤 | Мои списки (публичные и приватные) |
| POST | `/me/lists` | 👤 | `title`, `description`, `is_public`, `theme` |
| GET | `/me/lists/{list_id}` | 👤 | Список с позициями и заметками |
| PATCH | `/me/lists/{list_id}` | 👤 | Название, описание, приватность, тема |
| DELETE | `/me/lists/{list_id}` | 👤 | Удалить список |
| POST | `/me/lists/{list_id}/items` | 👤 | `item_id`, `note` (≤ 500) |
| PATCH | `/me/lists/{list_id}/items/{item_id}` | 👤 | Изменить заметку |
| DELETE | `/me/lists/{list_id}/items/{item_id}` | 👤 | Убрать карточку |
| PUT | `/me/lists/{list_id}/order` | 👤 | `{"item_ids": [3, 1, 2]}` — новый порядок |
| GET | `/public/lists/{list_id}` | 🌐 | Публичная витрина: обложки, заметки, порядок, тема |

Темы: `classic`, `noir`, `pastel` (минимум три по ТЗ 4.4.3). Приватный список на публичном маршруте отдаёт 404.

## 7. Рецензии и комментарии (T4.3, T4.4)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/catalog/{item_id}/reviews` | 🌐 | Рецензии карточки, новые сверху |
| POST | `/catalog/{item_id}/reviews` | 👤 | `title`, `body`, `rating` (опционально); одна рецензия на карточку |
| PATCH | `/reviews/{review_id}` | 👤 автор | Правка своей рецензии |
| DELETE | `/reviews/{review_id}` | 👤 автор · 🛡 | Удаление |
| GET | `/reviews/{review_id}/comments` | 🌐 | Комментарии |
| POST | `/reviews/{review_id}/comments` | 👤 | `body` (≤ 1000) |
| DELETE | `/comments/{comment_id}` | 👤 автор · 🛡 | Удаление |

Скрытые рецензии не отдаются гостю и не-автору. Удаление рецензии каскадно уносит комментарии, лайки и события ленты.

## 8. Лайки, подписки, лента (T5.3, T5.4)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| POST | `/likes` | 👤 | `{"target_type": "review"\|"comment", "target_id": 12}` |
| DELETE | `/likes` | 👤 | Снять лайк (тот же body) |
| POST | `/users/{login}/follow` | 👤 | Подписаться |
| DELETE | `/users/{login}/follow` | 👤 | Отписаться |
| GET | `/users/{login}/followers` | 🌐 | Подписчики |
| GET | `/users/{login}/following` | 🌐 | Подписки |
| GET | `/feed` | 👤 | Лента по подпискам, новые сверху, пагинация |

События ленты: `review_created`, `item_finished`, `rating_set`, `list_published`.

## 9. Жалобы (T4.1)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| POST | `/reports` | 👤 | `target_type` (`review`\|`comment`\|`card`\|`profile`), `target_id`, `reason`, `comment` |
| GET | `/me/reports` | 👤 | Мои жалобы и их статусы |

Причины: `spam`, `insult`, `false_info`, `copyright`, `other`. Повторная жалоба на тот же объект — 409.

## 10. Модерация (T4.2)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/moderation/reports` | 🛡 | Очередь жалоб: `?status=open&target_type=` |
| POST | `/moderation/reports/{report_id}/resolve` | 🛡 | `{"decision": "reject"\|"hide"\|"delete", "reason": "..."}` |
| POST | `/moderation/content/{target_type}/{target_id}/hide` | 🛡 | Скрыть материал |
| POST | `/moderation/content/{target_type}/{target_id}/delete` | 🛡 | Удалить материал с каскадом |
| GET | `/moderation/cards` | 🛡 | Локальные карточки на проверке |
| POST | `/moderation/cards/{item_id}/approve` | 🛡 | Подтвердить карточку |
| POST | `/moderation/cards/{item_id}/reject` | 🛡 | Отклонить с причиной |

Каждое решение пишется в журнал (`audit_log`) и сохраняется в жалобе.

## 11. Администрирование (T5.1, T5.2)

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/admin/summary` | 👑 | Пользователи, карточки, рецензии, открытые жалобы |
| GET | `/admin/users` | 👑 | `?q=&role=&is_blocked=` |
| PATCH | `/admin/users/{user_id}/role` | 👑 | `{"role": "user"\|"moderator"}` |
| POST | `/admin/users/{user_id}/block` | 👑 | Блокировка + отзыв сессий |
| POST | `/admin/users/{user_id}/unblock` | 👑 | Разблокировка |
| DELETE | `/admin/users/{user_id}` | 👑 | Удаление со всеми данными и файлами |
| GET | `/admin/audit` | 👑 | Журнал: кто, что, когда |

Свою роль и свою учётку изменить нельзя (409).

## 12. Служебное

| Метод | Путь | Доступ | Описание |
| --- | --- | --- | --- |
| GET | `/api/health` | 🌐 | `{"status": "ok", "db": "ok"}` |

## Чек-лист контракта

- [ ] Все эндпоинты из документа реализованы и видны в Swagger.
- [ ] Права проверены хотя бы одним тестом на каждую роль.
- [ ] Формат ответов совпадает с примерами (фронтенд не чинит руками).
- [ ] Новые поля описаны здесь до мержа.
