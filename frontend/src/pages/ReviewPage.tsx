import { useParams } from "react-router-dom";

import ComingSoon from "@/components/ui/ComingSoon";

export default function ReviewPage() {
  const { reviewId } = useParams();

  return (
    <ComingSoon task="T4.3" title="Рецензия">
      <p>
        Полный текст рецензии №{reviewId}, оценка автора, лайки и комментарии. Свою рецензию можно
        отредактировать или удалить.
      </p>
      <p className="text-sm text-shelf-500">Контракт: docs/api.md, раздел 7.</p>
    </ComingSoon>
  );
}
