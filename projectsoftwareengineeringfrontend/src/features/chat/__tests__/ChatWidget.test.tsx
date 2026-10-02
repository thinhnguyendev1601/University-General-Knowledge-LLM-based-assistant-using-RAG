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
  return { ...actual, sendMessage: vi.fn() }
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
    useChatStore.setState({
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

  it('thu gọn thành nút tròn khi đóng, không hiện panel', () => {
    useUIStore.setState({ isChatOpen: false })
    render(<ChatWidget />)

    expect(screen.getByLabelText('Mở chat')).toBeInTheDocument()
    expect(screen.queryByLabelText('Nhập tin nhắn')).not.toBeInTheDocument()
  })

  it('mở panel chat khi bấm nút tròn', async () => {
    useUIStore.setState({ isChatOpen: false })
    render(<ChatWidget />)

    await userEvent.click(screen.getByLabelText('Mở chat'))
    expect(screen.getByLabelText('Nhập tin nhắn')).toBeInTheDocument()
  })

  it('hiện empty state khi chưa có tin nhắn', () => {
    render(<ChatWidget />)
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
      'Học bổng?'
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

    expect(useChatStore.getState().conversations).toHaveLength(0)
  })
})
