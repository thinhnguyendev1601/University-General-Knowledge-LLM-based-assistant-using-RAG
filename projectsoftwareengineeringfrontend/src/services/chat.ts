/**
 * Chat service — chỉ có network, không có business logic.
 * Hiện dùng mock; khi backend sẵn sàng thì đổi sang httpClient.
 */
import type { ChatConversation, ChatMessage } from '@/types'
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

export async function sendMessage(
  conversationId: string,
  content: string
): Promise<ChatMessage> {
  // return httpClient.post<ChatMessage>('/chat/messages', { conversationId, content })
  return mockSendMessage(conversationId, content)
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  // return httpClient.delete(`/chat/conversations/${conversationId}`)
  return mockDeleteConversation(conversationId)
}
