import { useEffect, useState } from 'react';
let guard = null;
let historyIndex = 0;
export function setNavigationGuard(callback) { guard = callback; }
export function navigate(path, { replace = false, skipGuard = false } = {}) {
  if (!skipGuard && guard && !guard()) return false;
  if (!replace) historyIndex += 1;
  window.history[replace ? 'replaceState' : 'pushState']({ iuIndex: historyIndex }, '', path);
  window.dispatchEvent(new Event('iu:navigate'));
  return true;
}
export function parseRoute(pathname) {
  if (pathname === '/' || pathname === '/chat') return { name: 'chat', id: null };
  if (pathname === '/login') return { name: 'login' };
  if (pathname === '/tickets') return { name: 'tickets' };
  if (pathname === '/tickets/new') return { name: 'ticket-new' };
  try {
    const chat = pathname.match(/^\/chat\/([^/]+)$/);
    if (chat) return { name: 'chat', id: decodeURIComponent(chat[1]) };
    const ticket = pathname.match(/^\/tickets\/([^/]+)$/);
    if (ticket) return { name: 'ticket-detail', id: decodeURIComponent(ticket[1]) };
  } catch { return { name: 'not-found' }; }
  return { name: 'not-found' };
}
export function useRoute() {
  const [path, setPath] = useState(location.pathname);
  useEffect(() => {
    historyIndex = Number.isInteger(history.state?.iuIndex) ? history.state.iuIndex : 0;
    history.replaceState({ ...history.state, iuIndex: historyIndex }, '', location.href);
    let lastPath = location.pathname + location.search;
    let restoring = false;
    const internal = () => { lastPath = location.pathname + location.search; setPath(location.pathname); };
    const pop = () => {
      if (restoring) { restoring = false; return; }
      const nextIndex = history.state?.iuIndex;
      if (guard && !guard()) {
        if (Number.isInteger(nextIndex) && nextIndex !== historyIndex) { restoring = true; history.go(historyIndex - nextIndex); }
        else history.replaceState({ iuIndex: historyIndex }, '', lastPath);
        return;
      }
      if (Number.isInteger(nextIndex)) historyIndex = nextIndex;
      internal();
    };
    window.addEventListener('popstate', pop); window.addEventListener('iu:navigate', internal);
    return () => { window.removeEventListener('popstate', pop); window.removeEventListener('iu:navigate', internal); };
  }, []);
  return parseRoute(path);
}
