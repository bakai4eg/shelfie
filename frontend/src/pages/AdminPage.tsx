import ComingSoon from "@/components/ui/ComingSoon";

export default function AdminPage() {
  return (
    <ComingSoon task="T5.2" title="Администрирование">
      <p>
        Сводка по системе, управление ролями и блокировками, журнал действий модераторов и
        администраторов. Доступно только администраторам.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 11.</p>
    </ComingSoon>
  );
}
