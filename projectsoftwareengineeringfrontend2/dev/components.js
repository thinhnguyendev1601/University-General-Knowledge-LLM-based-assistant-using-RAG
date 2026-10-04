import { createRoot } from 'react-dom/client';
import { useState } from 'react';
import { h, Button, Dialog, Field, StatusBadge } from '../src/components/ui.js';
import { statuses } from '../src/mocks/fixtures.js';
function Preview() {
  const [open, setOpen] = useState(false);
  return h('main', { className: 'content-page' }, h('h1', null, 'Component preview'), h('p', null, 'Trang nội bộ để kiểm tra token, hover, focus, lỗi và disabled bằng bàn phím.'),
    h('section', { className: 'panel' }, h('h2', null, 'Button'), h('div', { className: 'message-actions' }, ...['primary', 'secondary', 'ghost', 'danger'].map(variant => h(Button, { key: variant, variant, onClick: () => setOpen(true) }, variant)), h(Button, { disabled: true }, 'Disabled'), h(Button, { variant: 'primary', disabled: true }, 'Đang lưu…'))),
    h('section', { className: 'panel' }, h('h2', null, 'Trường nhập'), h(Field, { label: 'Tên', name: 'preview-name' }, h('input', { id: 'preview-name', placeholder: 'Nhập nội dung' })), h(Field, { label: 'Trường lỗi', name: 'preview-error', error: 'Ví dụ thông báo lỗi sát trường.' }, h('input', { id: 'preview-error', 'aria-invalid': true, 'aria-describedby': 'preview-error-error' }))),
    h('section', { className: 'panel' }, h('h2', null, 'Trạng thái ticket'), statuses.map(status => h(StatusBadge, { key: status, status }))),
    open && h(Dialog, { title: 'Kiểm tra focus', onClose: () => setOpen(false) }, h('p', null, 'Tab di chuyển trong dialog; Escape đóng và trả focus về nút đã mở.'), h(Button, { onClick: () => setOpen(false), 'data-autofocus': true }, 'Đóng')));
}
createRoot(document.getElementById('root')).render(h(Preview));
