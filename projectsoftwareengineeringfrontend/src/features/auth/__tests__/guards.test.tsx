import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { RequireAuth } from '../RequireAuth'
import { RequireRole } from '../RequireRole'
import { useAuthStore } from '../authStore'
import type { Role } from '@/types'

function signIn(role: Role) {
  useAuthStore.getState().setAuth({
    csrfToken: 'csrf',
    expiresAt: '2030-01-01T00:00:00Z',
    user: {
      id: 'usr-001',
      name: 'Người dùng',
      email: 'a@university.edu.vn',
      role,
    },
  })
}

/** Dựng router tối giản với 3 route để quan sát điều hướng. */
function renderRoutes(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Trang đăng nhập</div>} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <div>Trang chủ</div>
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <RequireRole role="admin">
                <div>Trang quản trị</div>
              </RequireRole>
            </RequireAuth>
          }
        />
      </Routes>
    </MemoryRouter>
  )
}

describe('RequireAuth', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('chuyển về /login khi chưa đăng nhập', () => {
    renderRoutes('/')
    expect(screen.getByText('Trang đăng nhập')).toBeInTheDocument()
    expect(screen.queryByText('Trang chủ')).not.toBeInTheDocument()
  })

  it('cho vào trang khi đã đăng nhập', () => {
    signIn('user')
    renderRoutes('/')
    expect(screen.getByText('Trang chủ')).toBeInTheDocument()
  })

  it('không tin trạng thái đăng nhập giả trong localStorage', () => {
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: { isAuthenticated: true, user: { role: 'admin' } },
      })
    )
    renderRoutes('/admin')
    expect(screen.getByText('Trang đăng nhập')).toBeInTheDocument()
  })
})

describe('RequireRole', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('chuyển user thường khỏi /admin về trang chủ', () => {
    signIn('user')
    renderRoutes('/admin')

    expect(screen.getByText('Trang chủ')).toBeInTheDocument()
    expect(screen.queryByText('Trang quản trị')).not.toBeInTheDocument()
  })

  it('cho admin vào /admin', () => {
    signIn('admin')
    renderRoutes('/admin')
    expect(screen.getByText('Trang quản trị')).toBeInTheDocument()
  })

  it('chưa đăng nhập vào /admin thì về /login', () => {
    renderRoutes('/admin')
    expect(screen.getByText('Trang đăng nhập')).toBeInTheDocument()
  })
})
