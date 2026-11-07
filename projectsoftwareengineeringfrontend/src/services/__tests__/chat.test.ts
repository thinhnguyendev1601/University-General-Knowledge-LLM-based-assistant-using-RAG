import { beforeEach, expect, it, vi } from 'vitest'
import { getConversations, getMessages, sendMessage } from '../chat'
import { httpClient } from '../httpClient'
import type { ChatConversation, ChatMessage } from '@/types'

vi.mock('../httpClient', () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))
beforeEach(() => vi.resetAllMocks())

it('reads every conversation page rather than losing history after 100 items', async () => {
  const page: ChatConversation[] = Array.from({ length: 100 }, (_, i) => ({
    id: `c-${i}`,
    title: 'Saved',
    updatedAt: '2026-11-07',
  }))
  vi.mocked(httpClient.get)
    .mockResolvedValueOnce(page)
    .mockResolvedValueOnce([{ ...page[0], id: 'last' }])
  expect(await getConversations()).toHaveLength(101)
  expect(httpClient.get).toHaveBeenLastCalledWith(
    '/chat/conversations?limit=100&offset=100'
  )
})

it('uses the last server sequence when reading the next message page', async () => {
  const page: ChatMessage[] = Array.from({ length: 500 }, (_, i) => ({
    id: `m-${i}`,
    conversationId: 'c',
    role: 'user',
    content: 'Saved',
    createdAt: '2026-11-07',
    sequence: i + 1,
  }))
  vi.mocked(httpClient.get)
    .mockResolvedValueOnce(page)
    .mockResolvedValueOnce([])
  expect(await getMessages('c')).toHaveLength(500)
  expect(httpClient.get).toHaveBeenLastCalledWith(
    '/chat/conversations/c/messages?limit=500&afterSequence=500'
  )
})

it('sends the original request UUID and uses the server HTTP budget', async () => {
  vi.mocked(httpClient.get).mockResolvedValue({ requestTimeoutMs: 220000 })
  vi.mocked(httpClient.post).mockResolvedValue({ id: 'answer' })
  await sendMessage('conversation', 'Question', 'same-request', 'uit')
  expect(httpClient.post).toHaveBeenCalledWith(
    '/chat/messages',
    {
      conversationId: 'conversation',
      content: 'Question',
      requestId: 'same-request',
      institutionId: 'uit',
    },
    220000
  )
})
