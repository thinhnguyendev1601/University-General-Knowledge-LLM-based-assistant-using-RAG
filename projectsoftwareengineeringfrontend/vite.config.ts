import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  // dev: /api/* -> FastAPI (uvicorn api.app:app --port 8000, chạy ở thư mục gốc repo)
  server: {
    strictPort: true,
    proxy: { '/api': process.env.VITE_API_TARGET || 'http://127.0.0.1:8000' },
  },
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
