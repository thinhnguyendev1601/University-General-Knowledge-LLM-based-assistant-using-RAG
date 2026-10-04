import { createElement as h, useEffect, useId, useRef } from 'react';
export { h };
const paths = {
  book: 'M4 5h6a2 2 0 0 1 2 2v13a3 3 0 0 0-3-2H4V5Zm16 0h-6a2 2 0 0 0-2 2v13a3 3 0 0 1 3-2h5V5Z',
  plus: 'M12 5v14M5 12h14', search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  chat: 'M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z',
  ticket: 'M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4V5Zm10 0v2m0 3v2m0 3v2m0 2v-1',
  spark: 'm12 3 2.8 6.2L21 12l-6.2 2.8L12 21l-2.8-6.2L3 12l6.2-2.8L12 3Z',
  pen: 'm16 3 5 5L9 20l-6 1 1-6L16 3Zm-2 2 5 5', cap: 'm2 9 10-5 10 5-10 5L2 9Zm4 2v6l6 3 6-3v-6m4-2v8',
  arrow: 'M12 19V5m-6 6 6-6 6 6', close: 'm6 6 12 12M6 18 18 6', menu: 'M4 6h16M4 12h16M4 18h16',
  more: 'M5 12h.01M12 12h.01M19 12h.01', chevron: 'm9 5 7 7-7 7', back: 'm12 5-7 7 7 7M5 12h14',
  copy: 'M9 9h11v11H9V9ZM5 15H3V3h12v2', check: 'm5 12 4 4L19 6',
  thumb: 'M7 10v10H3V10h4Zm0 0 5-7h2v7h6l-2 10H7', logout: 'M9 4H4v16h5m5-13 5 5-5 5m-7-5h12',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  help: 'M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 4h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z'
};
export function Icon({ name, size = 20 }) { return h('svg', { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }, h('path', { d: paths[name] || paths.book })); }
export function Button({ children, icon, variant = 'secondary', className = '', ...props }) { return h('button', { type: 'button', className: `button ${variant} ${className}`, ...props }, icon && h(Icon, { name: icon }), children); }
export function Brand({ compact = false }) { return h('div', { className: 'brand' }, h('span', { className: 'brand-mark' }, h(Icon, { name: 'book', size: 23 })), !compact && h('div', null, h('strong', null, 'IU Study'), h('span', null, 'ASSISTANT'))); }
export function Dialog({ title, children, onClose, className = '' }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    const first = ref.current.querySelector('[data-autofocus]') || ref.current.querySelector('input, textarea, select') || ref.current.querySelector('button'); first?.focus();
    return () => { ref.current?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return h('dialog', { ref, className: `dialog ${className}`, onCancel: event => { event.preventDefault(); onClose(); }, onClick: event => { if (event.target === ref.current) { const rect = ref.current.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose(); } }, 'aria-labelledby': titleId },
    h('div', { className: 'dialog-heading' }, h('h2', { id: titleId }, title), h(Button, { variant: 'ghost', icon: 'close', onClick: onClose, 'aria-label': 'Đóng hộp thoại' })), children);
}
export function Field({ label, name, error, children, hint }) { return h('div', { className: 'field' }, h('label', { htmlFor: name }, label), children, hint && h('small', { id: `${name}-hint` }, hint), error && h('p', { className: 'field-error', id: `${name}-error`, role: 'alert' }, error)); }
export function EmptyState({ title, detail, children }) { return h('div', { className: 'empty-state' }, h('span', { className: 'empty-icon' }, h(Icon, { name: 'search', size: 28 })), h('h2', null, title), h('p', null, detail), children); }
export function StatusBadge({ status }) { const index = ['Đã gửi', 'Đang xử lý', 'Cần bổ sung', 'Đã giải quyết', 'Đã đóng'].indexOf(status); return h('span', { className: `badge status-${index}` }, h('span', { 'aria-hidden': true }, ['↗', '◷', '!', '✓', '–'][index]), status); }
