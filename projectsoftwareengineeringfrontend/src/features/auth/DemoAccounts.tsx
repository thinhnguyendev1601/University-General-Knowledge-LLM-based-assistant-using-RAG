import { getDemoAccounts } from '@/services'
import styles from './LoginForm.module.css'

export function DemoAccounts() {
  return (
    <aside className={styles.demoInfo} aria-label="Thông tin tài khoản demo">
      {getDemoAccounts().map((account) => (
        <p key={account.role}>
          <span className={styles.demoLabel}>
            Demo {account.role === 'admin' ? 'Admin' : 'User'}:
          </span>{' '}
          {account.email} / {account.password}
        </p>
      ))}
    </aside>
  )
}
