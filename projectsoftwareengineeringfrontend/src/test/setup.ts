/**
 * Vitest setup — chạy trước mỗi file test.
 * Thêm matcher của jest-dom và dọn DOM/localStorage giữa các test.
 */
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

// jsdom chưa có matchMedia — useUIStore cần nó để đọc prefers-color-scheme
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}

// jsdom chưa implement scrollIntoView — ChatWidget auto-scroll gọi hàm này
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}
