/**
 * Auth service — chỉ có network, không có business logic.
 * Hiện dùng mock; khi backend sẵn sàng thì đổi sang httpClient.
 */
import type { AuthResponse } from '@/types'
import { mockLogin, mockGetDemoAccounts, type DemoAccount } from '@/mocks'

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  // Khi có backend thật:
  // return httpClient.post<AuthResponse>('/auth/login', { email, password })
  return mockLogin(email, password)
}

/**
 * Tài khoản thử nghiệm để hiển thị ở trang login.
 * Trả về mảng rỗng khi đã có backend thật — khi đó không còn tài khoản demo.
 */
export function getDemoAccounts(): DemoAccount[] {
  return mockGetDemoAccounts()
}

export type { DemoAccount }
