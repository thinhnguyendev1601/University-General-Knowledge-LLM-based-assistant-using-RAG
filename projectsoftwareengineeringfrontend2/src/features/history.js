import { useState } from 'react';
import { h, Button, Dialog, Icon } from '../components/ui.js';
import { useStore } from '../app/store.js';
import { historyGroup, validTitle } from '../utils/validation.js';
import { navigate } from '../app/router.js';
export function History({ activeId, onNavigate }) {
  const { state, dispatch, notify } = useStore();
  const [search, setSearch] = useState(''); const [menu, setMenu] = useState(null);
  const [editing, setEditing] = useState(null); const [title, setTitle] = useState(''); const [error, setError] = useState(''); const [deleting, setDeleting] = useState(null);
  const filtered = [...state.conversations].filter(c => c.title.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))).sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
  function rename(event) { event.preventDefault(); if (!validTitle(title)) { setError('Tên hội thoại cần từ 1 đến 80 ký tự.'); return; } dispatch({ type: 'conversation-update', id: editing.id, patch: { title: title.trim() } }); setEditing(null); notify('Đã đổi tên hội thoại.'); }
  function remove() {
    if (deleting.id === activeId && !navigate('/chat')) return;
    dispatch({ type: 'conversation-remove', id: deleting.id }); setDeleting(null); notify('Đã xóa hội thoại.');
  }
  return h('div', { className: 'history' }, h('div', { className: 'search-input sidebar-search' }, h(Icon, { name: 'search', size: 17 }), h('input', { value: search, onChange: e => setSearch(e.target.value), 'aria-label': 'Tìm tiêu đề hội thoại', placeholder: 'Tìm hội thoại…' })),
    h('div', { className: 'history-scroll' }, ['Hôm nay', '7 ngày gần đây', 'Cũ hơn'].map(group => { const items = filtered.filter(c => historyGroup(c.updatedAt) === group); return items.length > 0 && h('section', { key: group }, h('h2', { className: 'history-label' }, group), items.map(conversation => h('div', { className: `history-row ${activeId === conversation.id ? 'selected' : ''}`, key: conversation.id },
      h('button', { className: 'history-link', 'aria-current': activeId === conversation.id ? 'page' : undefined, title: conversation.title, onClick: () => { if (navigate(`/chat/${conversation.id}`)) onNavigate?.(); } }, h(Icon, { name: 'chat', size: 16 }), h('span', null, conversation.title)),
      h('details', { className: 'history-menu', open: menu === conversation.id, onToggle: event => { if (!event.currentTarget.open && menu === conversation.id) setMenu(null); }, onKeyDown: event => { if (event.key === 'Escape') { setMenu(null); event.currentTarget.querySelector('summary').focus(); } } }, h('summary', { 'aria-label': `Thao tác với ${conversation.title}`, onClick: event => { event.preventDefault(); setMenu(menu === conversation.id ? null : conversation.id); } }, h(Icon, { name: 'more', size: 17 })), h('div', { className: 'history-dropdown' }, h('button', { onClick: event => { event.currentTarget.closest('details').querySelector('summary').focus(); setTitle(conversation.title); setError(''); setEditing(conversation); setMenu(null); } }, 'Đổi tên'), h('button', { className: 'danger-text', onClick: event => { event.currentTarget.closest('details').querySelector('summary').focus(); setDeleting(conversation); setMenu(null); } }, 'Xóa hội thoại')))))); }),
      !filtered.length && h('div', { className: 'sidebar-empty' }, h('p', null, search ? 'Không tìm thấy tiêu đề phù hợp.' : 'Chưa có hội thoại nào.'), search && h(Button, { variant: 'ghost', onClick: () => setSearch('') }, 'Xóa bộ lọc'))),
    editing && h(Dialog, { title: 'Đổi tên hội thoại', onClose: () => setEditing(null) }, h('form', { onSubmit: rename }, h('label', { htmlFor: 'rename' }, 'Tên hội thoại'), h('input', { id: 'rename', value: title, maxLength: 80, 'aria-invalid': !!error, 'aria-describedby': error ? 'rename-error' : undefined, onChange: e => setTitle(e.target.value), 'data-autofocus': true }), error && h('p', { className: 'field-error', id: 'rename-error', role: 'alert' }, error), h('div', { className: 'form-actions' }, h(Button, { onClick: () => setEditing(null) }, 'Hủy'), h(Button, { type: 'submit', variant: 'primary' }, 'Lưu tên')))),
    deleting && h(Dialog, { title: 'Xóa hội thoại này?', onClose: () => setDeleting(null) }, h('p', null, `“${deleting.title}” sẽ bị xóa khỏi lịch sử trên thiết bị. Trích đoạn trong ticket vẫn được giữ.`), h('div', { className: 'form-actions' }, h(Button, { onClick: () => setDeleting(null), 'data-autofocus': true }, 'Giữ lại'), h(Button, { variant: 'danger', onClick: remove }, 'Xóa hội thoại'))));
}

