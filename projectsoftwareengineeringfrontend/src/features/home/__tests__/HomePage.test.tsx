import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HomePage } from '../HomePage'
import { useUIStore } from '@/hooks/useUIStore'

describe('HomePage', () => {
  beforeEach(() => {
    useUIStore.setState({ isChatOpen: false })
  })

  it('hiện tên trường và slogan', () => {
    render(<HomePage />)

    expect(
      screen.getByRole('heading', { name: /Trợ lý Hỏi đáp Đại học/ })
    ).toBeInTheDocument()
    expect(screen.getByText(/Giải đáp mọi thắc mắc/)).toBeInTheDocument()
  })

  it('CTA mở khung chat widget', async () => {
    render(<HomePage />)

    expect(useUIStore.getState().isChatOpen).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: /Hỏi ngay/ }))
    expect(useUIStore.getState().isChatOpen).toBe(true)
  })
})
