/**
 * ChatWidget — widget chat cố định góc phải dưới.
 * Ghép nút tròn thu gọn + panel trượt (header, sidebar, danh sách tin, ô nhập).
 */
import { useState } from 'react'
import { useUIStore } from '@/hooks/useUIStore'
import { useChatStore } from './chatStore'
import { useChat } from './useChat'
import {
  createServerConversation,
  deleteServerConversation,
  deleteServerConversations,
  loadHistory,
  renameServerConversation,
} from './chatHistory'
import { ChatHeader } from './ChatHeader'
import { ChatSidebar } from './ChatSidebar'
import { ChatMessages } from './ChatMessages'
import { ChatInput } from './ChatInput'
import styles from './ChatWidget.module.css'

export function ChatWidget() {
  const isChatOpen = useUIStore((state) => state.isChatOpen)
  const toggleChat = useUIStore((state) => state.toggleChat)
  const closeChat = useUIStore((state) => state.closeChat)

  const conversations = useChatStore((state) => state.conversations)
  const messages = useChatStore((state) => state.messages)
  const activeConversationId = useChatStore(
    (state) => state.activeConversationId
  )
  const error = useChatStore((state) => state.error)
  const setActiveConversation = useChatStore(
    (state) => state.setActiveConversation
  )
  const historyLoading = useChatStore((state) => state.historyLoading)
  const pendingId = useChatStore((state) => state.pendingConversationId)
  const retryAt = useChatStore((state) => state.retryAt)
  const messagesLoadingId = useChatStore((state) => state.messagesLoadingId)

  const { send, retry, isLoading } = useChat(isChatOpen)
  const [showSidebar, setShowSidebar] = useState(false)

  const activeMessages = activeConversationId
    ? (messages[activeConversationId] ?? [])
    : []

  const handleNewConversation = () => {
    if (isLoading || historyLoading) return
    void createServerConversation()
    setShowSidebar(false)
  }

  const handleSelectConversation = (id: string) => {
    setActiveConversation(id)
    setShowSidebar(false)
  }

  return (
    <>
      {isChatOpen && (
        <div className={styles.chatPanel} id="chat-panel">
          {showSidebar && (
            <ChatSidebar
              conversations={conversations}
              activeConversationId={activeConversationId}
              onClose={() => setShowSidebar(false)}
              onSelect={handleSelectConversation}
              onDelete={(id) => void deleteServerConversation(id)}
              onCreate={handleNewConversation}
              onDeleteAll={() => void deleteServerConversations()}
              onRename={renameServerConversation}
              onRefresh={() => void loadHistory()}
              isLoading={historyLoading}
            />
          )}

          <ChatHeader
            onOpenSidebar={() => setShowSidebar(true)}
            onNewConversation={handleNewConversation}
            onClose={closeChat}
          />

          <ChatMessages
            messages={activeMessages}
            isLoading={isLoading && pendingId === activeConversationId}
            error={error}
            onRetry={retry}
            retryAt={retryAt}
            historyLoading={
              messagesLoadingId === activeConversationId &&
              activeConversationId !== null
            }
          />

          <ChatInput
            onSend={send}
            disabled={
              isLoading ||
              historyLoading ||
              (messagesLoadingId === activeConversationId &&
                activeConversationId !== null)
            }
          />
        </div>
      )}

      {!isChatOpen && (
        <button
          className={styles.chatToggle}
          onClick={toggleChat}
          data-open={isChatOpen}
          aria-label={isChatOpen ? 'Đóng chat' : 'Mở chat'}
          aria-expanded={isChatOpen}
          aria-controls="chat-panel"
          id="chat-toggle-btn"
        >
          {isChatOpen ? (
            <svg
              className={styles.chatToggleIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg
              className={styles.chatToggleIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          )}
        </button>
      )}
    </>
  )
}
