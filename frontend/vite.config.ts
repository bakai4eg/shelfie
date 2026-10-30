import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    // Удобно для локальной разработки: /api уходит на бэкенд без настройки CORS.
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
      // Аватарки и обложки каталога отдаёт FastAPI (/media), не Vite.
      "/media": {
        target: process.env.VITE_BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
