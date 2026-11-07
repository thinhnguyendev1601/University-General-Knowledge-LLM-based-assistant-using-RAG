import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button, Input } from '@/components/ui'
import { resetPassword } from '@/services'
import { useAuthStore } from './authStore'
import { newPasswordSchema } from './authValidation'
import { AuthPanel } from './AuthPanel'
import styles from './LoginForm.module.css'

const schema = z
  .object({ password: newPasswordSchema, confirmPassword: z.string() })
  .refine((data) => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Mật khẩu xác nhận không khớp',
  })
export function TokenActionForm() {
  const location = useLocation()
  const navigate = useNavigate()
  const [token, setToken] = useState(
    () => new URLSearchParams(location.hash.slice(1)).get('token') ?? ''
  )
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) })
  // Capture once in memory, then remove the secret from browser history/address bar.
  useEffect(() => {
    navigate(location.pathname, { replace: true })
  }, [navigate, location.pathname])
  const submit = async (password: string) => {
    setError(null)
    setBusy(true)
    try {
      const response = await resetPassword(token, password)
      useAuthStore.getState().clearAuth()
      setMessage(response.message)
      setToken('')
      reset()
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Không thể xử lý liên kết. Vui lòng thử lại.'
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <AuthPanel
      title="Đặt lại mật khẩu"
      description="Liên kết có thời hạn và chỉ sử dụng được một lần."
    >
      {error && (
        <p role="alert" className={styles.alertError}>
          {error}
        </p>
      )}
      {message ? (
        <p role="status" className={styles.alertInfo}>
          {message}
        </p>
      ) : !token ? (
        <p role="alert">
          Liên kết thiếu mã đặt lại mật khẩu. Vui lòng mở liên kết trong email
          hoặc gửi lại yêu cầu quên mật khẩu.
        </p>
      ) : (
        <form
          className={styles.form}
          noValidate
          onSubmit={handleSubmit((data) => submit(data.password))}
        >
          <Input
            id="reset-password"
            label="Mật khẩu mới"
            type="password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <Input
            id="reset-confirm"
            label="Xác nhận mật khẩu"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
          <Button type="submit" disabled={busy || isSubmitting} fullWidth>
            {busy ? 'Đang cập nhật...' : 'Đổi mật khẩu'}
          </Button>
        </form>
      )}
    </AuthPanel>
  )
}
