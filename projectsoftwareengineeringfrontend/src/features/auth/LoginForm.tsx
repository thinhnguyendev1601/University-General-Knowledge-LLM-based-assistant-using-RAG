import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button, Input } from '@/components/ui'
import { login } from '@/services'
import { AuthPanel } from './AuthPanel'
import { DemoAccounts } from './DemoAccounts'
import { useAuthStore } from './authStore'
import { universityEmailSchema } from './authValidation'
import styles from './LoginForm.module.css'

const schema = z.object({
  email: universityEmailSchema,
  password: z
    .string()
    .min(1, 'Vui lòng nhập mật khẩu')
    .max(128, 'Mật khẩu quá dài'),
})
type FormData = z.infer<typeof schema>

export function LoginForm() {
  const [error, setError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })
  const submit = async (data: FormData) => {
    setError(null)
    try {
      const response = await login(data.email, data.password)
      setAuth(response)
      const from = (location.state as { from?: { pathname?: string } } | null)
        ?.from?.pathname
      const fallback = response.user.role === 'admin' ? '/admin' : '/'
      navigate(
        from?.startsWith('/') && !from.startsWith('//') ? from : fallback,
        { replace: true }
      )
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Không thể đăng nhập. Vui lòng thử lại.'
      )
    }
  }
  return (
    <AuthPanel
      title="Đăng nhập"
      description="Sử dụng tài khoản với email @university.edu.vn."
    >
      {error && (
        <p role="alert" className={styles.alertError}>
          {error}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit(submit)} noValidate>
        <Input
          id="login-email"
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          id="login-password"
          label="Mật khẩu"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <button
          type="button"
          className={styles.forgotPasswordLink}
          aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
          onClick={() => setShowPassword(!showPassword)}
        >
          {showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
        </button>
        <Link to="/forgot-password">Quên mật khẩu?</Link>
        <Button type="submit" disabled={isSubmitting} fullWidth>
          {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </Button>
      </form>
      <DemoAccounts />
    </AuthPanel>
  )
}
