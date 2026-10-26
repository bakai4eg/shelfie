import { Route, Routes } from "react-router-dom";

import Layout from "@/components/layout/Layout";
import AuthProvider from "@/features/auth/AuthProvider";
import { RequireAuth, RequireRole } from "@/features/auth/guards";
import AdminPage from "@/pages/AdminPage";
import CatalogPage from "@/pages/CatalogPage";
import FeedPage from "@/pages/FeedPage";
import HomePage from "@/pages/HomePage";
import ItemPage from "@/pages/ItemPage";
import LibraryPage from "@/pages/LibraryPage";
import ListPage from "@/pages/ListPage";
import LoginPage from "@/pages/LoginPage";
import ModerationPage from "@/pages/ModerationPage";
import NotFoundPage from "@/pages/NotFoundPage";
import ProfilePage from "@/pages/ProfilePage";
import RegisterPage from "@/pages/RegisterPage";
import ReviewPage from "@/pages/ReviewPage";
import SettingsPage from "@/pages/SettingsPage";

/**
 * Маршруты приложения. Публичные экраны открыты гостю, закрытые обёрнуты
 * в RequireAuth/RequireRole: гость уходит на /login с запоминанием адреса.
 */
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="catalog/:itemId" element={<ItemPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="u/:login" element={<ProfilePage />} />
          <Route
            path="settings"
            element={
              <RequireAuth>
                <SettingsPage />
              </RequireAuth>
            }
          />
          <Route
            path="my/library"
            element={
              <RequireAuth>
                <LibraryPage />
              </RequireAuth>
            }
          />
          <Route path="lists/:listId" element={<ListPage />} />
          <Route path="reviews/:reviewId" element={<ReviewPage />} />
          <Route
            path="feed"
            element={
              <RequireAuth>
                <FeedPage />
              </RequireAuth>
            }
          />
          <Route
            path="moderation"
            element={
              <RequireRole role="moderator">
                <ModerationPage />
              </RequireRole>
            }
          />
          <Route
            path="admin"
            element={
              <RequireRole role="admin">
                <AdminPage />
              </RequireRole>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
