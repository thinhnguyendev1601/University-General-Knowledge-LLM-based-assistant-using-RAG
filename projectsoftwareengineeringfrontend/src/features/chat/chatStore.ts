/** A per-session memory view of server history. No chat content is persisted locally. */
import { create } from 'zustand'
import type { ChatConversation, ChatMessage } from '@/types'

interface ChatState {
  ownerId: string | null
  sessionVersion: number
  conversations: ChatConversation[]
  messages: Record<string, ChatMessage[]>
  activeConversationId: string | null
  isLoading: boolean
  historyLoading: boolean
  messagesLoadingId: string | null
  error: string | null
  errorRequestId: string | null
  retryAt: number
  pendingConversationId: string | null
  setActiveConversation: (id: string | null) => void
  upsertConversation: (conversation: ChatConversation) => void
  mergeMessages: (id: string, messages: ChatMessage[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useChatStore = create<ChatState>()((set) => ({
  ownerId: null,
  sessionVersion: 0,
  conversations: [],
  messages: {},
  activeConversationId: null,
  isLoading: false,
  historyLoading: false,
  messagesLoadingId: null,
  error: null,
  errorRequestId: null,
  retryAt: 0,
  pendingConversationId: null,
  setActiveConversation: (id) => set({ activeConversationId: id, error: null }),
  upsertConversation: (conversation) =>
    set((state) => {
      const previous = state.conversations.find(
        (item) => item.id === conversation.id
      )
      if (previous && previous.updatedAt > conversation.updatedAt) return state
      return {
        conversations: [
          conversation,
          ...state.conversations.filter((item) => item.id !== conversation.id),
        ].sort(
          (a, b) =>
            b.updatedAt.localeCompare(a.updatedAt) || b.id.localeCompare(a.id)
        ),
      }
    }),
  mergeMessages: (id, incoming) =>
    set((state) => {
      const merged = [...(state.messages[id] ?? [])]
      for (const message of incoming) {
        const index = merged.findIndex(
          (item) =>
            item.id === message.id ||
            (message.requestId &&
              item.requestId === message.requestId &&
              item.role === message.role)
        )
        if (index >= 0) merged[index] = message
        else merged.push(message)
      }
      merged.sort((a, b) =>
        a.sequence !== undefined && b.sequence !== undefined
          ? a.sequence - b.sequence
          : 0
      )
      return { messages: { ...state.messages, [id]: merged } }
    }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}))

// Old local IDs were never created on the server and cannot be treated as server IDs.
// Existing local history is ignored, rather than silently imported or erased.
window.addEventListener('auth-user-changed', (event) => {
  const ownerId = (event as CustomEvent<string | null>).detail
  const previous = useChatStore.getState()
  if (ownerId !== previous.ownerId || ownerId === null) {
    useChatStore.setState({
      ownerId,
      sessionVersion: previous.sessionVersion + 1,
      conversations: [],
      messages: {},
      activeConversationId: null,
      isLoading: false,
      historyLoading: false,
      messagesLoadingId: null,
      error: null,
      errorRequestId: null,
      retryAt: 0,
      pendingConversationId: null,
    })
  }
})
