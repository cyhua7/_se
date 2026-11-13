const PBKDF2_ITERATIONS = 100_000;
const SALT_BYTES = 16;
const HASH_BYTES = 32;
const SESSION_DAYS = 30;
const SESSION_COOKIE = 'bv_session';

const encoder = new TextEncoder();

function toBase64(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function fromBase64(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function toHex(bytes) {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function derive(password, salt) {
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    key,
    HASH_BYTES * 8
  );
  return new Uint8Array(bits);
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(value));
  return toHex(new Uint8Array(digest));
}

export async function hashPassword(password) {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const hash = await derive(password, salt);
  return { salt: toBase64(salt), hash: toBase64(hash) };
}

export async function verifyPassword(password, saltB64, hashB64) {
  let expected;
  try {
    expected = fromBase64(hashB64);
  } catch {
    return false;
  }
  const actual = await derive(password, fromBase64(saltB64));
  if (actual.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < actual.length; i += 1) diff |= actual[i] ^ expected[i];
  return diff === 0;
}

export async function createSession(env, userId) {
  const token = toHex(crypto.getRandomValues(new Uint8Array(32)));
  const tokenHash = await sha256Hex(token);
  const expiresAt = new Date(Date.now() + SESSION_DAYS * 86_400_000).toISOString();

  await env.DB.prepare(
    'INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)'
  )
    .bind(tokenHash, userId, expiresAt)
    .run();

  return { token, maxAge: SESSION_DAYS * 86_400 };
}

export async function getSessionUser(env, token) {
  if (!token) return null;
  const tokenHash = await sha256Hex(token);

  const row = await env.DB.prepare(
    `SELECT users.id AS id, users.email AS email, sessions.expires_at AS expires_at
       FROM sessions
       JOIN users ON users.id = sessions.user_id
      WHERE sessions.token_hash = ?`
  )
    .bind(tokenHash)
    .first();

  if (!row) return null;

  if (new Date(row.expires_at).getTime() <= Date.now()) {
    await env.DB.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(tokenHash).run();
    return null;
  }

  return { id: row.id, email: row.email };
}

export async function deleteSession(env, token) {
  if (!token) return;
  const tokenHash = await sha256Hex(token);
  await env.DB.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(tokenHash).run();
}

export function parseCookies(request) {
  const header = request.headers.get('cookie') || '';
  const cookies = new Map();
  for (const part of header.split(';')) {
    const index = part.indexOf('=');
    if (index < 0) continue;
    const name = part.slice(0, index).trim();
    if (!name) continue;
    try {
      cookies.set(name, decodeURIComponent(part.slice(index + 1).trim()));
    } catch {
      cookies.set(name, part.slice(index + 1).trim());
    }
  }
  return cookies;
}

export function readSessionToken(request) {
  return parseCookies(request).get(SESSION_COOKIE) || '';
}

export function sessionCookie(token, maxAge, secure) {
  return `${SESSION_COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${
    secure ? '; Secure' : ''
  }`;
}

export function clearSessionCookie(secure) {
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure ? '; Secure' : ''}`;
}

export function normalizeEmail(email) {
  if (typeof email !== 'string') return null;
  const value = email.trim().toLowerCase();
  if (value.length < 3 || value.length > 254) return null;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return null;
  return value;
}

export function validatePassword(password) {
  if (typeof password !== 'string') return '密碼格式錯誤';
  if (password.length < 8) return '密碼至少需要 8 個字元';
  if (password.length > 128) return '密碼不可超過 128 個字元';
  return null;
}
