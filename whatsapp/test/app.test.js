// HTTP layer only: a fake session manager stands in for Baileys.
import assert from 'node:assert/strict';
import http from 'node:http';
import { after, before, test } from 'node:test';
import { createHandler } from '../src/app.js';
import { HttpError } from '../src/http.js';

const TOKEN = 'test-token-1234567890';
const sent = [];
const fakeSession = {
  info: () => ({ status: 'connected', qr: null, phone: '5511900000000', name: 'Home', error: null }),
  start: async () => {},
  logout: async () => {},
  groups: async () => [{ id: '1203@g.us', name: 'Family', participants: 3 }],
  send: async (to, text) => {
    if (to === 'bad') throw new HttpError(400, 'bad is not on WhatsApp');
    sent.push({ to, text });
    return { id: 'abc' };
  },
};
const manager = {
  session: (id) => {
    if (!/^[A-Za-z0-9-]{1,64}$/.test(id)) throw new HttpError(400, 'Invalid session id');
    return fakeSession;
  },
};

let server;
let base;
before(async () => {
  server = http.createServer(createHandler({ manager, token: TOKEN }));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());

const call = (method, path, body, token = TOKEN) =>
  fetch(base + path, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });

test('health needs no token', async () => {
  const res = await fetch(`${base}/health`);
  assert.equal(res.status, 200);
});

test('everything else needs the token', async () => {
  assert.equal((await call('GET', '/sessions/abc', null, 'wrong')).status, 401);
  assert.equal((await call('GET', '/sessions/abc')).status, 200);
});

test('session routes', async () => {
  assert.equal((await (await call('GET', '/sessions/abc')).json()).status, 'connected');
  assert.equal((await call('POST', '/sessions/abc/connect')).status, 200);
  assert.deepEqual(await (await call('GET', '/sessions/abc/groups')).json(), [
    { id: '1203@g.us', name: 'Family', participants: 3 },
  ]);
  assert.equal((await call('GET', '/sessions/../etc')).status, 404);
  assert.equal((await call('GET', '/sessions/a%2Fb')).status, 400);
  assert.equal((await call('DELETE', '/sessions/abc')).status, 405);
});

test('sending messages', async () => {
  const ok = await call('POST', '/sessions/abc/messages', { to: '5511987654321', text: 'Hi' });
  assert.equal(ok.status, 200);
  assert.deepEqual(sent.at(-1), { to: '5511987654321', text: 'Hi' });
  assert.equal((await call('POST', '/sessions/abc/messages', { to: '551', text: '' })).status, 400);
  const bad = await call('POST', '/sessions/abc/messages', { to: 'bad', text: 'Hi' });
  assert.equal(bad.status, 400);
  assert.match((await bad.json()).error, /not on WhatsApp/);
});
