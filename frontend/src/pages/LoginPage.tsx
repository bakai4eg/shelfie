import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { useAuth } from "@/features/auth/context";
import { ApiError } from "@/lib/api";
import { safeNextPath } from "@/lib/auth";

interface FlashState {
  expired?: boolean;
  passwordChanged?: boolean;
}

export default function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();

  const next = safeNextPath(params.get("next"));
  const expired = Boolean((location.state as FlashState | null)?.expired);
  const passwordChanged = Boolean((location.state as FlashState | null)?.passwordChanged);

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (status === "authenticated") {
    return <Navigate to={next} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);

    if (!identifier.trim() || !password) {
      setError("Введите логин и пароль");
      return;
    }

    setPending(true);
    try {
      await login({ login: identifier.trim(), password });
      navigate(next, { replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "Не удалось войти. Попробуйте ещё раз",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mx-auto max-w-md px-4 py-12 sm:py-16">
      <h1 className="text-3xl font-semibold text-shelf-900">Вход</h1>
      <p className="mt-2 text-sm text-shelf-700">
        Логин или e-mail и пароль. Сессия сохранится после перезагрузки страницы.
      </p>

      {passwordChanged ? (
        <p className="mt-6 rounded-xl bg-green-50 px-4 py-3 text-sm text-green-900 ring-1 ring-green-200" role="status">
          Пароль изменён. Войдите заново.
        </p>
      ) : null}

      {expired ? (
        <p className="mt-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200" role="status">
          Сессия истекла — войдите снова.
        </p>
      ) : null}

      <form className="mt-6 space-y-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200" onSubmit={handleSubmit} noValidate>
        {error ? (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200" role="alert">
            {error}
          </p>
        ) : null}

        <Field
          label="Логин или e-mail"
          name="login"
          autoComplete="username"
          autoFocus
          value={identifier}
          onChange={(event) => setIdentifier(event.target.value)}
          placeholder="bakai или bakai@example.com"
        />

        <Field
          label="Пароль"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Входим…" : "Войти"}
        </Button>
      </form>

      <p className="mt-6 text-sm text-shelf-700">
        Нет аккаунта?{" "}
        <Link
          to={`/register?next=${encodeURIComponent(next)}`}
          className="font-medium text-accent-600 hover:text-accent-700"
        >
          Зарегистрироваться
        </Link>
      </p>
    </section>
  );
}
