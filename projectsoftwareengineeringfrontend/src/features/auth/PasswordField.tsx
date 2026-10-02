/**
 * PasswordField — ô mật khẩu kèm nút hiện/ẩn.
 * Tách riêng để LoginForm chỉ còn phần ghép form.
 */
import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { Input } from '@/components/ui'
import styles from './LoginForm.module.css'

interface PasswordFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(
  function PasswordField({ error, ...rest }, ref) {
    const [isVisible, setIsVisible] = useState(false)

    return (
      <div className={styles.passwordWrapper}>
        <Input
          ref={ref}
          id="login-password"
          label="Mật khẩu"
          type={isVisible ? 'text' : 'password'}
          placeholder="••••••••"
          autoComplete="current-password"
          error={error}
          {...rest}
        />
        <button
          type="button"
          className={styles.passwordToggle}
          onClick={() => setIsVisible((prev) => !prev)}
          aria-label={isVisible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
          id="toggle-password"
        >
          {isVisible ? (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    )
  }
)
