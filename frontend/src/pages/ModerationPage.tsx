import ComingSoon from "@/components/ui/ComingSoon";

export default function ModerationPage() {
  return (
    <ComingSoon task="T4.2" title="Модерация">
      <p>
        Очередь жалоб с контекстом, решения «отклонить / скрыть / удалить» и проверка локальных
        карточек перед публикацией. Доступно модераторам и администраторам.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 10.</p>
    </ComingSoon>
  );
}
