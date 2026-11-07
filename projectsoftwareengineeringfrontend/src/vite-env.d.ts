/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Tỷ lệ mô phỏng lỗi mạng cho mock chat (0..1). Chỉ dùng khi dev. */
  readonly VITE_MOCK_ERROR_RATE?: string
  /** 'true' = chat dùng mock thay vì backend RAG thật. */
  readonly VITE_USE_MOCK_CHAT?: string
  /** Timeout (ms) cho một câu trả lời chat; mặc định 180000. */
  readonly VITE_CHAT_TIMEOUT_MS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
