import { useEffect, useRef, useState } from 'react';
import { h, Button, EmptyState, Field, Icon, StatusBadge } from '../components/ui.js';
import { useStore } from '../app/store.js';
import { navigate, setNavigationGuard } from '../app/router.js';
import { formatDate, validateTicket } from '../utils/validation.js';
import { statuses } from '../mocks/fixtures.js';
import { ticketService } from '../services/mock.js';
const categories = ['Nội dung trả lời', 'Nguồn tài liệu', 'Vấn đề giao diện', 'Khác'];
export function TicketList() {
  const { state } = useStore();
  const [search, setSearch] = useState(''); const [status, setStatus] = useState('');
  const filtered = [...state.tickets].filter(ticket => `${ticket.title} ${ticket.id}`.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi')) && (!status || ticket.status === status)).sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));
  return h('section', { className: 'content-page' }, h('div', { className: 'page-title-row' }, h('div', null, h('span', { className: 'eyebrow' }, 'LUÔN CÓ CÁCH ĐỂ TIẾP TỤC'), h('h1', null, 'Ticket của tôi'), h('p', { className: 'muted' }, 'Theo dõi những câu hỏi cần thêm một chút hỗ trợ.')), h(Button, { variant: 'primary', icon: 'plus', onClick: () => navigate('/tickets/new') }, 'Tạo ticket')),
    h('div', { className: 'demo-notice' }, h(Icon, { name: 'help', size: 18 }), 'Ticket demo chỉ lưu trên thiết bị, chưa gửi đến nhân viên IU.'),
    h('div', { className: 'filters' }, h('div', { className: 'search-input' }, h(Icon, { name: 'search', size: 18 }), h('input', { value: search, onChange: e => setSearch(e.target.value), placeholder: 'Tìm theo tiêu đề hoặc mã ticket', 'aria-label': 'Tìm ticket theo tiêu đề hoặc mã' })), h('select', { value: status, onChange: e => setStatus(e.target.value), 'aria-label': 'Lọc trạng thái ticket' }, h('option', { value: '' }, 'Tất cả trạng thái'), statuses.map(value => h('option', { key: value }, value)))),
    h('p', { className: 'small muted result-count', role: 'status' }, `${filtered.length} ticket`),
    filtered.length ? h('div', { className: 'ticket-table-wrap' }, h('table', { className: 'ticket-table' }, h('thead', null, h('tr', null, ['Ticket', 'Danh mục', 'Trạng thái', 'Ngày tạo'].map(title => h('th', { key: title, scope: 'col' }, title)))), h('tbody', null, filtered.map(ticket => h('tr', { key: ticket.id }, h('td', { 'data-label': 'Ticket' }, h('span', { className: 'ticket-id' }, ticket.id), h('a', { href: `/tickets/${ticket.id}`, onClick: e => { if (!e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); navigate(`/tickets/${ticket.id}`); } } }, ticket.title)), h('td', { 'data-label': 'Danh mục' }, ticket.category), h('td', { 'data-label': 'Trạng thái' }, h(StatusBadge, { status: ticket.status })), h('td', { 'data-label': 'Ngày tạo' }, formatDate(ticket.createdAt))))))) : h(EmptyState, { title: state.tickets.length ? 'Chưa tìm thấy ticket phù hợp' : 'Bạn chưa có ticket nào', detail: state.tickets.length ? 'Thử một từ khóa hoặc trạng thái khác.' : 'Khi cần thêm hỗ trợ, bạn có thể bắt đầu tại đây.' }, h(Button, { onClick: () => { setSearch(''); setStatus(''); } }, 'Xóa bộ lọc')));
}
export function TicketForm() {
  const { dispatch, notify, state } = useStore();
  const params = new URLSearchParams(location.search);
  const [values, setValues] = useState(() => ({ title: '', category: '', course: '', description: '', conversationId: params.get('conversation') || null, selectedExcerpt: (params.get('excerpt') || '').slice(0, 1500) }));
  const [errors, setErrors] = useState({}); const [failure, setFailure] = useState(''); const [busy, setBusy] = useState(false);
  const form = useRef(null); const locked = useRef(false); const dirty = useRef(false); const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    setNavigationGuard(() => !dirty.current || window.confirm('Bạn có thay đổi chưa gửi. Rời form và bỏ các thay đổi?'));
    const beforeUnload = event => { if (dirty.current) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', beforeUnload);
    return () => { mounted.current = false; setNavigationGuard(null); window.removeEventListener('beforeunload', beforeUnload); };
  }, []);
  function update(name, value) { dirty.current = true; setValues(previous => ({ ...previous, [name]: value })); }
  async function submit(event) {
    event.preventDefault(); if (locked.current) return;
    const nextErrors = validateTicket(values); setErrors(nextErrors); setFailure('');
    if (Object.keys(nextErrors).length) { form.current.elements[Object.keys(nextErrors)[0]].focus(); return; }
    locked.current = true; setBusy(true);
    try {
      const ticket = await ticketService.create(values);
      if (!mounted.current) return;
      dispatch({ type: 'ticket-add', ticket }); dirty.current = false;
      notify('Đã lưu ticket demo trên thiết bị.'); navigate(`/tickets/${ticket.id}`, { skipGuard: true });
    } catch (error) { if (mounted.current) setFailure(error.message); }
    finally { locked.current = false; if (mounted.current) setBusy(false); }
  }
  const props = name => ({ id: name, name, value: values[name], disabled: busy, 'aria-invalid': !!errors[name], 'aria-describedby': errors[name] ? `${name}-error` : undefined, onChange: e => update(name, e.target.value) });
  const linked = state.conversations.find(c => c.id === values.conversationId);
  return h('section', { className: 'content-page narrow' }, h(Button, { variant: 'ghost', icon: 'back', onClick: () => navigate('/tickets') }, 'Ticket của tôi'), h('h1', null, 'Bạn cần hỗ trợ điều gì?'), h('p', { className: 'muted' }, 'Chia sẻ rõ vấn đề để dễ dàng tìm cách giải quyết.'), h('div', { className: 'demo-notice' }, h(Icon, { name: 'help', size: 18 }), 'Bản demo: ticket chỉ lưu trên thiết bị, chưa gửi đến nhân viên IU.'),
    h('form', { className: 'panel ticket-form', ref: form, onSubmit: submit, noValidate: true },
      h(Field, { label: 'Tiêu đề *', name: 'title', error: errors.title }, h('input', { ...props('title'), maxLength: 120, placeholder: 'Tóm tắt vấn đề bạn đang gặp' })),
      h('div', { className: 'form-grid' }, h(Field, { label: 'Danh mục *', name: 'category', error: errors.category }, h('select', props('category'), h('option', { value: '' }, 'Chọn danh mục'), categories.map(category => h('option', { key: category }, category)))), h(Field, { label: 'Môn học (không bắt buộc)', name: 'course' }, h('input', { ...props('course'), maxLength: 100, placeholder: 'Ví dụ: Calculus 1' }))),
      h(Field, { label: 'Mô tả *', name: 'description', error: errors.description }, h('textarea', { ...props('description'), rows: 6, maxLength: 3000, placeholder: 'Bạn đang gặp khó khăn ở đâu? Bạn mong muốn được hỗ trợ như thế nào?' }), h('span', { className: 'character-count' }, `${values.description.length}/3.000`)),
      values.conversationId && h('div', { className: 'linked-context' }, h('strong', null, 'Hội thoại liên quan'), h('p', { className: 'muted small' }, linked?.title || 'Hội thoại không còn khả dụng.'), values.selectedExcerpt && h('blockquote', null, values.selectedExcerpt), h(Button, { variant: 'ghost', disabled: busy, onClick: () => { dirty.current = true; setValues(previous => ({ ...previous, selectedExcerpt: '', conversationId: null })); } }, 'Bỏ liên kết và trích đoạn')),
      failure && h('p', { className: 'alert error', role: 'alert' }, failure), h('div', { className: 'form-actions' }, h(Button, { disabled: busy, onClick: () => navigate('/tickets') }, 'Hủy'), h(Button, { variant: 'primary', type: 'submit', disabled: busy }, busy ? 'Đang lưu ticket…' : 'Gửi ticket demo'))));
}
export function TicketDetail({ id }) {
  const { state } = useStore(); const ticket = state.tickets.find(t => t.id === id);
  if (!ticket) return h(EmptyState, { title: 'Không tìm thấy ticket', detail: 'Mã ticket không tồn tại trong dữ liệu demo của bạn.' }, h(Button, { onClick: () => navigate('/tickets') }, 'Về danh sách ticket'));
  const conversation = state.conversations.find(c => c.id === ticket.conversationId);
  return h('section', { className: 'content-page narrow' }, h(Button, { variant: 'ghost', icon: 'back', onClick: () => navigate('/tickets') }, 'Ticket của tôi'), h('div', { className: 'detail-title' }, h('span', { className: 'ticket-id' }, ticket.id), h('h1', null, ticket.title), h(StatusBadge, { status: ticket.status })), h('div', { className: 'panel detail-panel' }, h('dl', { className: 'detail-meta' }, h('div', null, h('dt', null, 'Danh mục'), h('dd', null, ticket.category)), h('div', null, h('dt', null, 'Môn học'), h('dd', null, ticket.course || 'Không chỉ định')), h('div', null, h('dt', null, 'Ngày tạo'), h('dd', null, formatDate(ticket.createdAt)))), h('h2', null, 'Nội dung hỗ trợ'), h('p', { className: 'preserve-lines' }, ticket.description), ticket.selectedExcerpt && h('div', { className: 'linked-context' }, h('h3', null, 'Trích đoạn hội thoại'), h('blockquote', null, ticket.selectedExcerpt)), ticket.conversationId && (conversation ? h(Button, { variant: 'ghost', icon: 'chat', onClick: () => navigate(`/chat/${conversation.id}`) }, 'Mở hội thoại liên quan') : h('p', { className: 'small muted' }, 'Hội thoại liên quan đã bị xóa. Trích đoạn vẫn được giữ trong ticket.'))),
    h('div', { className: 'panel detail-panel' }, h('h2', null, 'Tiến trình mô phỏng'), h('ol', { className: 'timeline' }, ticket.timeline.map((entry, index) => h('li', { key: index }, h('span', { className: 'timeline-dot' }), h('div', null, h('strong', null, entry.status), h('span', { className: 'small muted' }, formatDate(entry.date)), h('p', null, entry.note))))), h('p', { className: 'small muted' }, 'Thông tin và trạng thái là dữ liệu demo. Ticket chưa gửi đến nhân viên IU.')));
}

