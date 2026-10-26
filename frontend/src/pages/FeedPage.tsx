import ComingSoon from "@/components/ui/ComingSoon";

export default function FeedPage() {
  return (
    <ComingSoon task="T5.4" title="Лента активности">
      <p>
        Новые рецензии, завершённые карточки, оценки и публичные списки людей, на которых вы
        подписаны — в порядке убывания времени.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 8.</p>
    </ComingSoon>
  );
}
