import type { AuthResponse, ChatConversation, ChatMessage, User } from '@/types'
import { delay, generateId } from '@/utils'

interface MockUser {
  email: string
  password: string
  user: User
}

/** Tài khoản thử nghiệm hiển thị ở trang login khi chưa có backend. */
export interface DemoAccount {
  role: User['role']
  email: string
  password: string
}

/**
 * Mock users cho đăng nhập test.
 * Mật khẩu giả lập, KHÔNG phải logic bảo mật thật.
 */
const MOCK_USERS: MockUser[] = [
  {
    email: 'admin@university.edu.vn',
    password: 'admin123',
    user: {
      id: 'usr-001',
      name: 'Quản trị viên',
      email: 'admin@university.edu.vn',
      role: 'admin' as const,
    },
  },
  {
    email: 'user@university.edu.vn',
    password: 'user123',
    user: {
      id: 'usr-002',
      name: 'Nguyễn Văn A',
      email: 'user@university.edu.vn',
      role: 'user' as const,
    },
  },
]

const MOCK_REPLIES = [
  'Chào bạn! Tôi là trợ lý ảo của Đại học. Bạn cần hỗ trợ gì?',
  'Lịch thi học kỳ 2 năm 2025-2026 sẽ được cập nhật trên trang Phòng Đào tạo vào tuần đầu tháng 5. Bạn có thể theo dõi tại mục Thông báo trên website trường.',
  'Để đăng ký học bổng, bạn cần nộp hồ sơ tại Phòng Công tác Sinh viên trước ngày 30/4 hàng năm. Hồ sơ gồm: đơn xin học bổng, bảng điểm, giấy xác nhận thu nhập gia đình.',
  'Thủ tục xin cấp lại thẻ sinh viên: bạn cần viết đơn tại Phòng Đào tạo kèm 1 ảnh 3x4, giấy tờ tùy thân. Lệ phí: 50.000 VND. Thời gian xử lý: 5-7 ngày làm việc.',
  'Thư viện mở cửa từ 7:00 - 21:00 các ngày trong tuần (trừ Chủ nhật). Sinh viên cần mang thẻ sinh viên để mượn sách. Mỗi lần mượn tối đa 5 cuốn, thời hạn 14 ngày.',
  'Phòng Tài chính hỗ trợ tra cứu học phí qua cổng thông tin sinh viên. Bạn đăng nhập bằng mã số sinh viên và mật khẩu được cấp đầu năm.',
]

/**
 * Mock login — trả về dữ liệu giả đúng hợp đồng API.
 * Delay ~800ms để mô phỏng network.
 */
export async function mockLogin(
  email: string,
  password: string
): Promise<AuthResponse> {
  await delay(800)

  const found = MOCK_USERS.find(
    (mockUser) => mockUser.email === email && mockUser.password === password
  )

  if (!found) {
    throw new Error('Email hoặc mật khẩu không đúng')
  }

  return {
    token: `mock-jwt-token-${found.user.id}`,
    refreshToken: `mock-refresh-token-${found.user.id}`,
    user: found.user,
  }
}

/**
 * Danh sách tài khoản demo — lấy từ MOCK_USERS để component không hardcode.
 */
export function mockGetDemoAccounts(): DemoAccount[] {
  return MOCK_USERS.map((mockUser) => ({
    role: mockUser.user.role,
    email: mockUser.email,
    password: mockUser.password,
  }))
}

/**
 * Tỷ lệ mô phỏng lỗi mạng (0..1) để test nút "Thử lại" khi chưa có backend.
 * Bật bằng VITE_MOCK_ERROR_RATE=0.3 trong .env.local. Mặc định 0 = không lỗi.
 */
function getMockErrorRate(): number {
  const raw = import.meta.env.VITE_MOCK_ERROR_RATE
  const rate = Number(raw)
  return Number.isFinite(rate) ? Math.min(Math.max(rate, 0), 1) : 0
}

/**
 * Mock gửi tin nhắn chat — trả về phản hồi giả từ "trợ lý".
 * Delay 1-2s để mô phỏng xử lý server.
 */
export async function mockSendMessage(
  conversationId: string,
  _content: string
): Promise<ChatMessage> {
  await delay(1000 + Math.random() * 1000)

  // Mô phỏng lỗi mạng để kiểm tra luồng hiển thị lỗi + nút Thử lại
  if (Math.random() < getMockErrorRate()) {
    throw new Error('Mock network error')
  }

  const randomReply =
    MOCK_REPLIES[Math.floor(Math.random() * MOCK_REPLIES.length)]

  return {
    id: generateId(),
    conversationId,
    role: 'assistant',
    content: randomReply,
    createdAt: new Date().toISOString(),
  }
}

/**
 * Mock lấy danh sách hội thoại
 */
export async function mockGetConversations(): Promise<ChatConversation[]> {
  await delay(300)
  return []
}

/**
 * Mock lấy tin nhắn của hội thoại
 */
export async function mockGetMessages(
  _conversationId: string
): Promise<ChatMessage[]> {
  await delay(300)
  return []
}

/**
 * Mock xoá hội thoại
 */
export async function mockDeleteConversation(
  _conversationId: string
): Promise<void> {
  await delay(300)
}
