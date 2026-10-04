import { useEffect, useRef, useState } from 'react';
import { h, Button, Dialog, EmptyState, Icon } from '../components/ui.js';
import { useStore } from '../app/store.js';
import { navigate } from '../app/router.js';
import { chatService, scenario } from '../services/mock.js';
import { prompts } from '../mocks/fixtures.js';
import { safeUrl } from '../utils/validation.js';
export const messageText = message => Array.isArray(message.content) ? message.content.map(block => {
  if (['paragraph', 'heading', 'code'].includes(block.type)) return block.text;
  if (block.type === 'list') return block.items.join('\n');
  return [block.headers, ...block.rows].map(row => row.join(' | ')).join('\n');
}).join('\n\n') : message.content;
function useChatReply(conversationId) {
  const { dispatch, current } = useStore();
  const job = useRef(null); const [busy, setBusy] = useState(false);
  function stop() {
    const active = job.current;
    if (!active) return;
    job.current = null; active.controller.abort(); setBusy(false);
    dispatch({ type: 'message-update', conversationId: active.conversationId, messageId: active.messageId, patch: { status: 'stopped' } });
  }
  useEffect(() => { if (job.current && job.current.conversationId !== conversationId) stop(); }, [conversationId]);
  useEffect(() => () => { const active = job.current; if (active) { active.controller.abort(); dispatch({ type: 'message-update', conversationId: active.conversationId, messageId: active.messageId, patch: { status: 'stopped' } }); } }, []);
  async function start(id, messageId, question, retry = false, mode = scenario()) {
    if (job.current) return;
    const active = { conversationId: id, messageId, controller: new AbortController() };
    job.current = active; setBusy(true);
    dispatch({ type: 'message-update', conversationId: id, messageId, patch: { content: [], citations: [], status: 'waiting', error: '' } });
    try {
      for await (const part of chatService.reply(question, { signal: active.controller.signal, forceSuccess: retry, mode })) {
        if (job.current !== active || active.controller.signal.aborted) return;
        // IDs bind each response to its original conversation, including after navigation.
        dispatch({ type: 'message-update', conversationId: id, messageId, patch: { content: part.blocks, citations: part.citations, status: part.complete ? 'complete' : 'streaming' } });
      }
    } catch (error) {
      if (error.name !== 'AbortError' && job.current === active) dispatch({ type: 'message-update', conversationId: id, messageId, patch: { status: 'error', error: error.message } });
    } finally { if (job.current === active) { job.current = null; setBusy(false); } }
  }
  function send(question) {
    if (job.current || !question.trim()) return;
    const mode = scenario();
    const time = new Date().toISOString();
    let conversation = current.current.conversations.find(c => c.id === conversationId);
    const user = { id: crypto.randomUUID(), role: 'user', content: question.trim(), createdAt: time, status: 'complete' };
    const assistant = { id: crypto.randomUUID(), role: 'assistant', content: [], citations: [], status: 'waiting', feedback: null, createdAt: time };
    if (!conversation) {
      conversation = { id: crypto.randomUUID(), title: question.trim().slice(0, 80), createdAt: time, updatedAt: time, messages: [user, assistant] };
      dispatch({ type: 'conversation-add', conversation });
      navigate(`/chat/${conversation.id}`);
    } else dispatch({ type: 'conversation-update', id: conversation.id, patch: { updatedAt: time, messages: [...conversation.messages, user, assistant] } });
    start(conversation.id, assistant.id, question, false, mode);
  }
  return { busy, send, stop, retry: (message, question) => start(conversationId, message.id, question, true) };
}
function Block({ block, citations, onSource }) {
  if (block.type === 'heading') return h('h3', null, block.text);
  if (block.type === 'list') return h('ol', null, block.items.map((item, index) => h('li', { key: index }, item)));
  if (block.type === 'table') return h('div', { className: 'table-scroll', tabIndex: 0, 'aria-label': 'Bảng ví dụ, cuộn ngang nếu cần' }, h('table', null, h('thead', null, h('tr', null, block.headers.map((item, index) => h('th', { key: index, scope: 'col' }, item)))), h('tbody', null, block.rows.map((row, index) => h('tr', { key: index }, row.map((item, cell) => h('td', { key: cell }, item)))))));
  if (block.type === 'code') return h('div', { className: 'code-block' }, h('span', null, 'JavaScript'), h('pre', { tabIndex: 0 }, h('code', null, block.text)));
  return h('p', null, block.text.split(/(\[\d+\])/g).map((text, index) => {
    const match = text.match(/^\[(\d+)\]$/); const source = match && citations[Number(match[1]) - 1];
    return source ? h('button', { key: index, className: 'inline-citation', onClick: () => onSource(source), 'aria-label': `Mở nguồn ${match[1]}: ${source.documentTitle}` }, text) : text;
  }));
}
export function SourcePanel({ source, onClose }) {
  const url = safeUrl(source.url);
  return h(Dialog, { title: 'Nguồn tham khảo', onClose, className: 'source-panel' }, h('span', { className: 'badge neutral' }, 'Tài liệu mẫu'), h('div', { className: 'source-cover' }, h(Icon, { name: 'book', size: 44 })), h('h3', null, source.documentTitle), h('p', { className: 'muted' }, [source.course, source.page && `Trang ${source.page}`, source.section].filter(Boolean).join(' · ')), h('blockquote', null, source.excerpt), url ? h('a', { className: 'button primary', href: url, target: '_blank', rel: 'noopener noreferrer' }, 'Xem tài liệu') : h('p', { className: 'small muted' }, 'Nguồn mẫu chỉ có đoạn trích; không có liên kết tài liệu gốc.'), h('p', { className: 'small muted' }, 'Không phải thông tin được IU xác nhận.'));
}
export function Chat({ id }) {
  const { state, dispatch, notify } = useStore();
  const conversation = state.conversations.find(c => c.id === id);
  const { busy, send, stop, retry } = useChatReply(id);
  const [draft, setDraft] = useState(''); const [source, setSource] = useState(null);
  const composer = useRef(null); const scroller = useRef(null); const nearBottom = useRef(true); const [showJump, setShowJump] = useState(false);
  useEffect(() => { setDraft(''); setSource(null); nearBottom.current = true; setShowJump(false); composer.current?.focus(); }, [id]);
  useEffect(() => {
    const resize = () => { const area = composer.current; if (area) { area.style.height = 'auto'; area.style.height = `${Math.min(area.scrollHeight + 2, 160)}px`; } };
    resize(); window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [draft]);
  useEffect(() => {
    if (!scroller.current) return;
    if (!conversation) { scroller.current.scrollTop = 0; return; }
    if (nearBottom.current) scroller.current.scrollTop = scroller.current.scrollHeight;
    else setShowJump(true);
  }, [conversation?.messages]);
  function submit(event) { event.preventDefault(); if (!draft.trim() || busy) return; send(draft); setDraft(''); }
  async function copy(message) { try { await navigator.clipboard.writeText(messageText(message)); notify('Đã sao chép câu trả lời.'); } catch { notify('Không thể sao chép. Hãy chọn nội dung và sao chép thủ công.'); } }
  function createTicket(message) {
    const selected = window.getSelection()?.toString().trim();
    const text = messageText(message);
    const excerpt = selected && text.includes(selected) ? selected.slice(0, 1500) : text.slice(0, 400);
    navigate(`/tickets/new?conversation=${encodeURIComponent(id)}&message=${encodeURIComponent(message.id)}&excerpt=${encodeURIComponent(excerpt)}`);
  }
  if (id && !conversation) return h(EmptyState, { title: 'Không tìm thấy hội thoại', detail: 'Hội thoại có thể đã bị xóa hoặc đường dẫn không hợp lệ.' }, h(Button, { variant: 'primary', onClick: () => navigate('/chat') }, 'Bắt đầu chat mới'));
  return h('section', { className: 'chat-page', 'aria-label': 'Không gian hội thoại' },
    h('div', { className: 'chat-scroll', ref: scroller, onScroll: () => { const area = scroller.current; nearBottom.current = area.scrollHeight - area.scrollTop - area.clientHeight < 100; if (nearBottom.current) setShowJump(false); } },
      !conversation ? h('div', { className: 'welcome' }, h('span', { className: 'welcome-mark' }, h(Icon, { name: 'spark', size: 32 })), h('div', { className: 'welcome-greeting' }, `Chào ${state.user.displayName === 'Bạn' ? 'bạn' : state.user.displayName} 👋`), h('h1', null, 'Hôm nay, bạn muốn', h('br'), 'tìm hiểu điều gì?'), h('p', null, 'Một câu hỏi nhỏ có thể mở ra một điều mới.', h('br'), 'Cùng học, hiểu và khám phá với IU Study Assistant.'), h('div', { className: 'prompt-grid' }, prompts.map(prompt => h('button', { key: prompt.title, className: `prompt-card ${prompt.tone}`, onClick: () => { setDraft(prompt.question); composer.current?.focus(); } }, h('span', { className: 'prompt-icon' }, h(Icon, { name: prompt.icon, size: 22 })), h('strong', null, prompt.title), h('span', null, prompt.detail), h(Icon, { name: 'chevron', size: 16 })))), h('span', { className: 'welcome-footnote' }, h(Icon, { name: 'book', size: 15 }), 'Kiến thức dễ hiểu hơn, từng câu hỏi một.')) :
      h('div', { className: 'message-list' }, conversation.messages.map((message, index) => h('article', { key: message.id, className: `message ${message.role}` },
        h('div', { className: 'message-meta' }, message.role === 'assistant' && h('span', { className: 'assistant-avatar' }, h(Icon, { name: 'book', size: 17 })), h('strong', null, message.role === 'user' ? 'Bạn' : 'IU Study Assistant'), message.role === 'assistant' && h('span', { className: 'muted small' }, 'Phản hồi mẫu')),
        message.role === 'user' ? h('div', { className: 'user-bubble' }, message.content) : h('div', { className: 'answer-body' },
          message.content.map((block, blockIndex) => h(Block, { key: blockIndex, block, citations: message.citations, onSource: setSource })),
          message.status === 'waiting' && h('div', { className: 'thinking' }, h('span', { className: 'thinking-dots', 'aria-hidden': true }, '•••'), 'Đang chuẩn bị câu trả lời…'),
          message.status === 'streaming' && h('span', { className: 'stream-cursor', 'aria-hidden': true }),
          ['complete', 'stopped', 'error'].includes(message.status) && h('div', { className: 'answer-footer' },
            message.status === 'stopped' && h('p', { className: 'muted small' }, 'Đã dừng · Bạn có thể thử lại câu trả lời.'),
            message.status === 'error' && h('p', { className: 'alert error', role: 'alert' }, message.error || 'Phản hồi bị gián đoạn.'),
            message.citations.length ? h('div', { className: 'sources' }, h('p', { className: 'source-label' }, 'NGUỒN THAM KHẢO · TÀI LIỆU MẪU'), message.citations.map((citation, citationIndex) => h('button', { key: citation.id, className: 'source-card', onClick: () => setSource(citation) }, h('span', { className: 'source-number' }, citationIndex + 1), h('div', null, h('strong', null, citation.documentTitle), h('span', null, `Tài liệu mẫu · Trang ${citation.page || '—'}`)), h(Icon, { name: 'chevron', size: 16 })))) : message.status === 'complete' && h('p', { className: 'small muted' }, 'Câu trả lời tổng quát, chưa có nguồn.'),
            h('div', { className: 'message-actions' }, h(Button, { icon: 'copy', variant: 'ghost', onClick: () => copy(message), 'aria-label': 'Sao chép câu trả lời' }),
              ...['helpful', 'unhelpful'].map((feedback, feedbackIndex) => h(Button, { key: feedback, variant: 'ghost', className: feedbackIndex ? 'thumb-down' : '', icon: 'thumb', 'aria-label': feedbackIndex ? 'Chưa hữu ích' : 'Hữu ích', 'aria-pressed': message.feedback === feedback, onClick: () => dispatch({ type: 'message-update', conversationId: id, messageId: message.id, patch: { feedback: message.feedback === feedback ? null : feedback } }) })),
              h(Button, { icon: 'ticket', variant: 'ghost', onClick: () => createTicket(message) }, 'Tạo ticket'),
              ['stopped', 'error'].includes(message.status) && h(Button, { disabled: busy, variant: 'ghost', onClick: () => retry(message, conversation.messages[index - 1]?.content || '') }, 'Thử lại')))))))),
    h('div', { className: 'composer-area' }, showJump && h(Button, { className: 'jump-button', onClick: () => { nearBottom.current = true; scroller.current.scrollTop = scroller.current.scrollHeight; setShowJump(false); } }, '↓ Xuống tin nhắn mới'),
      h('form', { className: 'composer', onSubmit: submit }, h('textarea', { ref: composer, value: draft, maxLength: 4000, rows: 1, 'aria-label': 'Câu hỏi của bạn', placeholder: 'Hỏi bất cứ điều gì về việc học…', onChange: event => setDraft(event.target.value), onKeyDown: event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !event.isComposing && window.matchMedia('(min-width: 768px)').matches) { event.preventDefault(); submit(event); } } }), h('div', { className: 'composer-bottom' }, h('span', null, h('span', { className: 'online-dot' }), 'Trợ lý học tập', h('span', { className: 'composer-demo' }, 'Demo')), busy ? h(Button, { className: 'send-button', variant: 'primary', onClick: stop, 'aria-label': 'Dừng trả lời' }, '■') : h(Button, { type: 'submit', className: 'send-button', icon: 'arrow', variant: 'primary', disabled: !draft.trim(), 'aria-label': 'Gửi câu hỏi' }))),
      h('p', { className: 'composer-disclaimer' }, 'Phản hồi và nguồn là dữ liệu mẫu. Hãy kiểm chứng thông tin quan trọng.')),
    h('div', { className: 'sr-only', role: 'status', 'aria-live': 'polite' }, busy ? 'Trợ lý đang trả lời.' : 'Sẵn sàng.'), source && h(SourcePanel, { source, onClose: () => setSource(null) }));
}

