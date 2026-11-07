/** Cookie credentials stay HttpOnly; only the CSRF token is held in memory. */
let csrfToken: string | null = null
let authVersion = 0

export function setCsrfToken(token: string | null) {
  if (token !== csrfToken) ++authVersion
  csrfToken = token
}

export class ApiError extends Error {
  readonly status: number
  readonly retryAfterSeconds: number | null
  constructor(
    status: number,
    message: string,
    retryAfterSeconds: number | null = null
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfterSeconds = retryAfterSeconds
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = 15000
): Promise<T> {
  const controller = new AbortController()
  const requestAuthVersion = authVersion
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(`/api${endpoint}`, {
      ...options,
      credentials: 'same-origin',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        ...options.headers,
      },
    })
  } catch (error) {
    clearTimeout(timeoutId)
    throw error
  }
  if (
    response.status === 401 &&
    endpoint !== '/auth/login' &&
    requestAuthVersion === authVersion
  ) {
    window.dispatchEvent(new Event('auth-expired'))
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    let message = `Lỗi HTTP ${response.status}`
    if (typeof body === 'object' && body !== null && 'message' in body) {
      message = String(body.message)
      if ('errors' in body && Array.isArray(body.errors)) {
        const first: unknown = body.errors[0]
        if (typeof first === 'object' && first !== null && 'message' in first) {
          message = String(first.message).replace(/^Value error, /, '')
        }
      }
    }
    clearTimeout(timeoutId)
    const retryAfter = response.headers.get('Retry-After')
    throw new ApiError(
      response.status,
      message,
      retryAfter !== null && /^\d+$/.test(retryAfter)
        ? Number(retryAfter)
        : null
    )
  }
  try {
    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  } finally {
    clearTimeout(timeoutId)
  }
}

export const httpClient = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, body: unknown, timeoutMs?: number) =>
    request<T>(
      endpoint,
      { method: 'POST', body: JSON.stringify(body) },
      timeoutMs
    ),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
  patch: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) }),
}
