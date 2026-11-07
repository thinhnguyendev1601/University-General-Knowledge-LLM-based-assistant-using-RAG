import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatStore } from '../chatStore'
import {
  createServerConversation,
  deleteServerConversation,
  loadHistory,
  loadMessages,
  renameServerConversation,
} from '../chatHistory'
import * as api from '@/services'
import type { ChatConversation, ChatMessage } from '@/types'

vi.mock('@/services', async () => {
  const actual = await vi.importActual<typeof api>('@/services')
  return {
    ...actual,
    createConversation: vi.fn(),
    getConversations: vi.fn(),
    getMessages: vi.fn(),
    deleteConversation: vi.fn(),
    renameConversation: vi.fn(),
  }
})

const conversation: ChatConversation = {
  id: 'server-uuid',
  title: 'Saved on server',
  updatedAt: '2026-11-07T01:00:00Z',
}
const question: ChatMessage = {
  id: 'server-question',
  conversationId: conversation.id,
  role: 'user',
  content: 'Question',
  requestId: 'request-uuid',
  sequence: 1,
  deliveryStatus: 'failed',
  createdAt: conversation.updatedAt,
}

describe('server chat history', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    window.dispatchEvent(new CustomEvent('auth-user-changed', { detail: null }))
    window.dispatchEvent(
      new CustomEvent('auth-user-changed', { detail: 'student' })
    )
  })

  it('creates through the API and only uses the returned ID', async () => {
    vi.mocked(api.createConversation).mockResolvedValue(conversation)
    expect(await createServerConversation()).toBe(conversation.id)
    expect(api.createConversation).toHaveBeenCalledOnce()
    expect(useChatStore.getState().activeConversationId).toBe(conversation.id)
    expect(localStorage.getItem('chat-storage')).toBeNull()
  })

  it('restores server history after a new login and loads messages', async () => {
    vi.mocked(api.getConversations).mockResolvedValue([conversation])
    vi.mocked(api.getMessages).mockResolvedValue([question])
    await loadHistory()
    await loadMessages(conversation.id)
    expect(useChatStore.getState().activeConversationId).toBe(conversation.id)
    expect(useChatStore.getState().messages[conversation.id]).toEqual([
      question,
    ])
    window.dispatchEvent(new CustomEvent('auth-user-changed', { detail: null }))
    expect(useChatStore.getState().messages).toEqual({})
    window.dispatchEvent(
      new CustomEvent('auth-user-changed', { detail: 'student' })
    )
    await loadHistory()
    await loadMessages(conversation.id)
    expect(useChatStore.getState().messages[conversation.id]).toEqual([
      question,
    ])
  })

  it('reconciles optimistic questions by requestId without duplicates', () => {
    const store = useChatStore.getState()
    store.upsertConversation(conversation)
    store.mergeMessages(conversation.id, [
      { ...question, id: 'pending-request-uuid', sequence: undefined },
    ])
    store.mergeMessages(conversation.id, [question])
    store.mergeMessages(conversation.id, [
      { ...question, deliveryStatus: 'completed' },
    ])
    expect(useChatStore.getState().messages[conversation.id]).toHaveLength(1)
    expect(useChatStore.getState().messages[conversation.id][0].id).toBe(
      'server-question'
    )
  })

  it('does not mix late history, messages or creation into a different login', async () => {
    let finish: (items: ChatConversation[]) => void = () => {}
    vi.mocked(api.getConversations).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    const pending = loadHistory()
    window.dispatchEvent(
      new CustomEvent('auth-user-changed', { detail: 'other-student' })
    )
    finish([conversation])
    await pending
    expect(useChatStore.getState().conversations).toEqual([])
  })

  it('does not remove history when the delete request fails', async () => {
    useChatStore.getState().upsertConversation(conversation)
    vi.mocked(api.deleteConversation).mockRejectedValue(new Error('offline'))
    await deleteServerConversation(conversation.id)
    expect(useChatStore.getState().conversations).toEqual([conversation])
    expect(useChatStore.getState().error).toBe(
      'Không thể kết nối đến server. Vui lòng thử lại.'
    )
    vi.mocked(api.deleteConversation).mockResolvedValue(undefined)
    await deleteServerConversation(conversation.id)
    expect(useChatStore.getState().conversations).toEqual([])
  })

  it('renames on the server and keeps its returned metadata', async () => {
    useChatStore.getState().upsertConversation(conversation)
    vi.mocked(api.renameConversation).mockResolvedValue({
      ...conversation,
      title: 'Renamed',
    })
    await renameServerConversation(conversation.id, 'Renamed')
    expect(api.renameConversation).toHaveBeenCalledWith(
      conversation.id,
      'Renamed'
    )
    expect(useChatStore.getState().conversations[0].title).toBe('Renamed')
  })

  it('ignores a message response after its conversation was deleted', async () => {
    useChatStore.getState().upsertConversation(conversation)
    let finish: (items: ChatMessage[]) => void = () => {}
    vi.mocked(api.getMessages).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    const pending = loadMessages(conversation.id)
    vi.mocked(api.deleteConversation).mockResolvedValue(undefined)
    await deleteServerConversation(conversation.id)
    finish([question])
    await pending
    expect(useChatStore.getState().messages).toEqual({})
  })

  it('ignores a create response belonging to an old login', async () => {
    let finish: (item: ChatConversation) => void = () => {}
    vi.mocked(api.createConversation).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    const pending = createServerConversation()
    window.dispatchEvent(
      new CustomEvent('auth-user-changed', { detail: 'other-student' })
    )
    finish(conversation)
    expect(await pending).toBeNull()
    expect(useChatStore.getState().conversations).toEqual([])
  })

  it('does not replace newer message state with an older in-flight read', async () => {
    useChatStore.getState().upsertConversation(conversation)
    let finish: (items: ChatMessage[]) => void = () => {}
    vi.mocked(api.getMessages)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve
          })
      )
      .mockResolvedValueOnce([{ ...question, deliveryStatus: 'completed' }])
    const old = loadMessages(conversation.id)
    await loadMessages(conversation.id)
    finish([question])
    await old
    expect(
      useChatStore.getState().messages[conversation.id][0].deliveryStatus
    ).toBe('completed')
  })

  it('clears a network warning when polling discovers that the original request succeeded', async () => {
    useChatStore.getState().upsertConversation(conversation)
    useChatStore.setState({
      error: 'network warning',
      errorRequestId: question.requestId,
    })
    vi.mocked(api.getMessages).mockResolvedValue([
      question,
      { ...question, id: 'answer', role: 'assistant', sequence: 2 },
    ])
    await loadMessages(conversation.id)
    expect(useChatStore.getState().error).toBeNull()
  })
})
