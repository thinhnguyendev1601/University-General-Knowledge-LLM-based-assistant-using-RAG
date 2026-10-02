export interface ChatMessage {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string // ISO 8601
}

export interface ChatConversation {
  id: string
  title: string
  updatedAt: string
}

export interface SendMessagePayload {
  conversationId: string
  content: string
}
