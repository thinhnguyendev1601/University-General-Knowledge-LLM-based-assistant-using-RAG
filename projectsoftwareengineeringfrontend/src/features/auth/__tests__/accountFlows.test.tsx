import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import * as services from '@/services'
import { RegisterForm } from '../RegisterForm'
import { TokenActionForm } from '../TokenActionForm'
import { EmailRequestForm } from '../EmailRequestForm'
import { useAuthStore } from '../authStore'
import { useChatStore } from '@/features/chat/chatStore'

vi.mock('@/services', async () => ({
  ...(await vi.importActual<typeof services>('@/services')),
  registerAccount: vi.fn(),
  resetPassword: vi.fn(),
  forgotPassword: vi.fn(),
  getCurrentUser: vi.fn(),
  logout: vi.fn(),
}))

const PASSWORD = 'a sufficiently long password'
const session = {
  user: {
    id: 'student-1',
    email: 'student@university.edu.vn',
    name: 'Student',
    role: 'user' as const,
  },
  csrfToken: 'csrf-value',
  expiresAt: '2030-01-01T00:00:00Z',
}

function mount(element: React.ReactNode, path = '/') {
  return render(<MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>)
}

async function fillRegistration(email: string, confirmation = PASSWORD) {
  await userEvent.type(screen.getByLabelText('Họ tên'), 'Student')
  await userEvent.type(screen.getByLabelText('Email trường'), email)
  await userEvent.type(screen.getByLabelText('Mật khẩu'), PASSWORD)
  await userEvent.type(screen.getByLabelText('Xác nhận mật khẩu'), confirmation)
  await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
}

describe('Real account flows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().clearAuth()
  })

  it.each([
    'student@gmail.com',
    'student@cs.university.edu.vn',
    'student@university.edu.vn.evil.com',
  ])('rejects %s before calling the API', async (email) => {
    mount(<RegisterForm />)
    await fillRegistration(email)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '@university.edu.vn'
    )
    expect(services.registerAccount).not.toHaveBeenCalled()
  })

  it('registers a normalized school email without logging the user in', async () => {
    vi.mocked(services.registerAccount).mockResolvedValue({
      message: 'Đăng ký thành công. Bạn có thể đăng nhập ngay.',
    })
    mount(<RegisterForm />)
    await fillRegistration('Student@UNIVERSITY.EDU.VN')
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Bạn có thể đăng nhập ngay'
    )
    expect(services.registerAccount).toHaveBeenCalledWith({
      name: 'Student',
      email: session.user.email,
      password: PASSWORD,
    })
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(screen.queryByLabelText('Mật khẩu')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Gửi lại email xác minh' })
    ).not.toBeInTheDocument()
  })

  it('rejects mismatching passwords', async () => {
    mount(<RegisterForm />)
    await fillRegistration(session.user.email, 'another long password')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Mật khẩu xác nhận không khớp'
    )
    expect(services.registerAccount).not.toHaveBeenCalled()
  })

  it('keeps form values available after an API failure', async () => {
    vi.mocked(services.registerAccount).mockRejectedValue(
      new Error('Email này đã được đăng ký')
    )
    mount(<RegisterForm />)
    await fillRegistration(session.user.email)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email này đã được đăng ký'
    )
    expect(screen.getByLabelText('Email trường')).toHaveValue(
      session.user.email
    )
  })

  it('explains missing reset links without sending a request', () => {
    mount(<TokenActionForm />, '/reset-password')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Liên kết thiếu mã đặt lại mật khẩu'
    )
    expect(services.resetPassword).not.toHaveBeenCalled()
  })

  it('explains expired password reset links', async () => {
    vi.mocked(services.resetPassword).mockRejectedValue(
      new Error('Liên kết đã hết hạn')
    )
    mount(<TokenActionForm />, '/reset-password#token=expired')
    await userEvent.type(screen.getByLabelText('Mật khẩu mới'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Xác nhận mật khẩu'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Liên kết đã hết hạn'
    )
  })

  it('submits a new password and clears any old authenticated state', async () => {
    useAuthStore.getState().setAuth(session)
    vi.mocked(services.resetPassword).mockResolvedValue({
      message: 'Mật khẩu đã thay đổi',
    })
    mount(<TokenActionForm />, '/reset-password#token=reset-token')
    await userEvent.type(screen.getByLabelText('Mật khẩu mới'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Xác nhận mật khẩu'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Mật khẩu đã thay đổi'
    )
    expect(services.resetPassword).toHaveBeenCalledWith('reset-token', PASSWORD)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('requests a password reset email', async () => {
    vi.mocked(services.forgotPassword).mockResolvedValue({
      message: 'Hãy kiểm tra email',
    })
    mount(<EmailRequestForm />)
    await userEvent.type(
      screen.getByLabelText('Email trường'),
      session.user.email
    )
    await userEvent.click(screen.getByRole('button', { name: 'Gửi yêu cầu' }))
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Hãy kiểm tra email'
    )
    expect(services.forgotPassword).toHaveBeenCalledWith(session.user.email)
  })

  it('restores identity from the server and discards obsolete local mock authentication', async () => {
    localStorage.setItem('auth-storage', 'old-mock-token')
    vi.mocked(services.getCurrentUser).mockResolvedValue(session)
    await useAuthStore.getState().initialize()
    expect(useAuthStore.getState().user).toEqual(session.user)
    expect(localStorage.getItem('auth-storage')).toBeNull()
  })

  it('does not report a successful logout when the server cannot revoke the session', async () => {
    useAuthStore.getState().setAuth(session)
    vi.mocked(services.logout).mockRejectedValue(new Error('offline'))
    await expect(useAuthStore.getState().logout()).rejects.toThrow('offline')
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    vi.mocked(services.logout).mockResolvedValue(undefined)
    await useAuthStore.getState().logout()
    await waitFor(() =>
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    )
  })

  it('preserves local history when checking the session fails temporarily', async () => {
    useAuthStore.getState().setAuth(session)
    const conversationId = 'server-conversation'
    useChatStore
      .getState()
      .upsertConversation({
        id: conversationId,
        title: 'Saved',
        updatedAt: new Date().toISOString(),
      })
    useChatStore
      .getState()
      .mergeMessages(conversationId, [
        {
          id: 'server-message',
          conversationId,
          role: 'user',
          content: 'My existing question',
          createdAt: new Date().toISOString(),
        },
      ])
    const history = localStorage.getItem('chat-storage')
    vi.mocked(services.getCurrentUser).mockRejectedValue(new Error('offline'))
    await useAuthStore.getState().initialize()
    expect(useAuthStore.getState().initializationError).not.toBeNull()
    expect(useAuthStore.getState().isLoading).toBe(false)
    expect(localStorage.getItem('chat-storage')).toBe(history)
    expect(useChatStore.getState().messages[conversationId]).toHaveLength(1)
  })

  it('clears the previous account history when a different user signs in', () => {
    useAuthStore.getState().setAuth(session)
    const conversationId = 'server-conversation'
    useChatStore
      .getState()
      .upsertConversation({
        id: conversationId,
        title: 'Saved',
        updatedAt: new Date().toISOString(),
      })
    useChatStore
      .getState()
      .mergeMessages(conversationId, [
        {
          id: 'server-message',
          conversationId,
          role: 'user',
          content: 'Private question',
          createdAt: new Date().toISOString(),
        },
      ])
    useAuthStore
      .getState()
      .setAuth({ ...session, user: { ...session.user, id: 'student-2' } })
    expect(useChatStore.getState().messages).toEqual({})
    expect(useChatStore.getState().conversations).toEqual([])
  })
})
