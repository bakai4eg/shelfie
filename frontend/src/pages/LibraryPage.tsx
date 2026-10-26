import ComingSoon from "@/components/ui/ComingSoon";

export default function LibraryPage() {
  return (
    <ComingSoon task="T2.4" title="Мои полки">
      <p>
        Полки по статусам: «Читаю/Смотрю», «Прочитано/Просмотрено», «Запланировано», «Брошено», с
        фильтром по типу контента и сортировкой.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 5.</p>
    </ComingSoon>
  );
}
