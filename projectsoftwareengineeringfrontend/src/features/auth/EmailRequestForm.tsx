import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input } from '@/components/ui'
import { forgotPassword } from '@/services'
import { universityEmailSchema } from './authValidation'
import { AuthPanel } from './AuthPanel'
import styles from './LoginForm.module.css'

const schema = z.object({ email: universityEmailSchema })
export function EmailRequestForm() {
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) })
  const submit = async ({ email }: z.infer<typeof schema>) => {
    setError(null)
    setMessage(null)
    try {
      const response = await forgotPassword(email)
      setMessage(response.message)
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Chưa gửi được yêu cầu. Vui lòng thử lại.'
      )
    }
  }
  return (
    <AuthPanel
      title="Quên mật khẩu"
      description="Nhập email @university.edu.vn đã dùng để đăng ký."
    >
      {error && (
        <p role="alert" className={styles.alertError}>
          {error}
        </p>
      )}
      {message && (
        <p role="status" className={styles.alertInfo}>
          {message}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit(submit)} noValidate>
        <Input
          id="request-email"
          label="Email trường"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email')}
        />
        <Button type="submit" disabled={isSubmitting} fullWidth>
          {isSubmitting ? 'Đang gửi...' : 'Gửi yêu cầu'}
        </Button>
      </form>
    </AuthPanel>
  )
}
