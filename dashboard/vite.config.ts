/// <reference types="vitest/config" />
import type { Connect } from "vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = "http://192.168.1.139";

/** В dev при открытии в адресной строке `/admin/...` уводим на SPA (`/dashboard/admin/...`), а не на прокси API. */
function redirectAdminHtmlToDashboardSpa(): {
  name: string;
  configureServer(server: { middlewares: Connect.Server }): void;
} {
  return {
    name: "redirect-admin-html-to-dashboard-spa",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const raw = req.url ?? "";
        const path = raw.split("?")[0] ?? "";
        if (req.method !== "GET" || !path.startsWith("/admin")) {
          next();
          return;
        }
        const dest = (req.headers["sec-fetch-dest"] ?? "").toLowerCase();
        if (dest !== "document") {
          next();
          return;
        }
        res.statusCode = 302;
        res.setHeader("Location", `/dashboard${raw}`);
        res.end();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), redirectAdminHtmlToDashboardSpa()],
  base: "/dashboard/",
  test: {
    environment: "node",
    restoreMocks: true,
    clearMocks: true,
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/auth": { target: api, changeOrigin: true },
      "/users": { target: api, changeOrigin: true },
      "/balance": { target: api, changeOrigin: true },
      "/history": { target: api, changeOrigin: true },
      "/predict": { target: api, changeOrigin: true },
      "/admin": { target: api, changeOrigin: true },
    },
  },
});
