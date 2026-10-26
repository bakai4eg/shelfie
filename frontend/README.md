# Frontend

React 18 + TypeScript + Vite + Tailwind CSS. Контракт API — [`docs/api.md`](../docs/api.md), общая архитектура — [`docs/architecture.md`](../docs/architecture.md).

## Запуск

```bash
npm install
npm run dev        # http://localhost:5173
```

В dev-режиме запросы `/api` проксируются на `http://localhost:8000` (см. `vite.config.ts`), поэтому CORS не мешает. Если бэкенд живёт на другом адресе — задайте `VITE_API_URL` в `.env`.

```bash
npm run typecheck  # tsc --noEmit
npm run lint
npm run build      # проверка прод-сборки
```

## Структура

```
src/
├── app/          # App.tsx — маршруты и оболочка приложения
├── components/
│   ├── layout/   # Header, Footer, Layout
│   └── ui/       # кнопки, заглушки и прочий переиспользуемый кит
├── features/     # фичи по подсистемам (создаются вместе с задачами)
├── lib/          # api-клиент, константы ТЗ, типы ответов, утилиты
├── pages/        # страницы верхнего уровня
└── index.css     # Tailwind + токены палитры
```

### Как добавлять фичу

1. Папка `src/features/<подсистема>/`.
2. Внутри — `api.ts` (хуки TanStack Query), `components/`, `types.ts` при необходимости.
3. Страница в `src/pages/` собирает фичу и отвечает только за компоновку.
4. Страница **не делает `fetch` напрямую** — только через хук фичи.

```
features/
├── auth/        # T1.1, T1.2
├── profile/     # T1.3, T1.4
├── catalog/     # T2.1, T2.2, T3.4
├── local-cards/ # T2.3
├── shelves/     # T2.4, T3.3
├── lists/       # T3.2
├── social/      # T4.3, T4.4, T5.3, T5.4
├── moderation/  # T4.1, T4.2
└── admin/       # T5.1, T5.2
```

## Договорённости

- `@/` — алиас на `src/`, относительные импорты через `../../` не используем.
- Токен и заголовок `Authorization` живут только в `lib/api.ts` и `AuthProvider` (появится в T1.1).
- Константы из ТЗ (статусы, темы, причины жалоб) — в `lib/constants.ts`, не хардкодим в компонентах.
- Типы ответов — в `lib/types.ts`, синхронизированы с `docs/api.md`.
- Палитра — токены `shelf-*` и `accent-*` из `index.css`; произвольные hex в разметке не пишем.
- Адаптив проверяем от 360 px: сначала мобильная вёрстка, потом расширяем.
- Каждая страница-заглушка знает номер своей задачи — по нему открывается карточка на GitHub.
