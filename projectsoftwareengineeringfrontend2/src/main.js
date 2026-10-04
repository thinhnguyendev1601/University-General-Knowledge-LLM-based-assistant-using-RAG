import React, { createElement as h } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App.js';
import { StoreProvider } from './app/store.js';
class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? h('main', { className: 'empty-state' }, h('h1', null, 'Có lỗi khi mở giao diện'), h('p', null, 'Hãy tải lại trang. Nếu lỗi tiếp diễn, mở bản demo trong một phiên trình duyệt mới.'), h('button', { onClick: () => location.reload() }, 'Tải lại')) : this.props.children; }
}
createRoot(document.getElementById('root')).render(h(ErrorBoundary, null, h(StoreProvider, null, h(App))));
