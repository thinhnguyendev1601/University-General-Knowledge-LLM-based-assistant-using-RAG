/**
 * RequireAuth — bọc route cần đăng nhập.
 * Chuyển hướng về /login nếu chưa xác thực.
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from './authStore'

interface RequireAuthProps {
  children: React.ReactNode
}

export function RequireAuth({ children }: RequireAuthProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
