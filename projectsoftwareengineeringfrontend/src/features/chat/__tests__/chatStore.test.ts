import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore } from '../chatStore'
import type { ChatMessage } from '@/types'

function resetStore() {
  useChatStore.setState({
    conversations: [],
    messages: {},
    activeConversationId: null,
    isLoading: false,
    error: null,
  })
}

function assistantReply(conversationId: string, content: string): ChatMessage {
  return {
    id: `reply-${content}`,
    conversationId,
    role: 'assistant',
    content,
    createdAt: new Date().toISOString(),
  }
}

describe('chatStore', () => {
  beforeEach(resetStore)

  it('tạo hội thoại mới và đặt làm hội thoại đang mở', () => {
    const id = useChatStore.getState().createConversation()
    const state = useChatStore.getState()

    expect(state.conversations).toHaveLength(1)
    expect(state.activeConversationId).toBe(id)
    expect(state.conversations[0].title).toBe('Hội thoại mới')
    expect(state.messages[id]).toEqual([])
  })

  it('đổi tên hội thoại tự động từ câu hỏi đầu tiên', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().addUserMessage(id, 'Lịch thi học kỳ 2 khi nào?')

    expect(useChatStore.getState().conversations[0].title).toBe(
      'Lịch thi học kỳ 2 khi nào?'
    )
  })

  it('không đổi tên lại ở tin nhắn thứ hai', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().addUserMessage(id, 'Câu hỏi đầu')
    useChatStore.getState().addUserMessage(id, 'Câu hỏi sau')

    expect(useChatStore.getState().conversations[0].title).toBe('Câu hỏi đầu')
    expect(useChatStore.getState().messages[id]).toHaveLength(2)
  })

  it('thêm câu trả lời của trợ lý vào đúng hội thoại', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().addUserMessage(id, 'Xin chào')
    useChatStore
      .getState()
      .addAssistantMessage(id, assistantReply(id, 'Chào bạn'))

    const messages = useChatStore.getState().messages[id]
    expect(messages).toHaveLength(2)
    expect(messages[1].role).toBe('assistant')
    expect(messages[1].content).toBe('Chào bạn')
  })

  it('đưa hội thoại có tin mới lên đầu danh sách', () => {
    const first = useChatStore.getState().createConversation()
    const second = useChatStore.getState().createConversation()

    // `second` tạo sau nên đang ở đầu; gửi tin vào `first` phải đẩy nó lên
    expect(useChatStore.getState().conversations[0].id).toBe(second)

    useChatStore.getState().addUserMessage(first, 'Tin mới nhất')
    expect(useChatStore.getState().conversations[0].id).toBe(first)
  })

  it('xoá một hội thoại kèm tin nhắn của nó', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().addUserMessage(id, 'Sẽ bị xoá')
    useChatStore.getState().deleteConversation(id)

    const state = useChatStore.getState()
    expect(state.conversations).toHaveLength(0)
    expect(state.messages[id]).toBeUndefined()
    expect(state.activeConversationId).toBeNull()
  })

  it('chuyển sang hội thoại còn lại khi xoá hội thoại đang mở', () => {
    const first = useChatStore.getState().createConversation()
    const second = useChatStore.getState().createConversation()

    useChatStore.getState().setActiveConversation(second)
    useChatStore.getState().deleteConversation(second)

    expect(useChatStore.getState().activeConversationId).toBe(first)
  })

  it('xoá tất cả hội thoại', () => {
    useChatStore.getState().createConversation()
    useChatStore.getState().createConversation()
    useChatStore.getState().deleteAllConversations()

    const state = useChatStore.getState()
    expect(state.conversations).toHaveLength(0)
    expect(state.messages).toEqual({})
    expect(state.activeConversationId).toBeNull()
  })

  it('đổi tên hội thoại thủ công', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().updateConversationTitle(id, 'Tên mới')

    expect(useChatStore.getState().conversations[0].title).toBe('Tên mới')
  })

  it('lưu hội thoại vào localStorage để khôi phục sau reload', () => {
    const id = useChatStore.getState().createConversation()
    useChatStore.getState().addUserMessage(id, 'Câu hỏi cần khôi phục')

    const stored = localStorage.getItem('chat-storage')
    expect(stored).not.toBeNull()

    const parsed = JSON.parse(stored as string)
    expect(parsed.state.conversations).toHaveLength(1)
    expect(parsed.state.messages[id][0].content).toBe('Câu hỏi cần khôi phục')
    // Không persist trạng thái tạm thời
    expect(parsed.state.isLoading).toBeUndefined()
    expect(parsed.state.error).toBeUndefined()
  })
})
