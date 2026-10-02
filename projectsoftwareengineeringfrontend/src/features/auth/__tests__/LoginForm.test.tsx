import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LoginForm } from '../LoginForm'
import { useAuthStore } from '../authStore'
import * as services from '@/services'
import type { AuthResponse } from '@/types'

vi.mock('@/services', async () => {
  const actual = await vi.importActual<typeof services>('@/services')
  return { ...actual, login: vi.fn() }
})

const loginMock = vi.mocked(services.login)

const adminResponse: AuthResponse = {
  token: 'token-admin',
  refreshToken: 'refresh-admin',
  user: {
    id: 'usr-001',
    name: 'Quản trị viên',
    email: 'admin@university.edu.vn',
    role: 'admin',
  },
}

function renderLoginForm() {
  return render(
    <MemoryRouter>
      <LoginForm />
    </MemoryRouter>
  )
}

describe('LoginForm', () => {
  beforeEach(() => {
    loginMock.mockReset()
    useAuthStore.setState({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    })
  })

  it('báo lỗi khi để trống email và mật khẩu', async () => {
    renderLoginForm()

    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    expect(await screen.findByText('Vui lòng nhập email')).toBeInTheDocument()
    expect(screen.getByText('Vui lòng nhập mật khẩu')).toBeInTheDocument()
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('báo lỗi khi email sai định dạng', async () => {
    renderLoginForm()

    await userEvent.type(screen.getByLabelText('Email'), 'khong-phai-email')
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'matkhau123')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    expect(await screen.findByText('Email không hợp lệ')).toBeInTheDocument()
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('báo lỗi khi mật khẩu ngắn hơn 6 ký tự', async () => {
    renderLoginForm()

    await userEvent.type(screen.getByLabelText('Email'), 'a@university.edu.vn')
    await userEvent.type(screen.getByLabelText('Mật khẩu'), '123')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    expect(
      await screen.findByText('Mật khẩu phải có ít nhất 6 ký tự')
    ).toBeInTheDocument()
  })

  it('hiện message rõ ràng khi sai thông tin đăng nhập', async () => {
    loginMock.mockRejectedValue(new Error('Email hoặc mật khẩu không đúng'))
    renderLoginForm()

    await userEvent.type(screen.getByLabelText('Email'), 'a@university.edu.vn')
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'saimatkhau')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Email hoặc mật khẩu không đúng')
  })

  it('giữ nguyên giá trị đã gõ khi đăng nhập lỗi', async () => {
    loginMock.mockRejectedValue(new Error('Email hoặc mật khẩu không đúng'))
    renderLoginForm()

    await userEvent.type(screen.getByLabelText('Email'), 'a@university.edu.vn')
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'saimatkhau')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    await screen.findByRole('alert')
    expect(screen.getByLabelText('Email')).toHaveValue('a@university.edu.vn')
    expect(screen.getByLabelText('Mật khẩu')).toHaveValue('saimatkhau')
  })

  it('lưu token và user kèm role vào auth store khi đăng nhập thành công', async () => {
    loginMock.mockResolvedValue(adminResponse)
    renderLoginForm()

    await userEvent.type(
      screen.getByLabelText('Email'),
      'admin@university.edu.vn'
    )
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'admin123')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))

    await waitFor(() => {
      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.token).toBe('token-admin')
      expect(state.user?.role).toBe('admin')
    })
  })

  it('bật/tắt hiện mật khẩu', async () => {
    renderLoginForm()

    const password = screen.getByLabelText('Mật khẩu')
    expect(password).toHaveAttribute('type', 'password')

    await userEvent.click(screen.getByLabelText('Hiện mật khẩu'))
    expect(password).toHaveAttribute('type', 'text')

    await userEvent.click(screen.getByLabelText('Ẩn mật khẩu'))
    expect(password).toHaveAttribute('type', 'password')
  })

  it('hiện thông báo khi bấm quên mật khẩu, không dùng console.log', async () => {
    renderLoginForm()

    await userEvent.click(
      screen.getByRole('button', { name: 'Quên mật khẩu?' })
    )
    expect(await screen.findByRole('status')).toBeInTheDocument()
  })
})
