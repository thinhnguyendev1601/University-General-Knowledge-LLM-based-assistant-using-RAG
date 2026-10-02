/**
 * ChatMessages — danh sách tin nhắn, empty state, typing indicator, lỗi + thử lại.
 * Auto-scroll xuống cuối mỗi khi có tin mới hoặc trạng thái chờ đổi.
 */
import { useRef, useEffect } from 'react'
import type { ChatMessage } from '@/types'
import { formatDate } from '@/utils'
import styles from './ChatWidget.module.css'

interface ChatMessagesProps {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

export function ChatMessages({
  messages,
  isLoading,
  error,
  onRetry,
}: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isLoading, error])

  const isEmpty = messages.length === 0 && !isLoading && !error

  return (
    <div className={styles.chatMessages} id="chat-messages">
      {isEmpty ? (
        <div className={styles.emptyState}>
          <svg
            className={styles.emptyIcon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <div className={styles.emptyTitle}>Xin chào!</div>
          <div className={styles.emptyText}>
            Tôi là trợ lý ảo của trường Đại học. Hãy hỏi tôi bất cứ điều gì về
            lịch học, học bổng, thủ tục, quy chế...
          </div>
        </div>
      ) : (
        <>
          {messages.map((message) => {
            const isUser = message.role === 'user'
            return (
              <div key={message.id}>
                <div
                  className={`${styles.messageBubble} ${isUser ? styles.messageUser : styles.messageAssistant}`}
                >
                  {message.content}
                </div>
                <div
                  className={`${styles.messageTime} ${isUser ? styles.messageTimeUser : styles.messageTimeAssistant}`}
                >
                  {formatDate(message.createdAt)}
                </div>
              </div>
            )
          })}

          {isLoading && (
            <div className={styles.typingIndicator} aria-live="polite">
              <div className={styles.typingDots}>
                <span className={styles.typingDot} />
                <span className={styles.typingDot} />
                <span className={styles.typingDot} />
              </div>
              <span className={styles.typingText}>Đang trả lời...</span>
            </div>
          )}

          {error && (
            <div className={styles.messageError} role="alert">
              <span>{error}</span>
              <button
                className={styles.retryBtn}
                onClick={onRetry}
                id="retry-btn"
              >
                Thử lại
              </button>
            </div>
          )}
        </>
      )}
      <div ref={endRef} />
    </div>
  )
}
