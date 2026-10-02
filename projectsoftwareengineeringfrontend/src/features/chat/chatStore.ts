/**
 * Chat store — quản lý hội thoại và tin nhắn.
 * Lưu vào localStorage để khôi phục khi reload.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ChatConversation, ChatMessage } from '@/types'
import { generateId, generateConversationTitle } from '@/utils'

/**
 * Cập nhật 1 hội thoại và đưa lên đầu danh sách.
 * Sidebar render theo thứ tự mảng nên hội thoại vừa có tin mới luôn ở trên.
 */
function touchConversation(
  conversations: ChatConversation[],
  id: string,
  patch: Partial<ChatConversation> = {}
): ChatConversation[] {
  const target = conversations.find((conv) => conv.id === id)
  if (!target) return conversations

  const updated: ChatConversation = {
    ...target,
    ...patch,
    updatedAt: new Date().toISOString(),
  }
  return [updated, ...conversations.filter((conv) => conv.id !== id)]
}

interface ChatState {
  conversations: ChatConversation[]
  messages: Record<string, ChatMessage[]>
  activeConversationId: string | null
  isLoading: boolean
  error: string | null

  // Actions
  setActiveConversation: (id: string | null) => void
  createConversation: () => string
  deleteConversation: (id: string) => void
  deleteAllConversations: () => void
  addUserMessage: (conversationId: string, content: string) => ChatMessage
  addAssistantMessage: (conversationId: string, message: ChatMessage) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  updateConversationTitle: (id: string, title: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      messages: {},
      activeConversationId: null,
      isLoading: false,
      error: null,

      setActiveConversation: (id) =>
        set({ activeConversationId: id, error: null }),

      createConversation: () => {
        const id = generateId()
        const newConversation: ChatConversation = {
          id,
          title: 'Hội thoại mới',
          updatedAt: new Date().toISOString(),
        }
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          messages: { ...state.messages, [id]: [] },
          activeConversationId: id,
          error: null,
        }))
        return id
      },

      deleteConversation: (id) =>
        set((state) => {
          const newMessages = { ...state.messages }
          delete newMessages[id]
          const newConversations = state.conversations.filter(
            (conv) => conv.id !== id
          )
          return {
            conversations: newConversations,
            messages: newMessages,
            activeConversationId:
              state.activeConversationId === id
                ? (newConversations[0]?.id ?? null)
                : state.activeConversationId,
          }
        }),

      deleteAllConversations: () =>
        set({
          conversations: [],
          messages: {},
          activeConversationId: null,
        }),

      addUserMessage: (conversationId, content) => {
        const message: ChatMessage = {
          id: generateId(),
          conversationId,
          role: 'user',
          content,
          createdAt: new Date().toISOString(),
        }

        const state = get()
        const currentMessages = state.messages[conversationId] ?? []
        const isFirstMessage = currentMessages.length === 0

        set((prev) => ({
          messages: {
            ...prev.messages,
            [conversationId]: [
              ...(prev.messages[conversationId] ?? []),
              message,
            ],
          },
          // Đổi tên tự động từ câu hỏi đầu tiên
          conversations: touchConversation(
            prev.conversations,
            conversationId,
            isFirstMessage ? { title: generateConversationTitle(content) } : {}
          ),
        }))

        return message
      },

      addAssistantMessage: (conversationId, message) =>
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]: [
              ...(state.messages[conversationId] ?? []),
              message,
            ],
          },
          conversations: touchConversation(state.conversations, conversationId),
        })),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      updateConversationTitle: (id, title) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, title } : conv
          ),
        })),
    }),
    {
      name: 'chat-storage',
      // Không persist trạng thái loading/error
      partialize: (state) => ({
        conversations: state.conversations,
        messages: state.messages,
        activeConversationId: state.activeConversationId,
      }),
    }
  )
)
