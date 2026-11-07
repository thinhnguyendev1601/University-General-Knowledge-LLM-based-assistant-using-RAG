import { Link } from 'react-router-dom'
import styles from './LoginForm.module.css'

interface AuthPanelProps {
  title: string
  description: string
  children: React.ReactNode
}

export function AuthPanel({ title, description, children }: AuthPanelProps) {
  return (
    <main className={styles.container}>
      <section className={styles.card} aria-label={title}>
        <div className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{description}</p>
        </div>
        {children}
        <nav className={styles.authLinks} aria-label="Tài khoản">
          <Link to="/login">Đăng nhập</Link>
          <Link to="/register">Đăng ký</Link>
        </nav>
      </section>
    </main>
  )
}
