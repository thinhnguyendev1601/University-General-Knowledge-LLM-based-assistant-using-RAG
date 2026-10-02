/**
 * ChatSidebar — danh sách lịch sử hội thoại.
 * Chọn, xoá từng hội thoại, tạo mới, xoá tất cả.
 */
import type { ChatConversation } from '@/types'
import { formatDate } from '@/utils'
import { Button } from '@/components/ui'
import styles from './ChatWidget.module.css'

interface ChatSidebarProps {
  conversations: ChatConversation[]
  activeConversationId: string | null
  onClose: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onCreate: () => void
  onDeleteAll: () => void
}

export function ChatSidebar({
  conversations,
  activeConversationId,
  onClose,
  onSelect,
  onDelete,
  onCreate,
  onDeleteAll,
}: ChatSidebarProps) {
  return (
    <div className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <span className={styles.sidebarTitle}>Lịch sử hội thoại</span>
        <button
          className={styles.iconBtn}
          onClick={onClose}
          aria-label="Đóng sidebar"
          id="close-sidebar-btn"
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

      {conversations.length === 0 ? (
        <div className={styles.sidebarEmpty}>Chưa có hội thoại nào</div>
      ) : (
        <div className={styles.sidebarList}>
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`${styles.sidebarItem} ${conversation.id === activeConversationId ? styles.sidebarItemActive : ''}`}
              onClick={() => onSelect(conversation.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') onSelect(conversation.id)
              }}
              role="button"
              tabIndex={0}
            >
              <span className={styles.sidebarItemTitle}>
                {conversation.title}
              </span>
              <span className={styles.sidebarItemDate}>
                {formatDate(conversation.updatedAt)}
              </span>
              <button
                className={styles.sidebarItemDelete}
                onClick={(event) => {
                  // Chặn click nổi lên item cha để không chọn hội thoại vừa xoá
                  event.stopPropagation()
                  onDelete(conversation.id)
                }}
                aria-label={`Xoá hội thoại ${conversation.title}`}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      <div className={styles.sidebarFooter}>
        <Button
          size="sm"
          onClick={onCreate}
          fullWidth
          id="new-conversation-btn"
        >
          Hội thoại mới
        </Button>
        {conversations.length > 0 && (
          <Button
            size="sm"
            variant="danger"
            onClick={onDeleteAll}
            id="delete-all-conversations-btn"
          >
            Xoá tất cả
          </Button>
        )}
      </div>
    </div>
  )
}
