import { responseFor } from '../mocks/fixtures.js';
export const delay = (ms, signal) => new Promise((resolve, reject) => {
  if (signal?.aborted) { reject(new DOMException('Aborted', 'AbortError')); return; }
  const abort = () => { clearTimeout(timer); signal.removeEventListener('abort', abort); reject(new DOMException('Aborted', 'AbortError')); };
  const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, ms);
  signal?.addEventListener('abort', abort, { once: true });
});
// Developer scenarios are selected only through /?scenario=..., outside product controls.
export const scenario = () => new URLSearchParams(globalThis.location?.search || '').get('scenario');
export const authService = {
  async login({ email, password, demo = false }) {
    await delay(550);
    if (!demo && scenario() === 'login-network') throw new Error('Kết nối demo bị gián đoạn. Hãy thử lại.');
    if (!demo && (password !== 'demo123' || scenario() === 'login-error')) throw new Error('Thông tin demo không hợp lệ. Dùng mật khẩu demo123 hoặc chọn dùng thử.');
    const normalized = demo ? 'student@demo.local' : email.trim().toLowerCase();
    return { id: normalized, email: normalized, displayName: demo ? 'Bạn' : normalized.split('@')[0] };
  }
};
export const chatService = {
  async *reply(question, { signal, forceSuccess = false, mode = scenario() } = {}) {
    const answer = responseFor(question);
    await delay(650, signal);
    for (let index = 0; index < answer.blocks.length; index++) {
      if (!forceSuccess && mode === 'chat-error' && index === 1) throw new Error('Phản hồi bị gián đoạn. Bạn có thể thử lại.');
      const block = answer.blocks[index];
      if (['paragraph', 'heading', 'code'].includes(block.type)) {
        for (let length = 16; length < block.text.length + 16; length += 16) {
          await delay(35, signal);
          yield { blocks: [...answer.blocks.slice(0, index), { ...block, text: block.text.slice(0, length) }], citations: [] };
        }
      } else { await delay(180, signal); yield { blocks: answer.blocks.slice(0, index + 1), citations: [] }; }
    }
    signal?.throwIfAborted();
    yield { blocks: answer.blocks, citations: answer.citations, complete: true };
  }
};
export const ticketService = {
  async create(fields) {
    await delay(650);
    if (scenario() === 'ticket-error') throw new Error('Chưa thể lưu ticket demo. Nội dung đã nhập vẫn được giữ lại.');
    const createdAt = new Date().toISOString();
    return { ...fields, id: `IU-${crypto.randomUUID().slice(0, 8).toUpperCase()}`, title: fields.title.trim(), description: fields.description.trim(), status: 'Đã gửi', createdAt, timeline: [{ status: 'Đã gửi', date: createdAt, note: 'Đã lưu trên thiết bị. Chưa gửi đến nhân viên IU.' }] };
  }
};
