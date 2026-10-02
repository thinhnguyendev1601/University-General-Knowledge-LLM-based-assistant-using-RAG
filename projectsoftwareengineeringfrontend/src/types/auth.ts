// Vai trò người dùng trong hệ thống
export type Role = 'admin' | 'user'

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface AuthResponse {
  token: string
  refreshToken: string
  user: User
}

export interface LoginCredentials {
  email: string
  password: string
}
