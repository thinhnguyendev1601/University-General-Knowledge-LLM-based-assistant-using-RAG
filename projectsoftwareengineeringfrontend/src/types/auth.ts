// Vai trò người dùng trong hệ thống
export type Role = 'admin' | 'user'

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface AuthResponse {
  user: User
  csrfToken: string
  expiresAt: string
}

export interface RegisterCredentials {
  name: string
  email: string
  password: string
}

export interface MessageResponse {
  message: string
}

export interface LoginCredentials {
  email: string
  password: string
}
