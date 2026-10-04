import { useRef, useState } from 'react';
import { h, Brand, Button, Field, Icon } from '../components/ui.js';
import { validateLogin } from '../utils/validation.js';
import { authService } from '../services/mock.js';
import { useStore } from '../app/store.js';
import { navigate } from '../app/router.js';
export function Login({ returnTo }) {
  const { login } = useStore();
  const [values, setValues] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({}); const [failure, setFailure] = useState('');
  const [show, setShow] = useState(false); const [busy, setBusy] = useState(false);
  const form = useRef(null); const locked = useRef(false);
  async function submit(event, demo = false) {
    event?.preventDefault(); if (locked.current) return;
    const nextErrors = demo ? {} : validateLogin(values); setErrors(nextErrors); setFailure('');
    if (Object.keys(nextErrors).length) { form.current.elements[Object.keys(nextErrors)[0]].focus(); return; }
    locked.current = true; setBusy(true);
    try { login(await authService.login({ ...values, demo })); navigate(returnTo || '/chat', { replace: true, skipGuard: true }); }
    catch (error) { setFailure(error.message); }
    finally { locked.current = false; setBusy(false); }
  }
  return h('main', { className: 'login-page' },
    h('section', { className: 'login-story' }, h(Brand), h('div', { className: 'story-body' }, h('span', { className: 'eyebrow' }, 'MỘT NGƯỜI BẠN TRONG VIỆC HỌC'), h('h1', null, 'Học điều mới.', h('br'), h('span', null, 'Hiểu sâu hơn.')), h('p', null, 'Một không gian để đặt câu hỏi, khám phá kiến thức và tìm lời giải — theo nhịp của bạn.'), h('div', { className: 'study-illustration', 'aria-hidden': true }, h('div', { className: 'illustration-orbit' }), h('div', { className: 'illustration-book' }, h(Icon, { name: 'book', size: 84 })), h('span', { className: 'floating-note note-one' }, h(Icon, { name: 'spark' }), 'Hiểu từng bước'), h('span', { className: 'floating-note note-two' }, h(Icon, { name: 'check' }), 'Có nguồn tham khảo'))), h('p', { className: 'story-footer' }, 'Dành cho sinh viên IU · Bản trải nghiệm giao diện')),
    h('section', { className: 'login-form-side' }, h('div', { className: 'login-form-wrap' }, h('span', { className: 'badge neutral' }, 'Bản demo'), h('h2', null, 'Chào mừng bạn trở lại'), h('p', { className: 'muted' }, 'Bắt đầu một buổi học hiệu quả cùng IU Study.'),
      h('form', { ref: form, onSubmit: submit, noValidate: true },
        h(Field, { label: 'Email demo', name: 'email', error: errors.email }, h('input', { id: 'email', name: 'email', type: 'email', autoComplete: 'off', placeholder: 'ban@example.com', value: values.email, disabled: busy, 'aria-invalid': !!errors.email, 'aria-describedby': errors.email ? 'email-error' : undefined, onChange: e => setValues({ ...values, email: e.target.value }) })),
        h(Field, { label: 'Mật khẩu demo', name: 'password', error: errors.password, hint: 'Dùng mật khẩu demo123. Không nhập tài khoản thật.' }, h('div', { className: 'password-wrap' }, h('input', { id: 'password', name: 'password', type: show ? 'text' : 'password', autoComplete: 'off', placeholder: 'Nhập demo123', disabled: busy, value: values.password, 'aria-invalid': !!errors.password, 'aria-describedby': `password-hint${errors.password ? ' password-error' : ''}`, onChange: e => setValues({ ...values, password: e.target.value }) }), h(Button, { variant: 'ghost', icon: 'eye', onClick: () => setShow(!show), 'aria-label': show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu', 'aria-pressed': show, disabled: busy }))),
        failure && h('p', { className: 'alert error', role: 'alert' }, failure), h(Button, { type: 'submit', variant: 'primary', className: 'full', disabled: busy }, busy ? 'Đang đăng nhập…' : 'Đăng nhập', h(Icon, { name: 'chevron', size: 18 }))),
      h('div', { className: 'divider-text' }, 'hoặc khám phá ngay'), h(Button, { className: 'full', onClick: () => submit(null, true), disabled: busy, icon: 'spark' }, 'Dùng thử bản demo'), h('p', { className: 'login-notice' }, h(Icon, { name: 'help', size: 16 }), 'Dữ liệu chỉ lưu trên trình duyệt của bạn. Chưa kết nối hệ thống IU.'))));
}
