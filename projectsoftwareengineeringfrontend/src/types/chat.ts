export interface ChatCitation {
  chunkId: string
  docId: string | null
  title: string | null
  sourceUrl: string | null
  section: string
  page: number | null
  quote: string
}

export interface ChatMessage {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string // ISO 8601
  // Có từ backend RAG (POST /api/chat/messages); mock không trả các trường này
  status?: 'answered' | 'refused' | null
  sequence?: number
  requestId?: string | null
  deliveryStatus?: 'pending' | 'completed' | 'failed'
  replyToId?: string | null
  errorCode?: string | null
  institutionId?: string | null
  citations?: ChatCitation[]
  refusalReason?: string | null
  institution?: { ids: string[]; source: string | null }
}

export interface Institution {
  id: string
  name_en: string
  name_vi: string
  covered: boolean
}

export interface ChatConversation {
  id: string
  title: string
  updatedAt: string
  createdAt?: string
}

export interface SendMessagePayload {
  conversationId: string
  content: string
  requestId: string
  institutionId?: string // từ ô chọn trường; bỏ trống = backend tự nhận diện trong câu hỏi
}
