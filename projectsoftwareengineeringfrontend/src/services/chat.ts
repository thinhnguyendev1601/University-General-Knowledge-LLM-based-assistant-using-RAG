/**
 * Chat service — chỉ có network, không có business logic.
 * sendMessage gọi backend RAG thật (api/app.py); hội thoại vẫn lưu cục bộ (mock)
 * cho tới khi backend có endpoint conversations. VITE_USE_MOCK_CHAT=true để dùng lại mock.
 */
import type { ChatConversation, ChatMessage, Institution } from '@/types'
import { httpClient } from './httpClient'
import {
  mockSendMessage,
  mockGetConversations,
  mockGetMessages,
  mockDeleteConversation,
} from '@/mocks'

export async function getConversations(): Promise<ChatConversation[]> {
  // return httpClient.get<ChatConversation[]>('/chat/conversations')
  return mockGetConversations()
}

export async function getMessages(
  conversationId: string
): Promise<ChatMessage[]> {
  // return httpClient.get<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`)
  return mockGetMessages(conversationId)
}

const USE_MOCK_CHAT = import.meta.env.VITE_USE_MOCK_CHAT === 'true'
// LLM chạy trên CPU (Ollama) mất 30-120 s cho một câu trả lời
const CHAT_TIMEOUT_MS = Number(import.meta.env.VITE_CHAT_TIMEOUT_MS) || 180000

export async function sendMessage(
  conversationId: string,
  content: string,
  institutionId?: string
): Promise<ChatMessage> {
  if (USE_MOCK_CHAT) return mockSendMessage(conversationId, content)
  return httpClient.post<ChatMessage>(
    '/chat/messages',
    { conversationId, content, institutionId },
    CHAT_TIMEOUT_MS
  )
}

/** Danh sách trường cho ô chọn trường (covered = hệ thống có tài liệu). */
export async function getInstitutions(): Promise<Institution[]> {
  return httpClient.get<Institution[]>('/institutions')
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  // return httpClient.delete(`/chat/conversations/${conversationId}`)
  return mockDeleteConversation(conversationId)
}
