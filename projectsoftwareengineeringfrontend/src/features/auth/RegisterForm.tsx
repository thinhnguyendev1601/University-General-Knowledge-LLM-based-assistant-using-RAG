import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input } from '@/components/ui'
import { registerAccount } from '@/services'
import { AuthPanel } from './AuthPanel'
import { registrationSchema } from './authValidation'
import styles from './LoginForm.module.css'

type FormData = z.infer<typeof registrationSchema>

export function RegisterForm() {
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    resetField,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(registrationSchema) })
  const submit = async ({ name, email, password }: FormData) => {
    setError(null)
    try {
      const response = await registerAccount({ name, email, password })
      resetField('password')
      resetField('confirmPassword')
      setMessage(response.message)
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Không thể đăng ký. Vui lòng thử lại.'
      )
    }
  }
  return (
    <AuthPanel
      title="Đăng ký tài khoản"
      description="Dùng email @university.edu.vn để đăng ký và đăng nhập ngay. Mật khẩu từ 15 đến 128 ký tự."
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
      ) : (
        <form
          className={styles.form}
          onSubmit={handleSubmit(submit)}
          noValidate
        >
          <Input
            id="register-name"
            label="Họ tên"
            autoComplete="name"
            error={errors.name?.message}
            {...register('name')}
          />
          <Input
            id="register-email"
            label="Email trường"
            type="email"
            autoComplete="username"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            id="register-password"
            label="Mật khẩu"
            type="password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <Input
            id="register-confirm"
            label="Xác nhận mật khẩu"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Đang đăng ký...' : 'Tạo tài khoản'}
          </Button>
        </form>
      )}
    </AuthPanel>
  )
}
