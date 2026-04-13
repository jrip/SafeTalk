/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Полный origin API, например `http://127.0.0.1:8000`. Пусто — те же хост/путь, что у фронта (proxy/nginx). */
  readonly VITE_API_ORIGIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
