/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Tỷ lệ mô phỏng lỗi mạng cho mock chat (0..1). Chỉ dùng khi dev. */
  readonly VITE_MOCK_ERROR_RATE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
