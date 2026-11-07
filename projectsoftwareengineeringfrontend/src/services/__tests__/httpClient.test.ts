import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, httpClient, setCsrfToken } from '../httpClient'

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken(null)
})

it('uses cookies and an in-memory CSRF header, never a local mock bearer token', async () => {
  localStorage.setItem(
    'auth-storage',
    JSON.stringify({ state: { token: 'obsolete' } })
  )
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('csrf-secret')
  await httpClient.post('/auth/logout', {})
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/auth/logout',
    expect.objectContaining({
      credentials: 'same-origin',
      headers: expect.objectContaining({
        'X-CSRF-Token': 'csrf-secret',
        'X-Requested-With': 'XMLHttpRequest',
      }),
    })
  )
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined()
})

it('notifies the app about expired sessions without retrying unsafe requests', async () => {
  const listener = vi.fn()
  window.addEventListener('auth-expired', listener)
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: 'Phiên hết hạn' }), {
      status: 401,
    })
  )
  vi.stubGlobal('fetch', fetchMock)
  await expect(httpClient.get('/auth/me')).rejects.toBeInstanceOf(ApiError)
  expect(listener).toHaveBeenCalledOnce()
  expect(fetchMock).toHaveBeenCalledOnce()
  window.removeEventListener('auth-expired', listener)
})

it('exposes Retry-After so chat can wait before retrying a busy request', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ message: 'Hệ thống đang bận' }), {
          status: 503,
          headers: { 'Retry-After': '5' },
        })
      )
  )
  await expect(httpClient.post('/chat/messages', {})).rejects.toMatchObject({
    status: 503,
    retryAfterSeconds: 5,
  })
})

it('does not expire a new login because an old session request returned 401 late', async () => {
  const listener = vi.fn()
  window.addEventListener('auth-expired', listener)
  let finish: (response: Response) => void = () => {}
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
  )
  setCsrfToken('old-session')
  const pending = httpClient.get('/chat/conversations')
  setCsrfToken('new-session')
  finish(
    new Response(JSON.stringify({ message: 'Old session expired' }), {
      status: 401,
    })
  )
  await expect(pending).rejects.toBeInstanceOf(ApiError)
  expect(listener).not.toHaveBeenCalled()
  window.removeEventListener('auth-expired', listener)
})
