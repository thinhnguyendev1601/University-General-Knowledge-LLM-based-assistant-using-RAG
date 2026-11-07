import { create } from 'zustand'
import type { AuthResponse, User } from '@/types'
import { ApiError, getCurrentUser, logout as endSession } from '@/services'
import { setCsrfToken } from '@/services/httpClient'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  initializationError: string | null
  setAuth: (response: AuthResponse) => void
  clearAuth: () => void
  initialize: () => Promise<void>
  logout: () => Promise<void>
}

let initialization: Promise<void> | null = null

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  initializationError: null,
  setAuth: (response) => {
    setCsrfToken(response.csrfToken)
    window.dispatchEvent(
      new CustomEvent('auth-user-changed', { detail: response.user.id })
    )
    set({
      user: response.user,
      isAuthenticated: true,
      isLoading: false,
      initializationError: null,
    })
  },
  clearAuth: () => {
    setCsrfToken(null)
    window.dispatchEvent(new CustomEvent('auth-user-changed', { detail: null }))
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      initializationError: null,
    })
  },
  initialize: () => {
    if (initialization) return initialization
    localStorage.removeItem('auth-storage')
    set({ isLoading: true, initializationError: null })
    initialization = getCurrentUser()
      .then((response) => get().setAuth(response))
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          get().clearAuth()
        } else {
          set({
            isLoading: false,
            initializationError:
              'Không thể kiểm tra phiên đăng nhập. Vui lòng thử lại.',
          })
        }
      })
      .finally(() => {
        initialization = null
      })
    return initialization
  },
  logout: async () => {
    try {
      await endSession()
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) throw error
    }
    get().clearAuth()
  },
}))

window.addEventListener('auth-expired', () =>
  useAuthStore.getState().clearAuth()
)
