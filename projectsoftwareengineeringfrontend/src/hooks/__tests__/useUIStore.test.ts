import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from '../useUIStore'

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({ theme: 'light', isChatOpen: false })
    document.documentElement.removeAttribute('data-theme')
  })

  it('mở và đóng chat', () => {
    useUIStore.getState().openChat()
    expect(useUIStore.getState().isChatOpen).toBe(true)

    useUIStore.getState().closeChat()
    expect(useUIStore.getState().isChatOpen).toBe(false)
  })

  it('toggle chat đổi trạng thái qua lại', () => {
    useUIStore.getState().toggleChat()
    expect(useUIStore.getState().isChatOpen).toBe(true)

    useUIStore.getState().toggleChat()
    expect(useUIStore.getState().isChatOpen).toBe(false)
  })

  it('đổi theme và ghi data-theme lên <html>', () => {
    useUIStore.getState().toggleTheme()

    expect(useUIStore.getState().theme).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('đổi theme ngược lại về light', () => {
    useUIStore.getState().setTheme('dark')
    useUIStore.getState().toggleTheme()

    expect(useUIStore.getState().theme).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('persist theme vào localStorage, không persist trạng thái chat', () => {
    useUIStore.getState().setTheme('dark')
    useUIStore.getState().openChat()

    const stored = localStorage.getItem('ui-storage')
    expect(stored).not.toBeNull()

    const parsed = JSON.parse(stored as string)
    expect(parsed.state.theme).toBe('dark')
    expect(parsed.state.isChatOpen).toBeUndefined()
  })
})
