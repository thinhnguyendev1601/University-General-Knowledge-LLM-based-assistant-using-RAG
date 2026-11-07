import { useEffect } from 'react'
import { Button } from '@/components/ui'
import { useAuthStore } from './authStore'
import styles from './LoginForm.module.css'

interface AuthBootstrapProps {
  children: React.ReactNode
}

export function AuthBootstrap({ children }: AuthBootstrapProps) {
  const { isLoading, initializationError, initialize } = useAuthStore()
  useEffect(() => {
    void initialize()
  }, [initialize])
  if (isLoading) return <p role="status">Đang kiểm tra phiên đăng nhập...</p>
  if (initializationError) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <p role="alert">{initializationError}</p>
          <Button onClick={() => void initialize()}>Thử lại</Button>
        </div>
      </div>
    )
  }
  return <>{children}</>
}
