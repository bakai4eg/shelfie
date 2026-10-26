import { useParams } from "react-router-dom";

import ComingSoon from "@/components/ui/ComingSoon";
import GuestNotice from "@/components/ui/GuestNotice";

export default function ItemPage() {
  const { itemId } = useParams();

  return (
    <ComingSoon task="T3.4" title="Страница карточки">
      <p>
        Карточка №{itemId}: обложка, метаданные, средний рейтинг, кнопки полок и оценок, рецензии и
        комментарии. Центральный экран продукта.
      </p>
      <GuestNotice action="добавить карточку на полку, поставить оценку и написать рецензию" />
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 3.</p>
    </ComingSoon>
  );
}
