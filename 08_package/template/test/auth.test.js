import test from 'node:test';
import assert from 'node:assert/strict';

import {
  clearSessionCookie,
  hashPassword,
  normalizeEmail,
  parseCookies,
  readSessionToken,
  sessionCookie,
  validatePassword,
  verifyPassword,
} from '../src/auth.js';

test('normalizeEmail lowercases and trims valid addresses', () => {
  assert.equal(normalizeEmail('  User@Example.COM '), 'user@example.com');
  assert.equal(normalizeEmail('a@b.co'), 'a@b.co');
  assert.equal(normalizeEmail('not-an-email'), null);
  assert.equal(normalizeEmail('a@b'), null);
  assert.equal(normalizeEmail(''), null);
  assert.equal(normalizeEmail(null), null);
});

test('validatePassword enforces a minimum length', () => {
  assert.equal(validatePassword('short'), '密碼至少需要 8 個字元');
  assert.equal(validatePassword('12345678'), null);
  assert.equal(validatePassword(12345678), '密碼格式錯誤');
  assert.equal(validatePassword('a'.repeat(129)), '密碼不可超過 128 個字元');
});

test('hashPassword and verifyPassword round-trip', async () => {
  const { salt, hash } = await hashPassword('correct horse battery');
  assert.equal(typeof salt, 'string');
  assert.equal(typeof hash, 'string');
  assert.ok(salt.length > 0 && hash.length > 0);

  assert.equal(await verifyPassword('correct horse battery', salt, hash), true);
  assert.equal(await verifyPassword('wrong password', salt, hash), false);
  assert.equal(await verifyPassword('correct horse battery', salt, 'not base64!'), false);
});

test('hashPassword uses a different salt each time', async () => {
  const first = await hashPassword('same-password');
  const second = await hashPassword('same-password');
  assert.notEqual(first.salt, second.salt);
  assert.notEqual(first.hash, second.hash);
});

test('parseCookies and readSessionToken extract the session cookie', () => {
  const request = new Request('https://example.com', {
    headers: { cookie: 'theme=dark; bv_session=abc%20123; other=1' },
  });
  const cookies = parseCookies(request);
  assert.equal(cookies.get('theme'), 'dark');
  assert.equal(cookies.get('bv_session'), 'abc 123');
  assert.equal(readSessionToken(request), 'abc 123');
  assert.equal(readSessionToken(new Request('https://example.com')), '');
});

test('session cookies are HttpOnly and optionally Secure', () => {
  const insecure = sessionCookie('token', 3600, false);
  assert.match(insecure, /bv_session=token/);
  assert.match(insecure, /HttpOnly/);
  assert.match(insecure, /SameSite=Lax/);
  assert.doesNotMatch(insecure, /Secure/);

  const secure = sessionCookie('token', 3600, true);
  assert.match(secure, /; Secure/);

  const cleared = clearSessionCookie(true);
  assert.match(cleared, /Max-Age=0/);
  assert.match(cleared, /; Secure/);
});
