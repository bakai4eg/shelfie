import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import Button from "@/components/ui/Button";
import Field from "@/components/ui/Field";
import { useAuth } from "@/features/auth/context";
import { profileApi } from "@/features/profile/api";
import { ApiError } from "@/lib/api";
import type { PublicProfile } from "@/lib/types";

const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_AVATAR_SIZE = 5 * 1024 * 1024; // 5 МБ

function SettingsSkeleton() {
  return (
    <div className="mt-8 space-y-6 animate-pulse" aria-hidden>
      <div className="h-56 rounded-2xl bg-white p-6 ring-1 ring-shelf-200" />
      <div className="h-56 rounded-2xl bg-white p-6 ring-1 ring-shelf-200" />
      <div className="h-72 rounded-2xl bg-white p-6 ring-1 ring-shelf-200" />
    </div>
  );
}

export default function SettingsPage() {
  const { user, refresh, clearSession } = useAuth();
  const navigate = useNavigate();
  const login = user?.login ?? "";

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Блок а: Описание профиля
  const [bio, setBio] = useState("");
  const [bioPending, setBioPending] = useState(false);
  const [bioError, setBioError] = useState<string | null>(null);
  const [bioSuccess, setBioSuccess] = useState<string | null>(null);

  // Блок b: Аватар
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [avatarPending, setAvatarPending] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [avatarSuccess, setAvatarSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Блок c: Смена пароля
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordPending, setPasswordPending] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    if (!login) return;
    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);

    profileApi
      .get(login, controller.signal)
      .then((data) => {
        setProfile(data);
        setBio(data.bio ?? "");
      })
      .catch((err) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setLoadError(err instanceof Error ? err.message : "Не удалось загрузить профиль");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [login, reloadKey]);

  // Обработчик сохранения описания
  const isBioUnchanged = bio === (profile?.bio ?? "");

  async function handleBioSubmit(e: FormEvent) {
    e.preventDefault();
    if (isBioUnchanged) return;

    setBioPending(true);
    setBioError(null);
    setBioSuccess(null);
    try {
      const updated = await profileApi.updateBio(bio);
      setProfile(updated);
      setBio(updated.bio ?? "");
      setBioSuccess("Сохранено");
    } catch (cause) {
      setBioError(cause instanceof ApiError ? cause.message : "Не удалось сохранить описание");
    } finally {
      setBioPending(false);
    }
  }

  // Обработчик выбора файла аватара
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setAvatarError(null);
    setAvatarSuccess(null);
    const file = e.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      setAvatarError("Поддерживаются только форматы JPEG, PNG и WebP");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }

    if (file.size > MAX_AVATAR_SIZE) {
      setAvatarError("Файл не должен превышать 5 МБ");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  // Обработчик загрузки аватара
  async function handleUploadAvatar() {
    if (!selectedFile) return;

    setAvatarPending(true);
    setAvatarError(null);
    setAvatarSuccess(null);
    try {
      const res = await profileApi.uploadAvatar(selectedFile);
      setProfile((prev) => (prev ? { ...prev, avatar_url: res.avatar_url } : null));
      await refresh();
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setAvatarSuccess("Аватар обновлён");
    } catch (cause) {
      setAvatarError(
        cause instanceof ApiError ? cause.message : "Не удалось загрузить аватар",
      );
    } finally {
      setAvatarPending(false);
    }
  }

  // Обработчик удаления аватара
  async function handleDeleteAvatar() {
    setAvatarPending(true);
    setAvatarError(null);
    setAvatarSuccess(null);
    try {
      await profileApi.deleteAvatar();
      setProfile((prev) => (prev ? { ...prev, avatar_url: null } : null));
      await refresh();
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setAvatarSuccess("Аватар удалён");
    } catch (cause) {
      setAvatarError(
        cause instanceof ApiError ? cause.message : "Не удалось удалить аватар",
      );
    } finally {
      setAvatarPending(false);
    }
  }

  // Обработчик смены пароля
  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPasswordError(null);

    if (!currentPassword) {
      setPasswordError("Введите текущий пароль");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("Новый пароль должен быть не короче 8 символов");
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError("Новый пароль должен отличаться от текущего");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Пароли не совпадают");
      return;
    }

    setPasswordPending(true);
    try {
      await profileApi.changePassword(currentPassword, newPassword);
      clearSession();
      navigate("/login", { state: { passwordChanged: true } });
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 400) {
        setPasswordError("Неверный текущий пароль");
      } else if (cause instanceof ApiError) {
        setPasswordError(cause.message);
      } else {
        setPasswordError("Не удалось сменить пароль");
      }
    } finally {
      setPasswordPending(false);
    }
  }

  if (loading) {
    return (
      <section className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-3xl font-semibold text-shelf-900">Настройки профиля</h1>
        <p className="mt-1 text-sm text-shelf-600">
          Управление описанием, аватаром и паролем учётной записи.
        </p>
        <SettingsSkeleton />
      </section>
    );
  }

  if (loadError || !profile) {
    return (
      <section className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-semibold text-shelf-900">Не удалось загрузить настройки</h1>
        <p className="mt-2 text-sm text-shelf-600">{loadError ?? "Попробуйте ещё раз"}</p>
        <Button className="mt-6" onClick={() => setReloadKey((key) => key + 1)}>
          Повторить
        </Button>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-2xl px-4 py-10">
      <header>
        <h1 className="text-3xl font-semibold text-shelf-900">Настройки профиля</h1>
        <p className="mt-1 text-sm text-shelf-600">
          Управление описанием, аватаром и паролем учётной записи.
        </p>
      </header>

      <div className="mt-8 space-y-6">
        {/* Блок 1: Описание профиля */}
        <form
          className="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200"
          onSubmit={handleBioSubmit}
          noValidate
        >
          <div>
            <h2 className="text-lg font-semibold text-shelf-900">Описание профиля</h2>
            <p className="mt-0.5 text-sm text-shelf-600">
              Краткий рассказ о себе, который увидят другие пользователи в вашем профиле.
            </p>
          </div>

          {bioSuccess ? (
            <p
              className="rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700 ring-1 ring-green-200"
              role="status"
            >
              {bioSuccess}
            </p>
          ) : null}

          {bioError ? (
            <p
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200"
              role="alert"
            >
              {bioError}
            </p>
          ) : null}

          <div className="space-y-1.5">
            <label htmlFor="bio-textarea" className="block text-sm font-medium text-shelf-800">
              О себе
            </label>
            <textarea
              id="bio-textarea"
              rows={4}
              maxLength={500}
              value={bio}
              onChange={(e) => {
                setBio(e.target.value);
                setBioSuccess(null);
                setBioError(null);
              }}
              placeholder="Расскажите о любимых книгах, фильмах или сериалах…"
              className="w-full rounded-xl border border-shelf-300 bg-white px-3 py-2 text-sm text-shelf-900 placeholder:text-shelf-400 focus:border-accent-600 focus:outline-2 focus:outline-offset-2 focus:outline-accent-600"
            />
            <div className="flex justify-between text-xs text-shelf-500">
              <span>До 500 символов. Пустая строка удаляет описание.</span>
              <span>{bio.length}/500</span>
            </div>
          </div>

          <div>
            <Button type="submit" disabled={bioPending || isBioUnchanged}>
              {bioPending ? "Сохраняем…" : "Сохранить"}
            </Button>
          </div>
        </form>

        {/* Блок 2: Аватар */}
        <div className="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200">
          <div>
            <h2 className="text-lg font-semibold text-shelf-900">Аватар</h2>
            <p className="mt-0.5 text-sm text-shelf-600">
              Изображение для шапки и профиля. Поддерживаются JPEG, PNG и WebP до 5 МБ.
            </p>
          </div>

          {avatarSuccess ? (
            <p
              className="rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700 ring-1 ring-green-200"
              role="status"
            >
              {avatarSuccess}
            </p>
          ) : null}

          {avatarError ? (
            <p
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200"
              role="alert"
            >
              {avatarError}
            </p>
          ) : null}

          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={`Аватар @${profile.login}`}
                className="h-24 w-24 shrink-0 rounded-full object-cover ring-2 ring-shelf-200"
              />
            ) : (
              <div
                className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full bg-accent-600 text-3xl font-semibold text-white"
                aria-hidden
              >
                {profile.login.slice(0, 1).toUpperCase()}
              </div>
            )}

            <div className="flex-1 space-y-3">
              <div>
                <label htmlFor="avatar-file" className="sr-only">
                  Выбрать файл аватара
                </label>
                <input
                  ref={fileInputRef}
                  id="avatar-file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-shelf-700 file:mr-4 file:rounded-xl file:border-0 file:bg-shelf-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-shelf-800 hover:file:bg-shelf-200 focus:outline-hidden"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  type="button"
                  onClick={handleUploadAvatar}
                  disabled={!selectedFile || avatarPending}
                >
                  {avatarPending ? "Загружаем…" : "Загрузить"}
                </Button>

                {profile.avatar_url ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleDeleteAvatar}
                    disabled={avatarPending}
                  >
                    Удалить
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        {/* Блок 3: Смена пароля */}
        <form
          className="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-shelf-200"
          onSubmit={handlePasswordSubmit}
          noValidate
        >
          <div>
            <h2 className="text-lg font-semibold text-shelf-900">Смена пароля</h2>
            <p className="mt-0.5 text-sm text-shelf-600">
              После смены пароля все активные сессии на других устройствах будут завершены.
            </p>
          </div>

          {passwordError ? (
            <p
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200"
              role="alert"
            >
              {passwordError}
            </p>
          ) : null}

          <Field
            label="Текущий пароль"
            name="currentPassword"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => {
              setCurrentPassword(e.target.value);
              setPasswordError(null);
            }}
          />

          <Field
            label="Новый пароль"
            name="newPassword"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              setPasswordError(null);
            }}
            hint="Не менее 8 символов"
          />

          <Field
            label="Повторите новый пароль"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              setPasswordError(null);
            }}
          />

          <div>
            <Button type="submit" disabled={passwordPending}>
              {passwordPending ? "Сохраняем…" : "Сменить пароль"}
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}
