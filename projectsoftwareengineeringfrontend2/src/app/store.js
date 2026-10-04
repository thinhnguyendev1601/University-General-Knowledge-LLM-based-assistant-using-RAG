import { createContext, useContext, useEffect, useReducer, useRef } from 'react';
import { createElement as h } from 'react';
import { readData, readSession, sessionKey, writeData } from '../utils/persistence.js';
import { createFixtures } from '../mocks/fixtures.js';
const Store = createContext(null);
function storage() { try { return localStorage; } catch { return { getItem() { throw new Error(); }, setItem() { throw new Error(); }, removeItem() {} }; } }
function initialState() {
  const user = readSession(storage());
  const restored = user ? readData(storage(), user.id) : { data: { conversations: [], tickets: [] }, warning: '' };
  return { user, ...restored.data, warning: restored.warning, toast: '' };
}
export function reducer(state, action) {
  switch (action.type) {
    case 'login': return { ...state, user: action.user, ...action.data, warning: action.warning };
    case 'logout': return { ...state, user: null, conversations: [], tickets: [], warning: '' };
    case 'conversation-add': return { ...state, conversations: [action.conversation, ...state.conversations] };
    case 'conversation-update': return { ...state, conversations: state.conversations.map(c => c.id === action.id ? { ...c, ...action.patch } : c) };
    case 'message-update': return { ...state, conversations: state.conversations.map(c => c.id === action.conversationId ? { ...c, updatedAt: new Date().toISOString(), messages: c.messages.map(m => m.id === action.messageId ? { ...m, ...action.patch } : m) } : c) };
    case 'conversation-remove': return { ...state, conversations: state.conversations.filter(c => c.id !== action.id) };
    case 'ticket-add': return { ...state, tickets: [action.ticket, ...state.tickets] };
    case 'reset': return { ...state, ...createFixtures(), warning: '' };
    case 'warning': return { ...state, warning: action.value };
    case 'toast': return { ...state, toast: action.value };
    default: return state;
  }
}
export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const current = useRef(state); current.current = state;
  useEffect(() => {
    if (!state.user) return;
    const message = writeData(storage(), state.user.id, { conversations: state.conversations, tickets: state.tickets });
    if (message) dispatch({ type: 'warning', value: message });
  }, [state.user, state.conversations, state.tickets]);
  useEffect(() => { if (!state.toast) return; const timer = setTimeout(() => dispatch({ type: 'toast', value: '' }), 3500); return () => clearTimeout(timer); }, [state.toast]);
  function login(user) {
    const restored = readData(storage(), user.id);
    try { storage().setItem(sessionKey, JSON.stringify(user)); } catch { restored.warning = 'Phiên demo không thể lưu. Bạn sẽ cần đăng nhập lại khi tải lại trang.'; }
    dispatch({ type: 'login', user, ...restored });
  }
  function logout() { try { storage().removeItem(sessionKey); } catch { /* In-memory session still ends. */ } dispatch({ type: 'logout' }); }
  return h(Store.Provider, { value: { state, dispatch, current, login, logout, notify: value => dispatch({ type: 'toast', value }) } }, children);
}
export const useStore = () => useContext(Store);
