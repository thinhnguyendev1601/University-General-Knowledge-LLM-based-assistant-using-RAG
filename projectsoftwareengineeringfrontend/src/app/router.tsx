/**
 * AppRouter — khai báo toàn bộ route và lớp bảo vệ của chúng.
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { RequireAuth, RequireRole } from '@/features/auth'
import { LoginPage } from '@/pages/LoginPage'
import { HomePage } from '@/pages/HomePage'
import { AdminPage } from '@/pages/AdminPage'

export function AppRouter() {
  return (
    <Routes>
      {/* Login — không cần auth */}
      <Route path="/login" element={<LoginPage />} />

      {/* Trang chủ — cần đăng nhập */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        }
      />

      {/* Admin — cần role admin */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireRole role="admin">
              <AdminPage />
            </RequireRole>
          </RequireAuth>
        }
      />

      {/* Catch-all → redirect về trang chủ */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
