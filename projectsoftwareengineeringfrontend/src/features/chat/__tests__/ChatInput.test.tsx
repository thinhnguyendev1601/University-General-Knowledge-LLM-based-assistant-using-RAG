import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '../ChatInput'

describe('ChatInput', () => {
  it('gửi tin bằng Enter', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    const textarea = screen.getByLabelText('Nhập tin nhắn')
    await userEvent.type(textarea, 'Lịch thi khi nào?')
    await userEvent.keyboard('{Enter}')

    expect(onSend).toHaveBeenCalledWith('Lịch thi khi nào?')
    expect(textarea).toHaveValue('')
  })

  it('xuống dòng bằng Shift+Enter, không gửi', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    const textarea = screen.getByLabelText('Nhập tin nhắn')
    await userEvent.type(textarea, 'Dòng 1')
    await userEvent.keyboard('{Shift>}{Enter}{/Shift}')
    await userEvent.type(textarea, 'Dòng 2')

    expect(onSend).not.toHaveBeenCalled()
    expect(textarea).toHaveValue('Dòng 1\nDòng 2')
  })

  it('không gửi tin chỉ có khoảng trắng', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), '   ')
    await userEvent.keyboard('{Enter}')

    expect(onSend).not.toHaveBeenCalled()
  })

  it('vô hiệu nút gửi khi ô nhập rỗng', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)
    expect(screen.getByLabelText('Gửi tin nhắn')).toBeDisabled()
  })

  it('vô hiệu nút gửi khi đang chờ trả lời', async () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />)

    await userEvent.type(screen.getByLabelText('Nhập tin nhắn'), 'Xin chào')
    expect(screen.getByLabelText('Gửi tin nhắn')).toBeDisabled()
  })

  it('giữ nguyên text dài nhiều dòng khi paste', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    const textarea = screen.getByLabelText('Nhập tin nhắn')
    const longText = 'Dòng A\nDòng B\nDòng C'
    await userEvent.click(textarea)
    await userEvent.paste(longText)

    expect(textarea).toHaveValue(longText)
  })
})
