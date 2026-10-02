/**
 * Header — thanh nav cố định trên cùng.
 * Hiển thị logo, theme toggle, avatar/role, link admin.
 */
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/features/auth'
import { useUIStore } from '@/hooks/useUIStore'
import styles from './Header.module.css'

export function Header() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const theme = useUIStore((state) => state.theme)
  const toggleTheme = useUIStore((state) => state.toggleTheme)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((word) => word[0])
      .join('')
      .substring(0, 2)
      .toUpperCase()
  }

  return (
    <header className={styles.header} id="app-header">
      <Link to="/" className={styles.headerBrand}>
        <div className={styles.headerLogo}>
          <svg
            className={styles.headerLogoIcon}
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
        <span className={styles.headerBrandName}>UniAssistant</span>
      </Link>

      <nav className={styles.headerNav}>
        <button
          className={styles.themeToggle}
          onClick={toggleTheme}
          aria-label={
            theme === 'light'
              ? 'Chuyển sang chế độ tối'
              : 'Chuyển sang chế độ sáng'
          }
          id="theme-toggle-btn"
        >
          {theme === 'light' ? (
            <svg
              className={styles.themeToggleIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          ) : (
            <svg
              className={styles.themeToggleIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          )}
        </button>

        {user ? (
          <div className={styles.userInfo}>
            {user.role === 'admin' && (
              <Link to="/admin" className={styles.adminLink} id="admin-link">
                Quản lý dữ liệu
              </Link>
            )}
            <div className={styles.userAvatar} title={user.name}>
              {getInitials(user.name)}
            </div>
            <div>
              <div className={styles.userName}>{user.name}</div>
              <div className={styles.userRole}>{user.role}</div>
            </div>
            <button
              className={styles.logoutBtn}
              onClick={handleLogout}
              id="logout-btn"
            >
              Đăng xuất
            </button>
          </div>
        ) : (
          <Link to="/login" className={styles.adminLink} id="login-link">
            Đăng nhập
          </Link>
        )}
      </nav>
    </header>
  )
}
