import ComingSoon from "@/components/ui/ComingSoon";

export default function CatalogPage() {
  return (
    <ComingSoon task="T2.1" title="Каталог">
      <p>
        Поиск по книгам, фильмам и сериалам, фильтры по типу, году, жанру, стране и источнику,
        региональный фильтр «Кыргызстан» и сортировка результатов.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 3.</p>
    </ComingSoon>
  );
}
