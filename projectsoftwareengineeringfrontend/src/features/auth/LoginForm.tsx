/**
 * LoginForm — form đăng nhập với validate Zod.
 * Hiển thị lỗi ngay dưới field, báo lỗi sai thông tin rõ ràng.
 */
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from './authStore'
import { PasswordField } from './PasswordField'
import { DemoAccounts } from './DemoAccounts'
import { login } from '@/services'
import { Button, Input, Spinner } from '@/components/ui'
import styles from './LoginForm.module.css'

const loginSchema = z.object({
  email: z.string().min(1, 'Vui lòng nhập email').email('Email không hợp lệ'),
  password: z
    .string()
    .min(1, 'Vui lòng nhập mật khẩu')
    .min(6, 'Mật khẩu phải có ít nhất 6 ký tự'),
})

type LoginFormData = z.infer<typeof loginSchema>

export function LoginForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [serverError, setServerError] = useState<string | null>(null)
  const [showForgotNotice, setShowForgotNotice] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null)
    try {
      const response = await login(data.email, data.password)
      setAuth(response.token, response.refreshToken, response.user)

      // Ưu tiên trang người dùng định vào trước khi bị chặn, nếu không thì
      // điều hướng theo role: admin → /admin, user → /
      const from = (location.state as { from?: { pathname: string } })?.from
        ?.pathname
      const fallback = response.user.role === 'admin' ? '/admin' : '/'
      navigate(from ?? fallback, { replace: true })
    } catch (err: unknown) {
      // Giữ nguyên giá trị đã gõ khi lỗi — react-hook-form không reset form
      setServerError(
        err instanceof Error ? err.message : 'Đã xảy ra lỗi, vui lòng thử lại'
      )
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.logo}>
            <svg
              className={styles.logoIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
              <path d="M6 12v5c3 3 9 3 12 0v-5" />
            </svg>
          </div>
          <h1 className={styles.title}>Đăng nhập</h1>
          <p className={styles.subtitle}>Trợ lý hỏi đáp Đại học</p>
        </div>

        {serverError && (
          <div
            className={styles.alertError}
            role="alert"
            id="login-error-alert"
          >
            <svg
              className={styles.alertIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            {serverError}
          </div>
        )}

        {showForgotNotice && (
          <div className={styles.alertInfo} role="status" id="forgot-notice">
            Tính năng quên mật khẩu cần backend gửi email đặt lại mật khẩu nên
            chưa khả dụng. Xem BACKEND_BLOCKED_FEATURES.md.
          </div>
        )}

        <form
          className={styles.form}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          id="login-form"
        >
          <Input
            id="login-email"
            label="Email"
            type="email"
            placeholder="name@university.edu.vn"
            autoComplete="email"
            error={errors.email?.message}
            {...register('email')}
          />

          <PasswordField
            error={errors.password?.message}
            {...register('password')}
          />

          <div className={styles.forgotPassword}>
            <button
              type="button"
              className={styles.forgotPasswordLink}
              id="forgot-password-btn"
              onClick={() => setShowForgotNotice(true)}
            >
              Quên mật khẩu?
            </button>
          </div>

          <Button
            type="submit"
            fullWidth
            disabled={isSubmitting}
            id="login-submit-btn"
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                Đang đăng nhập...
              </>
            ) : (
              'Đăng nhập'
            )}
          </Button>
        </form>

        <DemoAccounts />
      </div>
    </div>
  )
}
