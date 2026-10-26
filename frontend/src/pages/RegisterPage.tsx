import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { useAuth } from "@/features/auth/context";
import { ApiError } from "@/lib/api";
import { safeNextPath } from "@/lib/auth";
import {
  LOGIN_MAX_LENGTH,
  LOGIN_MIN_LENGTH,
  LOGIN_PATTERN,
  PASSWORD_MAX_BYTES,
  PASSWORD_MIN_LENGTH,
} from "@/lib/constants";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;

interface Values {
  login: string;
  email: string;
  password: string;
}

type Errors = Partial<Record<keyof Values, string>>;

function validate(values: Values): Errors {
  const errors: Errors = {};
  const login = values.login.trim();
  const email = values.email.trim();

  if (!login) {
    errors.login = "Введите логин";
  } else if (login.length < LOGIN_MIN_LENGTH || login.length > LOGIN_MAX_LENGTH) {
    errors.login = `Логин — от ${LOGIN_MIN_LENGTH} до ${LOGIN_MAX_LENGTH} символов`;
  } else if (!LOGIN_PATTERN.test(login)) {
    errors.login = "Только латиница, цифры и подчёркивание";
  }

  if (!email) {
    errors.email = "Введите e-mail";
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = "Похоже, в e-mail ошибка";
  }

  if (values.password.length < PASSWORD_MIN_LENGTH) {
    errors.password = `Пароль не короче ${PASSWORD_MIN_LENGTH} символов`;
  } else if (new TextEncoder().encode(values.password).length > PASSWORD_MAX_BYTES) {
    errors.password = `Пароль длиннее ${PASSWORD_MAX_BYTES} байт`;
  }

  return errors;
}

export default function RegisterPage() {
  const { register, status } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNextPath(params.get("next"));

  const [values, setValues] = useState<Values>({ login: "", email: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (status === "authenticated") {
    return <Navigate to={next} replace />;
  }

  function update(field: keyof Values, value: string): void {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);

    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      return;
    }

    setPending(true);
    try {
      await register({
        login: values.login.trim(),
        email: values.email.trim(),
        password: values.password,
      });
      navigate(next, { replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "Не удалось создать аккаунт. Попробуйте ещё раз",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mx-auto max-w-md px-4 py-12 sm:py-16">
      <h1 className="text-3xl font-semibold text-shelf-900">Регистрация</h1>
      <p className="mt-2 text-sm text-shelf-700">
        Логин станет адресом публичного профиля. E-mail нужен для входа и восстановления доступа.
      </p>

      <form className="mt-6 space-y-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200" onSubmit={handleSubmit} noValidate>
        {error ? (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200" role="alert">
            {error}
          </p>
        ) : null}

        <Field
          label="Логин"
          name="login"
          autoComplete="username"
          autoFocus
          value={values.login}
          onChange={(event) => update("login", event.target.value)}
          error={errors.login}
          hint={`От ${LOGIN_MIN_LENGTH} до ${LOGIN_MAX_LENGTH} символов: латиница, цифры, подчёркивание`}
          placeholder="bakai"
        />

        <Field
          label="E-mail"
          name="email"
          type="email"
          autoComplete="email"
          value={values.email}
          onChange={(event) => update("email", event.target.value)}
          error={errors.email}
          placeholder="bakai@example.com"
        />

        <Field
          label="Пароль"
          name="password"
          type="password"
          autoComplete="new-password"
          value={values.password}
          onChange={(event) => update("password", event.target.value)}
          error={errors.password}
          hint={`Не короче ${PASSWORD_MIN_LENGTH} символов`}
        />

        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Создаём аккаунт…" : "Создать аккаунт"}
        </Button>
      </form>

      <p className="mt-6 text-sm text-shelf-700">
        Уже есть аккаунт?{" "}
        <Link
          to={`/login?next=${encodeURIComponent(next)}`}
          className="font-medium text-accent-600 hover:text-accent-700"
        >
          Войти
        </Link>
      </p>
    </section>
  );
}
