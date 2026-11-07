import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatWidget } from '../ChatWidget'
import { useChatStore } from '../chatStore'
import { useUIStore } from '@/hooks/useUIStore'
import * as services from '@/services'
import type { ChatMessage } from '@/types'

vi.mock('@/services', async () => {
  const actual = await vi.importActual<typeof services>('@/services')
  return {
    ...actual,
    sendMessage: vi.fn(),
    getConversations: vi.fn(),
    getMessages: vi.fn(),
    getConversation: vi.fn(),
    createConversation: vi.fn(),
    deleteAllConversations: vi.fn(),
  }
})

const sendMessageMock = vi.mocked(services.sendMessage)

function reply(content: string): ChatMessage {
  return {
    id: 'assistant-1',
    conversationId: 'conv-1',
    role: 'assistant',
    content,
    createdAt: new Date().toISOString(),
  }
}

describe('ChatWidget', () => {
  beforeEach(() => {
    vi.mocked(services.getConversations).mockResolvedValue([])
    vi.mocked(services.getMessages).mockResolvedValue([])
    const conversation = {
      id: 'conv-1',
      title: 'Hội thoại mới',
      updatedAt: new Date().toISOString(),
    }
    vi.mocked(services.createConversation).mockResolvedValue(conversation)
    vi.mocked(services.getConversation).mockResolvedValue(conversation)
    vi.mocked(services.deleteAllConversations).mockResolvedValue(undefined)
    useChatStore.setState({
      ownerId: 'student',
      sessionVersion: useChatStore.getState().sessionVersion + 1,
      historyLoading: false,
      messagesLoadingId: null,
      pendingConversationId: null,
      errorRequestId: null,
      retryAt: 0,
      conversations: [],
      messages: {},
      activeConversationId: null,
      isLoading: false,
      error: null,
    })
    useUIStore.setState({ isChatOpen: true })
  })

  afterEach(() => {
    sendMessageMock.mockReset()
  })

  it('thu gọn thành nút tròn khi đóng, không hiện panel', async () => {
    useUIStore.setState({ isChatOpen: false })
    render(<ChatWidget />)

    await waitFor(() =>
      expect(useChatStore.getState().historyLoading).toBe(false)
    )
    expect(screen.getByLabelText('Mở chat')).toBeInTheDocument()
    expect(screen.queryByLabelText('Nhập tin nhắn')).not.toBeInTheDocument()
  })

  it('mở panel chat khi bấm nút tròn', async () => {
    useUIStore.setState({ isChatOpen: false })
    render(<ChatWidget />)

    await userEvent.click(screen.getByLabelText('Mở chat'))
    expect(screen.getByLabelText('Nhập tin nhắn')).toBeInTheDocument()
  })

  it('hiện empty state khi chưa có tin nhắn', async () => {
    render(<ChatWidget />)
    await waitFor(() =>
      expect(useChatStore.getState().historyLoading).toBe(false)
    )
    expect(screen.getByText('Xin chào!')).toBeInTheDocument()
  })

  it('hiện tin của người dùng và câu trả lời của trợ lý', async () => {
    sendMessageMock.mockResolvedValue(reply('Lịch thi sẽ có vào tháng 5.'))
    render(<ChatWidget />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Lịch thi?')
    await userEvent.keyboard('{Enter}')

    expect(screen.getByText('Lịch thi?')).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.getByText('Lịch thi sẽ có vào tháng 5.')
      ).toBeInTheDocument()
    })
  })

  it('hiện "Đang trả lời..." trong lúc chờ server', async () => {
    let resolveReply: (message: ChatMessage) => void = () => {}
    sendMessageMock.mockImplementation(
      () =>
        new Promise<ChatMessage>((resolve) => {
          resolveReply = resolve
        })
    )
    render(<ChatWidget />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Xin chào')
    await userEvent.keyboard('{Enter}')

    expect(await screen.findByText('Đang trả lời...')).toBeInTheDocument()

    resolveReply(reply('Chào bạn!'))
    await waitFor(() => {
      expect(screen.queryByText('Đang trả lời...')).not.toBeInTheDocument()
    })
  })

  it('hiện lỗi kèm nút Thử lại khi gọi API thất bại', async () => {
    sendMessageMock.mockRejectedValue(new Error('network down'))
    render(<ChatWidget />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Học bổng?')
    await userEvent.keyboard('{Enter}')

    expect(
      await screen.findByText('Không thể kết nối đến server. Vui lòng thử lại.')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Thử lại' })).toBeInTheDocument()
    // Không mất nội dung đã gửi
    expect(screen.getByText('Học bổng?')).toBeInTheDocument()
  })

  it('gửi lại câu hỏi cũ khi bấm Thử lại', async () => {
    sendMessageMock.mockRejectedValueOnce(new Error('network down'))
    render(<ChatWidget />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Học bổng?')
    await userEvent.keyboard('{Enter}')
    await screen.findByRole('button', { name: 'Thử lại' })

    sendMessageMock.mockResolvedValueOnce(reply('Hồ sơ nộp trước 30/4.'))
    await userEvent.click(screen.getByRole('button', { name: 'Thử lại' }))

    await waitFor(() => {
      expect(screen.getByText('Hồ sơ nộp trước 30/4.')).toBeInTheDocument()
    })
    // Gửi lại đúng nội dung câu hỏi cũ
    expect(sendMessageMock).toHaveBeenLastCalledWith(
      expect.any(String),
      'Học bổng?',
      expect.any(String),
      undefined
    )
    expect(sendMessageMock.mock.calls[1][2]).toBe(
      sendMessageMock.mock.calls[0][2]
    )
  })

  it('mở sidebar lịch sử và hiện hội thoại đã lưu', async () => {
    render(<ChatWidget />)

    await userEvent.click(screen.getByLabelText('Lịch sử hội thoại'))
    expect(screen.getByText('Chưa có hội thoại nào')).toBeInTheDocument()
  })

  it('xoá tất cả hội thoại từ sidebar', async () => {
    sendMessageMock.mockResolvedValue(reply('ok'))
    render(<ChatWidget />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Câu hỏi A')
    await userEvent.keyboard('{Enter}')
    await waitFor(() => {
      expect(useChatStore.getState().conversations).toHaveLength(1)
    })

    await userEvent.click(screen.getByLabelText('Lịch sử hội thoại'))
    await userEvent.click(screen.getByRole('button', { name: 'Xoá tất cả' }))

    await waitFor(() =>
      expect(useChatStore.getState().conversations).toHaveLength(0)
    )
  })

  it('keeps the typed question if creating its server conversation fails', async () => {
    vi.mocked(services.createConversation).mockRejectedValueOnce(
      new Error('offline')
    )
    render(<ChatWidget />)
    await waitFor(() =>
      expect(useChatStore.getState().historyLoading).toBe(false)
    )
    await userEvent.type(
      screen.getByLabelText('Nhập tin nhắn'),
      'Keep this draft'
    )
    await userEvent.keyboard('{Enter}')
    await waitFor(() =>
      expect(screen.getByLabelText('Nhập tin nhắn')).toHaveValue(
        'Keep this draft'
      )
    )
    expect(sendMessageMock).not.toHaveBeenCalled()
  })

  it('retries a failed server question after reload with its original request and institution', async () => {
    const conversation = {
      id: 'conv-1',
      title: 'Saved on server',
      updatedAt: new Date().toISOString(),
    }
    vi.mocked(services.getConversations).mockResolvedValueOnce([conversation])
    vi.mocked(services.getMessages).mockResolvedValue([
      {
        id: 'question-1',
        conversationId: 'conv-1',
        role: 'user',
        content: 'Saved question',
        createdAt: conversation.updatedAt,
        requestId: 'original-request',
        institutionId: 'uit',
        sequence: 1,
        deliveryStatus: 'failed',
      },
    ])
    sendMessageMock.mockResolvedValueOnce(reply('Recovered answer'))
    render(<ChatWidget />)
    await userEvent.click(
      await screen.findByRole('button', { name: /^Thử lại$/ })
    )
    await screen.findByText('Recovered answer')
    expect(sendMessageMock).toHaveBeenCalledWith(
      'conv-1',
      'Saved question',
      'original-request',
      'uit'
    )
  })

  it('does not keep polling a pending question while the chat panel is closed', async () => {
    const conversation = {
      id: 'conv-1',
      title: 'Saved',
      updatedAt: new Date().toISOString(),
    }
    vi.mocked(services.getConversations).mockResolvedValueOnce([conversation])
    vi.mocked(services.getMessages).mockResolvedValue([
      {
        id: 'pending',
        conversationId: 'conv-1',
        role: 'user',
        content: 'Waiting',
        requestId: 'request',
        deliveryStatus: 'pending',
        createdAt: conversation.updatedAt,
      },
    ])
    useUIStore.setState({ isChatOpen: false })
    render(<ChatWidget />)
    await waitFor(() =>
      expect(useChatStore.getState().messages['conv-1']).toHaveLength(1)
    )
    const reads = vi.mocked(services.getMessages).mock.calls.length
    vi.useFakeTimers()
    try {
      vi.advanceTimersByTime(10000)
      expect(services.getMessages).toHaveBeenCalledTimes(reads)
    } finally {
      vi.useRealTimers()
    }
  })
})
