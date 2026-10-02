import { describe, it, expect, vi, afterEach } from 'vitest'
import { formatDate, generateConversationTitle, generateId, delay } from '..'

describe('generateConversationTitle', () => {
  it('giữ nguyên câu hỏi ngắn', () => {
    expect(generateConversationTitle('Lịch thi khi nào?')).toBe(
      'Lịch thi khi nào?'
    )
  })

  it('cắt ngắn câu hỏi dài quá 40 ký tự và thêm dấu ...', () => {
    const long = 'a'.repeat(50)
    const title = generateConversationTitle(long)
    expect(title).toHaveLength(43)
    expect(title.endsWith('...')).toBe(true)
  })

  it('bỏ khoảng trắng ở hai đầu', () => {
    expect(generateConversationTitle('  Học bổng  ')).toBe('Học bổng')
  })
})

describe('formatDate', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('trả về "Vừa xong" khi dưới 1 phút', () => {
    expect(formatDate(new Date().toISOString())).toBe('Vừa xong')
  })

  it('trả về số phút khi dưới 1 giờ', () => {
    const fiveMinsAgo = new Date(Date.now() - 5 * 60_000).toISOString()
    expect(formatDate(fiveMinsAgo)).toBe('5 phút trước')
  })

  it('trả về số giờ khi dưới 1 ngày', () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 3_600_000).toISOString()
    expect(formatDate(threeHoursAgo)).toBe('3 giờ trước')
  })

  it('trả về số ngày khi dưới 1 tuần', () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 86_400_000).toISOString()
    expect(formatDate(twoDaysAgo)).toBe('2 ngày trước')
  })

  it('trả về ngày dd/mm/yyyy khi quá 1 tuần', () => {
    const old = new Date('2024-01-15T10:00:00.000Z').toISOString()
    expect(formatDate(old)).toMatch(/\d{2}\/\d{2}\/\d{4}/)
  })
})

describe('generateId', () => {
  it('tạo ID khác nhau mỗi lần gọi', () => {
    expect(generateId()).not.toBe(generateId())
  })
})

describe('delay', () => {
  it('resolve sau khoảng thời gian cho trước', async () => {
    const start = Date.now()
    await delay(20)
    expect(Date.now() - start).toBeGreaterThanOrEqual(15)
  })
})
