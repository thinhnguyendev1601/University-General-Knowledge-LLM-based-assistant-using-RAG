/**
 * UI store — chỉ cho UI state: mở/đóng chat, theme.
 * Không chứa dữ liệu nghiệp vụ.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark'

interface UIState {
  theme: Theme
  isChatOpen: boolean
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  openChat: () => void
  closeChat: () => void
  toggleChat: () => void
}

/**
 * Phát hiện preference hệ thống khi chưa có lựa chọn user.
 */
function getSystemTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: getSystemTheme(),
      isChatOpen: false,

      toggleTheme: () => {
        const newTheme = get().theme === 'light' ? 'dark' : 'light'
        document.documentElement.setAttribute('data-theme', newTheme)
        set({ theme: newTheme })
      },

      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme)
        set({ theme })
      },

      openChat: () => set({ isChatOpen: true }),
      closeChat: () => set({ isChatOpen: false }),
      toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),
    }),
    {
      name: 'ui-storage',
      // Chỉ persist theme, không persist trạng thái chat
      partialize: (state) => ({ theme: state.theme }),
    }
  )
)
