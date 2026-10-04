import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateLogin, validateTicket, validTitle, historyGroup, safeUrl } from '../src/utils/validation.js';
import { readSession, readData, writeData, validData, sessionKey } from '../src/utils/persistence.js';
import { createFixtures, responseFor, statuses } from '../src/mocks/fixtures.js';
import { authService, chatService, ticketService, delay } from '../src/services/mock.js';

const tests = [];
const test = (name, run) => tests.push({ name, run });
const dataKey = userId => `iu-study:v1:${userId}`;
// React is supplied by the browser import map. Load only pure exports in Node;
// hook and provider behavior is covered by the browser checklist.
async function loadPureExports(path, { stripAllImports = false } = {}) {
  const url = new URL(path, import.meta.url);
  const source = (await readFile(url, 'utf8'))
    .replace(stripAllImports ? /^import .*;\r?\n/gm : /$^/g, '')
    .replace(/^import .* from 'react';\r?\n/gm, '')
    .replace(/^const Store = createContext\(null\);\r?\n/gm, '')
    .replace(/from '(\.[^']+)'/g, (_, relative) => `from '${new URL(relative, url).href}'`);
  return import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
}
function memoryStorage() {
  const values = new Map();
  return {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key)
  };
}

test('login validates blank fields, invalid email and trimmed email', () => {
  assert.ok(validateLogin({ email: 'invalid', password: ' ' }).email);
  assert.ok(validateLogin({ email: 'invalid', password: ' ' }).password);
  assert.deepEqual(validateLogin({ email: ' student@example.edu ', password: 'demo123' }), {});
});

test('ticket validates categories and both length boundaries after trim', () => {
  const fields = { title: '12345', category: 'Khác', description: 'x'.repeat(20) };
  assert.deepEqual(validateTicket(fields), {});
  assert.deepEqual(validateTicket({ ...fields, title: ' x '.repeat(121), description: 'x'.repeat(3001), category: 'unknown' }), {
    title: 'Tiêu đề cần từ 5 đến 120 ký tự.', category: 'Chọn một danh mục hỗ trợ.', description: 'Mô tả cần từ 20 đến 3.000 ký tự.'
  });
  assert.ok(validateTicket({ ...fields, title: ' 1234 ', description: ' '.repeat(20) }).title);
  assert.ok(validateTicket({ ...fields, description: ' '.repeat(20) }).description);
  assert.deepEqual(validateTicket({ ...fields, title: 'x'.repeat(120), description: 'x'.repeat(3000) }), {});
  assert.equal(validTitle(' '), false);
  assert.equal(validTitle(' Tên mới '), true);
  assert.equal(validTitle('x'.repeat(81)), false);
});

test('history grouping uses local day boundaries', () => {
  const now = new Date(2026, 9, 4, 12);
  assert.equal(historyGroup(new Date(2026, 9, 4, 0).toISOString(), now), 'Hôm nay');
  assert.equal(historyGroup(new Date(2026, 9, 3, 23, 59).toISOString(), now), '7 ngày gần đây');
  assert.equal(historyGroup(new Date(2026, 8, 27, 0).toISOString(), now), '7 ngày gần đây');
  assert.equal(historyGroup(new Date(2026, 8, 26, 23, 59).toISOString(), now), 'Cũ hơn');
});

test('source URLs reject executable schemes and accept HTTPS', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,test', 'file:///C:/test', '/relative', 'invalid']) assert.equal(safeUrl(value), null);
  assert.equal(safeUrl('https://example.edu/document'), 'https://example.edu/document');
});

test('message copying handles empty text blocks, lists and tables without crashing', async () => {
  const { messageText } = await loadPureExports('../src/features/chat.js', { stripAllImports: true });
  for (const type of ['paragraph', 'heading', 'code']) assert.equal(messageText({ content: [{ type, text: '' }] }), '');
  assert.equal(messageText({ content: [] }), '');
  assert.equal(messageText({ content: 'Câu hỏi tiếng Việt' }), 'Câu hỏi tiếng Việt');
  assert.equal(messageText({ content: [{ type: 'list', items: ['A', 'B'] }] }), 'A\nB');
  assert.equal(messageText({ content: [{ type: 'table', headers: ['A', 'B'], rows: [['1', '2']] }] }), 'A | B\n1 | 2');
});

test('route parsing handles form precedence, encoded IDs, malformed IDs and unknown paths', async () => {
  const { parseRoute } = await loadPureExports('../src/app/router.js');
  assert.deepEqual(parseRoute('/'), { name: 'chat', id: null });
  assert.deepEqual(parseRoute('/chat'), { name: 'chat', id: null });
  assert.deepEqual(parseRoute('/login'), { name: 'login' });
  assert.deepEqual(parseRoute('/tickets'), { name: 'tickets' });
  assert.deepEqual(parseRoute('/tickets/new'), { name: 'ticket-new' });
  assert.deepEqual(parseRoute('/chat/Ti%E1%BA%BFng%20Vi%E1%BB%87t'), { name: 'chat', id: 'Tiếng Việt' });
  assert.deepEqual(parseRoute('/tickets/IU-1006'), { name: 'ticket-detail', id: 'IU-1006' });
  for (const path of ['/chat/%', '/chat/a/extra', '/unknown', '/tickets/a/extra']) assert.deepEqual(parseRoute(path), { name: 'not-found' });
});

test('navigation guard cancels mutations and replacement respects guard bypass', async () => {
  const { navigate, setNavigationGuard } = await loadPureExports('../src/app/router.js');
  const calls = [];
  globalThis.window = {
    history: { pushState: (...args) => calls.push(['push', ...args]), replaceState: (...args) => calls.push(['replace', ...args]) },
    dispatchEvent: event => calls.push(['event', event.type])
  };
  setNavigationGuard(() => false);
  assert.equal(navigate('/chat'), false);
  assert.deepEqual(calls, []);
  assert.equal(navigate('/login', { replace: true, skipGuard: true }), true);
  assert.equal(calls[0][0], 'replace');
  assert.equal(calls[0][3], '/login');
  assert.equal(calls[1][1], 'iu:navigate');
  setNavigationGuard(null);
  delete globalThis.window;
});

test('reducer keeps stream updates in the specified conversation and preserves ticket excerpts', async () => {
  const { reducer } = await loadPureExports('../src/app/store.js');
  const fixture = createFixtures();
  const state = { ...fixture, user: { id: 'a' }, warning: '', toast: '' };
  const updated = reducer(state, { type: 'message-update', conversationId: fixture.conversations[0].id, messageId: fixture.conversations[0].messages[1].id, patch: { status: 'stopped' } });
  assert.equal(updated.conversations[0].messages[1].status, 'stopped');
  assert.equal(state.conversations[0].messages[1].status, 'complete');
  assert.equal(updated.conversations[1], state.conversations[1]);
  const removed = reducer(updated, { type: 'conversation-remove', id: fixture.conversations[0].id });
  assert.equal(removed.conversations.some(item => item.id === fixture.conversations[0].id), false);
  assert.equal(removed.tickets[0].selectedExcerpt, state.tickets[0].selectedExcerpt);
  const loggedOut = reducer(removed, { type: 'logout' });
  assert.equal(loggedOut.user, null);
  assert.deepEqual(loggedOut.conversations, []);
  assert.deepEqual(loggedOut.tickets, []);
  const loggedIn = reducer(loggedOut, { type: 'login', user: { id: 'b' }, data: { conversations: [], tickets: [] }, warning: '' });
  assert.deepEqual(loggedIn.conversations, []);
});

test('fixtures cover every status and pass the persistence schema', () => {
  const data = createFixtures();
  assert.equal(data.conversations.length, 8);
  assert.equal(data.tickets.length, 6);
  assert.equal(validData({ version: 1, ...data }), true);
  assert.deepEqual([...new Set(data.tickets.map(ticket => ticket.status))].sort(), [...statuses].sort());
  assert.equal(new Set(data.conversations.map(item => item.id)).size, data.conversations.length);
  assert.ok(responseFor('đạo hàm').citations.length);
  assert.equal(responseFor('JavaScript code').blocks[1].type, 'code');
});

test('corrupt JSON, incompatible schema and malformed nested values recover with warning', () => {
  const storage = memoryStorage();
  const fixture = { version: 1, ...createFixtures() };
  const badBlock = structuredClone(fixture);
  badBlock.conversations[0].messages[1].content = [{ type: 'table', headers: ['A'], rows: [null] }];
  const badDate = structuredClone(fixture);
  badDate.tickets[0].createdAt = 'not a date';
  for (const value of ['{', 'null', JSON.stringify({ ...fixture, version: 2 }), JSON.stringify(badBlock), JSON.stringify(badDate)]) {
    storage.setItem(dataKey('user'), value);
    const result = readData(storage, 'user');
    assert.ok(result.warning);
    assert.equal(validData({ version: 1, ...result.data }), true);
  }
  assert.equal(readData(memoryStorage(), 'new-user').warning, '');
});

test('storage denial and full quota return explicit warnings', () => {
  const storage = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('quota'); } };
  assert.equal(readSession(storage), null);
  assert.ok(readData(storage, 'user').warning);
  assert.ok(writeData(storage, 'user', createFixtures()));
});

test('persisted message error objects are rejected before React renders them', () => {
  const data = { version: 1, ...createFixtures() };
  data.conversations[0].messages[1].status = 'error';
  data.conversations[0].messages[1].error = { message: 'Corrupt data' };
  assert.equal(validData(data), false);
});

test('persisted ticket course objects are rejected before React renders them', () => {
  const data = { version: 1, ...createFixtures() };
  data.tickets[0].course = { name: 'Corrupt course' };
  assert.equal(validData(data), false);
});

test('persisted streams become stopped and data remains isolated by user', () => {
  const storage = memoryStorage();
  const data = createFixtures();
  data.conversations[0].title = 'Hội thoại riêng của A';
  data.conversations[0].messages[1].status = 'streaming';
  data.conversations[1].messages[1].status = 'waiting';
  assert.equal(writeData(storage, 'a@example.edu', data), '');
  const loaded = readData(storage, 'a@example.edu').data;
  assert.equal(loaded.conversations[0].messages[1].status, 'stopped');
  assert.equal(loaded.conversations[1].messages[1].status, 'stopped');
  assert.notEqual(readData(storage, 'b@example.edu').data.conversations[0].title, data.conversations[0].title);
  assert.equal(data.conversations[0].messages[1].status, 'streaming');
});

test('session rejects malformed JSON and missing required fields', () => {
  const storage = memoryStorage();
  for (const value of ['{', 'null', '{}', '{"id":1,"email":"a","displayName":"A"}']) {
    storage.setItem(sessionKey, value);
    assert.equal(readSession(storage), null);
  }
  const session = { id: 'a@example.edu', email: 'a@example.edu', displayName: 'A' };
  storage.setItem(sessionKey, JSON.stringify(session));
  assert.deepEqual(readSession(storage), session);
});

test('demo login normalizes identity and never returns a password', async () => {
  globalThis.location = { search: '' };
  const session = await authService.login({ email: ' A@Example.edu ', password: 'demo123' });
  assert.equal(session.id, 'a@example.edu');
  assert.equal(Object.hasOwn(session, 'password'), false);
  await assert.rejects(authService.login({ email: 'a@example.edu', password: 'wrong' }));
});

test('login failure scenarios reject valid credentials while the demo shortcut remains available', async () => {
  try {
    for (const scenario of ['login-error', 'login-network']) {
      globalThis.location = { search: `?scenario=${scenario}` };
      await assert.rejects(authService.login({ email: 'a@example.edu', password: 'demo123' }));
      const session = await authService.login({ demo: true });
      assert.deepEqual(session, { id: 'student@demo.local', email: 'student@demo.local', displayName: 'Bạn' });
      assert.equal(Object.hasOwn(session, 'password'), false);
    }
  } finally { globalThis.location = { search: '' }; }
});

test('optional malformed citation metadata is rejected by persisted data validation', () => {
  for (const [field, value] of [['course', {}], ['section', []], ['url', {}], ['page', 'twenty']]) {
    const data = { version: 1, ...createFixtures() };
    data.conversations[0].messages[1].citations[0] = { ...data.conversations[0].messages[1].citations[0], [field]: value };
    assert.equal(validData(data), false);
  }
});

test('abort stops waits before start and during an active timer', async () => {
  const before = new AbortController();
  before.abort();
  await assert.rejects(delay(100, before.signal), { name: 'AbortError' });
  const during = new AbortController();
  const waiting = delay(1000, during.signal);
  during.abort();
  await assert.rejects(waiting, { name: 'AbortError' });
});

test('stream abort prevents further chunks after a partial response', async () => {
  const controller = new AbortController();
  const reply = chatService.reply('JavaScript code', { signal: controller.signal });
  const first = await reply.next();
  assert.equal(first.done, false);
  assert.equal(first.value.complete, undefined);
  controller.abort();
  await assert.rejects(reply.next(), { name: 'AbortError' });
});

test('stream abort at the final partial chunk prevents complete delivery', async () => {
  const controller = new AbortController();
  const question = 'JavaScript code';
  const expected = responseFor(question).blocks;
  const reply = chatService.reply(question, { signal: controller.signal });
  for (;;) {
    const chunk = await reply.next();
    assert.equal(chunk.done, false);
    if (!chunk.value.complete && JSON.stringify(chunk.value.blocks) === JSON.stringify(expected)) break;
  }
  controller.abort();
  await assert.rejects(reply.next(), { name: 'AbortError' });
});

test('failure scenario errors after partial response and retry completes', async () => {
  globalThis.location = { search: '?scenario=chat-error' };
  const received = [];
  await assert.rejects(async () => { for await (const chunk of chatService.reply('JavaScript code')) received.push(chunk); });
  assert.ok(received.length);
  const retry = [];
  for await (const chunk of chatService.reply('JavaScript code', { forceSuccess: true })) retry.push(chunk);
  assert.equal(retry.at(-1).complete, true);
  globalThis.location = { search: '' };
});

test('stream failure scenario remains active after navigation clears the query', async () => {
  try {
    globalThis.location = { search: '?scenario=chat-error' };
    const reply = chatService.reply('JavaScript code');
    const first = await reply.next();
    assert.equal(first.done, false);
    assert.equal(first.value.complete, undefined);
    globalThis.location = { search: '' };
    await assert.rejects(async () => { for await (const chunk of reply) assert.notEqual(chunk.complete, true); }, /Phản hồi bị gián đoạn/);
  } finally { globalThis.location = { search: '' }; }
});

test('explicit stream failure mode works after navigation has already cleared the query', async () => {
  globalThis.location = { search: '' };
  const received = [];
  await assert.rejects(async () => {
    for await (const chunk of chatService.reply('JavaScript code', { mode: 'chat-error' })) received.push(chunk);
  }, /Phản hồi bị gián đoạn/);
  assert.ok(received.length);
  assert.equal(received.some(chunk => chunk.complete), false);
});

test('created tickets preserve excerpts after their linked conversation is deleted', async () => {
  const fields = { title: '  Tiêu đề mới  ', category: 'Khác', description: ' Mô tả đủ dài để gửi ticket hỗ trợ. ', course: '', conversationId: 'sample-chat-1', selectedExcerpt: 'Đoạn trích cần giữ lại.' };
  const ticket = await ticketService.create(fields);
  assert.equal(ticket.title, 'Tiêu đề mới');
  assert.equal(ticket.status, 'Đã gửi');
  const data = { conversations: [], tickets: [ticket] };
  const storage = memoryStorage();
  writeData(storage, 'user', data);
  assert.equal(readData(storage, 'user').data.tickets[0].selectedExcerpt, fields.selectedExcerpt);
  globalThis.location = { search: '?scenario=ticket-error' };
  await assert.rejects(ticketService.create(fields));
  assert.equal(fields.title, '  Tiêu đề mới  ');
  globalThis.location = { search: '' };
});

let failures = 0;
for (const { name, run } of tests) {
  try { await run(); console.log(`PASS ${name}`); }
  catch (error) { failures++; console.error(`FAIL ${name}\n${error.stack}`); }
}
console.log(`${tests.length - failures}/${tests.length} logic checks passed.`);
if (failures) process.exitCode = 1;
