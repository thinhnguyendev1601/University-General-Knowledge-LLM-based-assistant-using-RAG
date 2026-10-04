import { createFixtures, statuses } from '../mocks/fixtures.js';
const PREFIX = 'iu-study:v1:';
export const sessionKey = `${PREFIX}session`;
const dateValid = value => typeof value === 'string' && Number.isFinite(Date.parse(value));
const blockValid = block => block && ['paragraph', 'heading', 'code', 'list', 'table'].includes(block.type) && (['paragraph', 'heading', 'code'].includes(block.type) ? typeof block.text === 'string' : block.type === 'list' ? Array.isArray(block.items) && block.items.every(x => typeof x === 'string') : Array.isArray(block.headers) && block.headers.every(x => typeof x === 'string') && Array.isArray(block.rows) && block.rows.every(row => Array.isArray(row) && row.every(x => typeof x === 'string')));
const optionalString = value => value == null || typeof value === 'string';
const citationValid = source => source && typeof source.id === 'string' && typeof source.documentTitle === 'string' && typeof source.excerpt === 'string' && optionalString(source.course) && optionalString(source.section) && optionalString(source.url) && (source.page == null || typeof source.page === 'number');
export function validData(value) {
  return value?.version === 1 && Array.isArray(value.conversations) && Array.isArray(value.tickets) &&
    value.conversations.every(c => c && typeof c.id === 'string' && typeof c.title === 'string' && dateValid(c.createdAt) && dateValid(c.updatedAt) && Array.isArray(c.messages) && c.messages.every(m => m && typeof m.id === 'string' && ['user', 'assistant'].includes(m.role) && ['complete', 'streaming', 'waiting', 'stopped', 'error'].includes(m.status) && optionalString(m.error) && dateValid(m.createdAt) && (m.role === 'user' ? typeof m.content === 'string' : Array.isArray(m.content) && m.content.every(blockValid) && Array.isArray(m.citations) && m.citations.every(citationValid)))) &&
    value.tickets.every(t => t && typeof t.id === 'string' && typeof t.title === 'string' && typeof t.description === 'string' && typeof t.category === 'string' && typeof t.selectedExcerpt === 'string' && optionalString(t.course) && optionalString(t.conversationId) && statuses.includes(t.status) && dateValid(t.createdAt) && Array.isArray(t.timeline) && t.timeline.every(item => item && statuses.includes(item.status) && dateValid(item.date) && typeof item.note === 'string'));
}
export function readSession(storage) {
  try { const value = JSON.parse(storage.getItem(sessionKey)); return value && typeof value.id === 'string' && typeof value.email === 'string' && typeof value.displayName === 'string' ? value : null; } catch { return null; }
}
export function readData(storage, userId) {
  try {
    const raw = storage.getItem(PREFIX + userId);
    if (!raw) return { data: createFixtures(), warning: '' };
    const value = JSON.parse(raw);
    if (!validData(value)) throw new Error('Invalid schema');
    return { data: { conversations: value.conversations.map(c => ({ ...c, messages: c.messages.map(m => ['waiting', 'streaming'].includes(m.status) ? { ...m, status: 'stopped' } : m) })), tickets: value.tickets }, warning: '' };
  } catch { return { data: createFixtures(), warning: 'Không thể đọc dữ liệu đã lưu. Đang dùng dữ liệu mẫu; bạn có thể đặt lại dữ liệu demo trong tài khoản.' }; }
}
export function writeData(storage, userId, data) {
  try { storage.setItem(PREFIX + userId, JSON.stringify({ version: 1, ...data })); return ''; }
  catch { return 'Không thể lưu trên thiết bị. Thay đổi hiện chỉ giữ trong phiên này.'; }
}
