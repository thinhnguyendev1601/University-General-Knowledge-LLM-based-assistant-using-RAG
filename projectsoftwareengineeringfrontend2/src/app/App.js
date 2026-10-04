import { useEffect, useRef, useState } from 'react';
import { h, Brand, Button, Dialog, EmptyState, Icon } from '../components/ui.js';
import { useStore } from './store.js';
import { navigate, useRoute } from './router.js';
import { Login } from '../features/auth.js';
import { Chat } from '../features/chat.js';
import { History } from '../features/history.js';
import { TicketDetail, TicketForm, TicketList } from '../features/tickets.js';
function Account({ onClose }) {
  const { state, dispatch, logout, notify } = useStore(); const [reset, setReset] = useState(false);
  return h(Dialog, { title: 'Tài khoản demo', onClose }, h('div', { className: 'account-detail' }, h('span', { className: 'profile-avatar' }, state.user.displayName.slice(0, 1).toUpperCase()), h('strong', null, state.user.email)), h('p', { className: 'muted' }, 'Dữ liệu được lưu riêng theo email trên trình duyệt này. Đăng xuất giữ lại lịch sử và ticket để bạn có thể đăng nhập lại. Mật khẩu không được lưu.'), reset ? h('div', { className: 'alert' }, h('p', null, 'Đặt lại toàn bộ lịch sử và ticket của tài khoản này về dữ liệu mẫu?'), h('div', { className: 'form-actions' }, h(Button, { onClick: () => setReset(false) }, 'Hủy'), h(Button, { variant: 'danger', onClick: () => { if (!navigate('/chat')) return; dispatch({ type: 'reset' }); setReset(false); onClose(); notify('Đã đặt lại dữ liệu demo.'); } }, 'Đặt lại'))) : h(Button, { onClick: () => setReset(true) }, 'Đặt lại dữ liệu demo'), h('div', { className: 'form-actions' }, h(Button, { icon: 'logout', onClick: () => { if (navigate('/login')) { onClose(); logout(); } } }, 'Đăng xuất')));
}
function Sidebar({ route, onNavigate }) {
  const { state } = useStore();
  return h('div', { className: 'sidebar-inner' }, h(Brand), h(Button, { icon: 'plus', className: 'new-chat', onClick: () => { if (navigate('/chat')) onNavigate?.(); } }, 'Cuộc trò chuyện mới'), h(History, { activeId: route.name === 'chat' ? route.id : null, onNavigate }), h('div', { className: 'sidebar-bottom' }, h(Button, { variant: 'ghost', icon: 'ticket', className: `ticket-nav ${route.name.startsWith('ticket') ? 'nav-selected' : ''}`, onClick: () => { if (navigate('/tickets')) onNavigate?.(); } }, 'Ticket của tôi', h('span', { className: 'count-pill' }, state.tickets.length)), h('div', { className: 'sidebar-tip' }, h('span', null, h(Icon, { name: 'spark', size: 18 }), 'Học từng chút, tiến xa hơn'), h('p', null, 'Đừng ngại hỏi. Mỗi câu hỏi đều là một khởi đầu.'))));
}
export function App() {
  const { state } = useStore(); const route = useRoute();
  const [drawer, setDrawer] = useState(false); const [collapsed, setCollapsed] = useState(false); const [account, setAccount] = useState(false);
  const returnTo = useRef(null);
  useEffect(() => {
    if (!state.user && route.name !== 'login') { returnTo.current = location.pathname === '/' ? '/chat' : location.pathname + location.search; navigate('/login', { replace: true, skipGuard: true }); }
    else if (state.user && route.name === 'login') navigate('/chat', { replace: true, skipGuard: true });
  }, [state.user, route.name]);
  if (!state.user) return h(Login, { returnTo: returnTo.current });
  const conversation = state.conversations.find(c => c.id === route.id);
  const title = route.name === 'chat' ? conversation?.title || 'Không gian học tập' : route.name.startsWith('ticket') ? 'Trung tâm hỗ trợ' : 'IU Study Assistant';
  let page;
  if (route.name === 'chat' || route.name === 'login') page = h(Chat, { id: route.name === 'chat' ? route.id : null });
  else if (route.name === 'tickets') page = h(TicketList);
  else if (route.name === 'ticket-new') page = h(TicketForm);
  else if (route.name === 'ticket-detail') page = h(TicketDetail, { id: route.id });
  else page = h(EmptyState, { title: 'Trang này không tồn tại', detail: 'Bạn có thể quay về không gian học tập để tiếp tục.' }, h(Button, { variant: 'primary', onClick: () => navigate('/chat') }, 'Về chat'));
  return h('div', { className: `app-shell ${collapsed ? 'sidebar-collapsed' : ''}` }, h('a', { className: 'skip-link', href: '#main-content' }, 'Bỏ qua đến nội dung chính'),
    h('aside', { className: 'desktop-sidebar', 'aria-label': 'Điều hướng và lịch sử' }, h(Sidebar, { route })),
    h('div', { className: 'workspace' }, h('header', { className: 'app-header' }, h('div', { className: 'header-left' }, h(Button, { className: 'mobile-menu', variant: 'ghost', icon: 'menu', 'aria-label': 'Mở điều hướng', onClick: () => setDrawer(true) }), h(Button, { className: 'desktop-toggle', variant: 'ghost', icon: 'menu', 'aria-label': collapsed ? 'Mở sidebar' : 'Thu gọn sidebar', 'aria-expanded': !collapsed, onClick: () => setCollapsed(!collapsed) }), h('div', null, h('span', { className: 'header-title' }, title), h('span', { className: 'header-subtitle' }, 'IU Study Assistant'))), h('div', { className: 'header-right' }, h('span', { className: 'demo-pill' }, h('span', { className: 'online-dot' }), 'Bản demo'), h(Button, { variant: 'ghost', icon: 'help', 'aria-label': 'Tạo ticket hỗ trợ', onClick: () => navigate('/tickets/new') }), h('button', { className: 'profile-avatar', 'aria-label': 'Mở tài khoản demo', onClick: () => setAccount(true) }, state.user.displayName === 'Bạn' ? 'SV' : state.user.displayName.slice(0, 2).toUpperCase()))),
      state.warning && h('div', { className: 'storage-warning', role: 'alert' }, state.warning), h('main', { id: 'main-content', className: 'main-content', tabIndex: -1 }, page)),
    drawer && h(Dialog, { title: 'Điều hướng', className: 'mobile-drawer', onClose: () => setDrawer(false) }, h(Sidebar, { route, onNavigate: () => setDrawer(false) })), account && h(Account, { onClose: () => setAccount(false) }), state.toast && h('div', { className: 'toast', role: 'status' }, h(Icon, { name: 'check', size: 18 }), state.toast));
}
