import type { Role } from '@/types'

export interface DemoAccount {
  role: Role
  email: string
  password: string
}

/** Legacy sample credentials for display; they do not bypass server authentication. */
export const demoAccounts: readonly DemoAccount[] = [
  { role: 'admin', email: 'admin@university.edu.vn', password: 'admin123' },
  { role: 'user', email: 'user@university.edu.vn', password: 'user123' },
]
