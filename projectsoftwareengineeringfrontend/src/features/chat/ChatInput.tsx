/**
 * ChatInput — ô nhập tin nhắn.
 * Enter gửi, Shift+Enter xuống dòng. Textarea tự giãn theo nội dung
 * nên paste text dài nhiều dòng không phá layout.
 */
import { useState, useRef } from 'react'
import styles from './ChatWidget.module.css'

const MAX_TEXTAREA_HEIGHT = 120

interface ChatInputProps {
  onSend: (content: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resize = () => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`
  }

  const handleSend = () => {
    if (!value.trim() || disabled) return
    onSend(value)
    // Chỉ xoá nội dung sau khi đã chuyển cho store — lỗi mạng không làm mất tin
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={styles.chatInputArea}>
      <div className={styles.chatInputWrapper}>
        <textarea
          ref={textareaRef}
          className={styles.chatTextarea}
          placeholder="Nhập câu hỏi..."
          value={value}
          onChange={(event) => {
            setValue(event.target.value)
            resize()
          }}
          onKeyDown={handleKeyDown}
          rows={1}
          id="chat-input"
          aria-label="Nhập tin nhắn"
        />
        <button
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          aria-label="Gửi tin nhắn"
          id="send-message-btn"
        >
          <svg
            className={styles.sendBtnIcon}
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
