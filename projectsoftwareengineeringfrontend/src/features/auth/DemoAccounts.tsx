/**
 * DemoAccounts — hiển thị tài khoản thử nghiệm khi chưa có backend.
 * Dữ liệu đến từ services/, không hardcode trong component.
 */
import { getDemoAccounts } from '@/services'
import styles from './LoginForm.module.css'

export function DemoAccounts() {
  const accounts = getDemoAccounts()

  if (accounts.length === 0) return null

  return (
    <>
      <div className={styles.divider}>
        <span className={styles.dividerLine} />
        <span className={styles.dividerText}>Tài khoản thử nghiệm</span>
        <span className={styles.dividerLine} />
      </div>

      <div className={styles.demoInfo}>
        {accounts.map((account) => (
          <p key={account.email}>
            <span className={styles.demoLabel}>
              {account.role === 'admin' ? 'Admin:' : 'User:'}
            </span>{' '}
            {account.email} / {account.password}
          </p>
        ))}
      </div>
    </>
  )
}
