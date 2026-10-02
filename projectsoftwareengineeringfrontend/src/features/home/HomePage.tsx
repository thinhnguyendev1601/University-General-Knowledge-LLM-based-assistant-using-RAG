/**
 * HomePage — landing page tối giản.
 * Tên trường, slogan, CTA mở chat widget.
 */
import { useUIStore } from '@/hooks/useUIStore'
import { Button } from '@/components/ui'
import styles from './HomePage.module.css'

export function HomePage() {
  const openChat = useUIStore((state) => state.openChat)

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.heroIcon}>
            <svg
              className={styles.heroIconSvg}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
              <path d="M6 12v5c3 3 9 3 12 0v-5" />
            </svg>
          </div>

          <h1 className={styles.heroTitle}>Trợ lý Hỏi đáp Đại học</h1>

          <p className={styles.heroSubtitle}>
            Giải đáp mọi thắc mắc về lịch học, học bổng, thủ tục, quy chế —
            nhanh chóng và chính xác.
          </p>

          <Button
            size="lg"
            onClick={openChat}
            className={styles.heroCta}
            id="hero-open-chat-btn"
          >
            <svg
              className={styles.heroCtaIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            Hỏi ngay
          </Button>

          <div className={styles.features}>
            <div className={styles.featureCard}>
              <svg
                className={styles.featureIcon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <div className={styles.featureTitle}>Lịch học & Lịch thi</div>
              <div className={styles.featureDesc}>
                Tra cứu lịch học, lịch thi, thời khoá biểu
              </div>
            </div>

            <div className={styles.featureCard}>
              <svg
                className={styles.featureIcon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
              <div className={styles.featureTitle}>Quy chế & Thủ tục</div>
              <div className={styles.featureDesc}>
                Thông tin quy chế, hướng dẫn thủ tục hành chính
              </div>
            </div>

            <div className={styles.featureCard}>
              <svg
                className={styles.featureIcon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="12" cy="8" r="7" />
                <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
              </svg>
              <div className={styles.featureTitle}>Học bổng</div>
              <div className={styles.featureDesc}>
                Điều kiện, hồ sơ, thời hạn đăng ký học bổng
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        © 2025 Trợ lý Hỏi đáp Đại học. Mọi quyền được bảo lưu.
      </footer>
    </div>
  )
}
