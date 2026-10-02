/**
 * HTTP Client thống nhất — tất cả API call đi qua đây.
 * Timeout, header Authorization, parse lỗi thống nhất, refresh token.
 * Khi backend thật sẵn sàng, chỉ cần đổi BASE_URL và bỏ mock trong services/.
 */

const BASE_URL = '/api'
const TIMEOUT_MS = 15000

/** Lỗi HTTP đã được chuẩn hoá để UI hiển thị message thống nhất. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface AuthTokens {
  token: string | null
  refreshToken: string | null
}

/**
 * Đọc token từ localStorage của auth store (Zustand persist).
 * Không import authStore để tránh vòng phụ thuộc services → features.
 */
function readTokens(): AuthTokens {
  const empty: AuthTokens = { token: null, refreshToken: null }
  const stored = localStorage.getItem('auth-storage')
  if (!stored) return empty

  try {
    const parsed: unknown = JSON.parse(stored)
    if (typeof parsed !== 'object' || parsed === null || !('state' in parsed)) {
      return empty
    }
    const state = (parsed as { state: Partial<AuthTokens> }).state
    return {
      token: state.token ?? null,
      refreshToken: state.refreshToken ?? null,
    }
  } catch {
    return empty
  }
}

/**
 * Gọi endpoint refresh để lấy token mới.
 * Backend chưa có endpoint này nên luôn trả null — xem BACKEND_BLOCKED_FEATURES.md.
 * Khi backend sẵn sàng: POST /api/auth/refresh { refreshToken } → { token }.
 */
async function refreshAccessToken(): Promise<string | null> {
  return null
}

async function parseError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null)
  const message =
    typeof body === 'object' && body !== null && 'message' in body
      ? String((body as { message: unknown }).message)
      : `Lỗi HTTP ${response.status}`
  return new ApiError(response.status, message)
}

async function send(
  endpoint: string,
  options: RequestInit,
  token: string | null
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    return await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    })
  } finally {
    clearTimeout(timeoutId)
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const { token } = readTokens()
  let response = await send(endpoint, options, token)

  // Token hết hạn → thử refresh một lần rồi gọi lại
  if (response.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      response = await send(endpoint, options, newToken)
    }
  }

  if (!response.ok) {
    throw await parseError(response)
  }

  // DELETE thường không trả body
  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const httpClient = {
  get: <T>(endpoint: string) => request<T>(endpoint),

  post: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }),

  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
}
