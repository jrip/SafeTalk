/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = "http://192.168.1.139";

export default defineConfig({
  plugins: [react()],
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
    },
  },
});
