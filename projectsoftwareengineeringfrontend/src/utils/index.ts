/**
 * Tạo UUID đơn giản dùng cho mock data.
 * Không dùng cho bảo mật — chỉ để tạo ID client-side.
 */
export function generateId(): string {
  return crypto.randomUUID()
}

/**
 * Format ngày giờ ISO 8601 thành chuỗi dễ đọc
 */
export function formatDate(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Vừa xong'
  if (diffMins < 60) return `${diffMins} phút trước`
  if (diffHours < 24) return `${diffHours} giờ trước`
  if (diffDays < 7) return `${diffDays} ngày trước`

  return date.toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/**
 * Tạo tiêu đề hội thoại từ nội dung câu hỏi đầu tiên.
 * Cắt ngắn nếu quá dài.
 */
export function generateConversationTitle(firstMessage: string): string {
  const maxLength = 40
  const trimmed = firstMessage.trim()
  if (trimmed.length <= maxLength) return trimmed
  return trimmed.substring(0, maxLength) + '...'
}

/**
 * Delay helper — dùng cho mock service
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
