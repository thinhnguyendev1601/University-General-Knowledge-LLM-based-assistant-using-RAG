import type {
  AuthResponse,
  MessageResponse,
  RegisterCredentials,
} from '@/types'
import { httpClient } from './httpClient'
import { demoAccounts } from '@/mocks/demoAccounts'

export const getDemoAccounts = () => demoAccounts

export const login = (email: string, password: string) =>
  httpClient.post<AuthResponse>('/auth/login', { email, password })
export const getCurrentUser = () => httpClient.get<AuthResponse>('/auth/me')
export const logout = () => httpClient.post<void>('/auth/logout', {})
export const registerAccount = (body: RegisterCredentials) =>
  httpClient.post<MessageResponse>('/auth/register', body)
export const forgotPassword = (email: string) =>
  httpClient.post<MessageResponse>('/auth/forgot-password', { email })
export const resetPassword = (token: string, password: string) =>
  httpClient.post<MessageResponse>('/auth/reset-password', { token, password })
