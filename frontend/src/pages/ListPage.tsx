import { useParams } from "react-router-dom";

import ComingSoon from "@/components/ui/ComingSoon";

export default function ListPage() {
  const { listId } = useParams();

  return (
    <ComingSoon task="T3.2" title="Витрина списка">
      <p>
        Публичная страница списка №{listId}: обложки, заметки автора, порядок карточек и выбранная
        тема оформления. Открывается без входа.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 6.</p>
    </ComingSoon>
  );
}
