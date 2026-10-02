/**
 * RequireRole — bọc route cần role cụ thể.
 * Chuyển hướng về trang chủ nếu không có quyền.
 */
import { Navigate } from 'react-router-dom'
import { useAuthStore } from './authStore'
import type { Role } from '@/types'

interface RequireRoleProps {
  role: Role
  children: React.ReactNode
}

export function RequireRole({ role, children }: RequireRoleProps) {
  const user = useAuthStore((state) => state.user)

  if (!user || user.role !== role) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
