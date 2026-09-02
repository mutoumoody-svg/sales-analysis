/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEV_HOST?: string;
  readonly VITE_DEV_PORT?: string;
  readonly VITE_API_PROXY_TARGET?: string;
  readonly VITE_PREVIEW_HOST?: string;
  readonly VITE_PREVIEW_PORT?: string;
  readonly VITE_ADMIN_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
