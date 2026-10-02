/**
 * AdminPage — trang quản lý dữ liệu cho admin.
 * Hiện chỉ là placeholder (xem BACKEND_BLOCKED_FEATURES.md).
 */
import { Header } from '@/components/Header'
import { ChatWidget } from '@/features/chat'
import styles from './AdminPage.module.css'

export function AdminPage() {
  return (
    <>
      <Header />
      <div className={styles.container}>
        <div className={styles.content}>
          <div className={styles.iconWrapper}>
            <svg
              className={styles.icon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className={styles.title}>Quản lý dữ liệu</h1>
          <p className={styles.description}>
            Trang quản trị dữ liệu đang trong quá trình phát triển. Khi backend
            sẵn sàng, bạn sẽ có thể quản lý FAQ, lịch học, quy chế, học bổng và
            các thông tin khác tại đây.
          </p>
          <div className={styles.badge}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Chờ Backend
          </div>
        </div>
      </div>
      <ChatWidget />
    </>
  )
}
