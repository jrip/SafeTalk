import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App, ConfigProvider } from "antd";
import ruRU from "antd/locale/ru_RU";
import dayjs from "dayjs";
import "dayjs/locale/ru";
import { getToken } from "./auth";
import { ClientProvider } from "./client/ClientContext";
import { createSafeTalkApiClient } from "./client/createSafeTalkApiClient";
import AppRoutes from "./App";
import { safetalkTheme } from "./safetalkTheme";
import "./main.css";

dayjs.locale("ru");

const apiClient = createSafeTalkApiClient({
  getAccessToken: getToken,
  apiOrigin: import.meta.env.VITE_API_ORIGIN ?? "",
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider locale={ruRU} theme={safetalkTheme}>
      <App>
        <ClientProvider client={apiClient}>
          <BrowserRouter basename="/dashboard">
            <AppRoutes />
          </BrowserRouter>
        </ClientProvider>
      </App>
    </ConfigProvider>
  </StrictMode>,
);
