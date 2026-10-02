/**
 * ChatHeader — header của panel chat: tên trợ lý, nút lịch sử / tạo mới / đóng.
 */
import styles from './ChatWidget.module.css'

interface ChatHeaderProps {
  onOpenSidebar: () => void
  onNewConversation: () => void
  onClose: () => void
}

export function ChatHeader({
  onOpenSidebar,
  onNewConversation,
  onClose,
}: ChatHeaderProps) {
  return (
    <div className={styles.chatHeader}>
      <div className={styles.chatHeaderInfo}>
        <div className={styles.chatAvatar}>
          <svg
            className={styles.chatAvatarIcon}
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
        <div>
          <div className={styles.chatHeaderTitle}>Trợ lý Đại học</div>
          <div className={styles.chatHeaderStatus}>
            <span className={styles.statusDot} />
            Trực tuyến
          </div>
        </div>
      </div>

      <div className={styles.chatHeaderActions}>
        <button
          className={styles.iconBtn}
          onClick={onOpenSidebar}
          aria-label="Lịch sử hội thoại"
          id="open-sidebar-btn"
        >
          <svg
            className={styles.iconBtnSvg}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <button
          className={styles.iconBtn}
          onClick={onNewConversation}
          aria-label="Tạo hội thoại mới"
          id="new-chat-btn"
        >
          <svg
            className={styles.iconBtnSvg}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <button
          className={styles.iconBtn}
          onClick={onClose}
          aria-label="Đóng chat"
          id="close-chat-btn"
        >
          <svg
            className={styles.iconBtnSvg}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  )
}
