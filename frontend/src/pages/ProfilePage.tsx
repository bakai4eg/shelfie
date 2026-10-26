import { useParams } from "react-router-dom";

import ComingSoon from "@/components/ui/ComingSoon";

export default function ProfilePage() {
  const { login } = useParams();

  return (
    <ComingSoon task="T1.3" title={`Профиль @${login ?? ""}`}>
      <p>
        Публичная страница пользователя: аватар, описание, дата регистрации, статистика и его
        рецензии с публичными списками.
      </p>
      <p className="text-sm text-shelf-500">Открывается без входа. Контракт: docs/api.md, раздел 2.</p>
    </ComingSoon>
  );
}
