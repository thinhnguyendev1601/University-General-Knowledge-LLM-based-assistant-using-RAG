/** Server history is authoritative; no implicit import from legacy localStorage. */
import type { ChatConversation, ChatMessage, Institution } from '@/types'
import { httpClient } from './httpClient'

export async function getConversations(): Promise<ChatConversation[]> {
  const result: ChatConversation[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await httpClient.get<ChatConversation[]>(
      `/chat/conversations?limit=100&offset=${offset}`
    )
    result.push(...page)
    if (page.length < 100)
      return [...new Map(result.map((item) => [item.id, item])).values()]
  }
}

export function createConversation(): Promise<ChatConversation> {
  return httpClient.post('/chat/conversations', {})
}

export function getConversation(id: string): Promise<ChatConversation> {
  return httpClient.get(`/chat/conversations/${id}`)
}

export async function getMessages(id: string): Promise<ChatMessage[]> {
  const result: ChatMessage[] = []
  let sequence = 0
  while (true) {
    const page = await httpClient.get<ChatMessage[]>(
      `/chat/conversations/${id}/messages?limit=500&afterSequence=${sequence}`
    )
    result.push(...page)
    if (page.length < 500) return result
    const next = page.at(-1)?.sequence
    if (next === undefined || next <= sequence)
      throw new Error('Không đọc được trang lịch sử tiếp theo.')
    sequence = next
  }
}

export function getChatConfiguration(): Promise<{ requestTimeoutMs: number }> {
  return httpClient.get('/chat/config')
}

export async function sendMessage(
  conversationId: string,
  content: string,
  requestId: string,
  institutionId?: string
): Promise<ChatMessage> {
  const { requestTimeoutMs } = await getChatConfiguration()
  return httpClient.post(
    '/chat/messages',
    { conversationId, content, requestId, institutionId },
    requestTimeoutMs
  )
}

export function getInstitutions(): Promise<Institution[]> {
  return httpClient.get('/institutions')
}

export function renameConversation(
  id: string,
  title: string
): Promise<ChatConversation> {
  return httpClient.patch(`/chat/conversations/${id}`, { title })
}

export function deleteConversation(id: string): Promise<void> {
  return httpClient.delete(`/chat/conversations/${id}`)
}

export function deleteAllConversations(): Promise<void> {
  return httpClient.delete('/chat/conversations')
}
