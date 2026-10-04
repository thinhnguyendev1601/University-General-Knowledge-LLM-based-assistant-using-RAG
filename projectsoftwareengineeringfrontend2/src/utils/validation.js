export function validateLogin({ email, password }) {
  const errors = {};
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) errors.email = 'Nhập một địa chỉ email hợp lệ.';
  if (!password.trim()) errors.password = 'Vui lòng nhập mật khẩu demo.';
  return errors;
}
export function validateTicket({ title, category, description }) {
  const errors = {};
  if (title.trim().length < 5 || title.trim().length > 120) errors.title = 'Tiêu đề cần từ 5 đến 120 ký tự.';
  if (!['Nội dung trả lời', 'Nguồn tài liệu', 'Vấn đề giao diện', 'Khác'].includes(category)) errors.category = 'Chọn một danh mục hỗ trợ.';
  if (description.trim().length < 20 || description.trim().length > 3000) errors.description = 'Mô tả cần từ 20 đến 3.000 ký tự.';
  return errors;
}
export function validTitle(value) { return value.trim().length >= 1 && value.trim().length <= 80; }
export function historyGroup(date, now = new Date()) {
  const time = new Date(date);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (time >= today) return 'Hôm nay';
  const weekStart = new Date(today); weekStart.setDate(weekStart.getDate() - 7);
  return time >= weekStart ? '7 ngày gần đây' : 'Cũ hơn';
}
export const formatDate = value => new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value));
export function safeUrl(value) { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } }
