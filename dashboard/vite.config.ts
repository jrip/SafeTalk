/// <reference types="vitest/config" />
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Connect, Plugin } from "vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = "http://192.168.1.139";

const dashboardDir = path.dirname(fileURLToPath(import.meta.url));
const staticLandingPath = path.resolve(dashboardDir, "..", "static", "index.htm");

/** В dev `GET /` — та же статическая главная, что в Docker на `/` (`static/index.htm`). */
function serveRootStaticLanding(): Plugin {
  return {
    name: "serve-root-static-landing",
    enforce: "pre",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.method !== "GET") {
          next();
          return;
        }
        const raw = req.url ?? "";
        const pathname = raw.split("?")[0] ?? "";
        if (pathname !== "/" && pathname !== "") {
          next();
          return;
        }
        try {
          const html = fs.readFileSync(staticLandingPath, "utf-8");
          res.setHeader("Content-Type", "text/html; charset=utf-8");
          res.end(html);
        } catch {
          next();
        }
      });
    },
  };
}

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
        const urlPath = raw.split("?")[0] ?? "";
        if (req.method !== "GET" || !urlPath.startsWith("/admin")) {
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
  plugins: [serveRootStaticLanding(), react(), redirectAdminHtmlToDashboardSpa()],
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
      "/docs": { target: api, changeOrigin: true },
      "/openapi.json": { target: api, changeOrigin: true },
      "/docs-public": { target: api, changeOrigin: true },
      "/openapi-public.json": { target: api, changeOrigin: true },
      "/auth": { target: api, changeOrigin: true },
      "/users": { target: api, changeOrigin: true },
      "/balance": { target: api, changeOrigin: true },
      "/history": { target: api, changeOrigin: true },
      "/predict": { target: api, changeOrigin: true },
      "/admin": { target: api, changeOrigin: true },
    },
  },
});
