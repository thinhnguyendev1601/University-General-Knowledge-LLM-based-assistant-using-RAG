/**
 * useChat — logic gửi tin & thử lại, tách khỏi phần render.
 * Giữ lại nội dung câu hỏi lỗi trong ref để nút "Thử lại" gửi lại được.
 */
import { useRef, useCallback } from 'react'
import { sendMessage } from '@/services'
import { useChatStore } from './chatStore'

const ERROR_MESSAGE = 'Không thể kết nối đến server. Vui lòng thử lại.'

export function useChat() {
  const activeConversationId = useChatStore(
    (state) => state.activeConversationId
  )
  const isLoading = useChatStore((state) => state.isLoading)
  const createConversation = useChatStore((state) => state.createConversation)
  const addUserMessage = useChatStore((state) => state.addUserMessage)
  const addAssistantMessage = useChatStore((state) => state.addAssistantMessage)
  const setLoading = useChatStore((state) => state.setLoading)
  const setError = useChatStore((state) => state.setError)

  // Câu hỏi chưa được trả lời — dùng để gửi lại khi bấm "Thử lại"
  const pendingMessage = useRef<string | null>(null)

  /** Gọi service và ghi câu trả lời vào store; trả về false nếu lỗi. */
  const requestReply = useCallback(
    async (conversationId: string, content: string) => {
      setError(null)
      setLoading(true)
      try {
        const reply = await sendMessage(conversationId, content)
        addAssistantMessage(conversationId, reply)
        pendingMessage.current = null
        return true
      } catch {
        setError(ERROR_MESSAGE)
        return false
      } finally {
        setLoading(false)
      }
    },
    [addAssistantMessage, setError, setLoading]
  )

  const send = useCallback(
    async (rawContent: string) => {
      const content = rawContent.trim()
      if (!content || isLoading) return false

      // Chưa có hội thoại nào đang mở thì tạo mới trước khi thêm tin
      const conversationId = activeConversationId ?? createConversation()

      addUserMessage(conversationId, content)
      pendingMessage.current = content
      return requestReply(conversationId, content)
    },
    [
      activeConversationId,
      addUserMessage,
      createConversation,
      isLoading,
      requestReply,
    ]
  )

  const retry = useCallback(async () => {
    const content = pendingMessage.current
    if (!content || !activeConversationId) return
    await requestReply(activeConversationId, content)
  }, [activeConversationId, requestReply])

  return { send, retry, isLoading }
}
