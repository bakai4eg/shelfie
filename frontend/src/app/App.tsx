import { Route, Routes } from "react-router-dom";

import Layout from "@/components/layout/Layout";
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
 * Маршруты приложения. Каждая страница-заглушка знает, какая задача её наполняет.
 * Закрытые маршруты появятся вместе с AuthProvider (T1.1).
 */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="catalog/:itemId" element={<ItemPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="u/:login" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="my/library" element={<LibraryPage />} />
        <Route path="lists/:listId" element={<ListPage />} />
        <Route path="reviews/:reviewId" element={<ReviewPage />} />
        <Route path="feed" element={<FeedPage />} />
        <Route path="moderation" element={<ModerationPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
