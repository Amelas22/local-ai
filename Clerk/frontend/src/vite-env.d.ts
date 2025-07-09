/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_AUTH_ENABLED: string
  readonly VITE_MOCK_API: string
  readonly VITE_LOG_LEVEL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}