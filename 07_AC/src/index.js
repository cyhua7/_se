import {
  deriveTags,
  extractMeta,
  normalizeUrl,
  parseAiResult,
  toPublicBookmark,
} from './lib.js';

const AI_MODEL = '@cf/meta/llama-3.1-8b-instruct';
const MAX_REQUEST_BYTES = 500 * 1024;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MAX_HTML_CHARS = 600_000;

const IMAGE_EXTENSIONS = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
  'image/gif': 'gif',
  'image/avif': 'avif',
};
const ALLOWED_IMAGE_TYPES = new Set(Object.keys(IMAGE_EXTENSIONS));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
        return await handleApi(request, env, url);
      }
      return await env.ASSETS.fetch(request);
    } catch (error) {
      console.error('Unhandled error:', error);
      return json({ error: '伺服器發生錯誤', detail: String(error?.message || error) }, 500);
    }
  },
};

async function handleApi(request, env, url) {
  try {
    const { pathname } = url;

    if (pathname === '/api/health') {
      return json({ ok: true, ai: Boolean(env.AI), auth: Boolean(env.ACCESS_KEY) });
    }

    // 封面圖會用 <img> 載入，無法附加自訂標頭，因此依不可猜測的 R2 key 公開。
    if (pathname.startsWith('/api/covers/')) {
      return await serveCover(env, pathname);
    }

    if (!isAuthorized(request, env)) {
      return json({ error: '需要存取金鑰（x-access-key）' }, 401);
    }

    if (pathname === '/api/bookmarks') {
      if (request.method === 'GET') return await listBookmarks(env, url);
      if (request.method === 'POST') return await createBookmark(request, env);
      return methodNotAllowed();
    }

    if (pathname === '/api/tags' && request.method === 'GET') {
      return await listTags(env);
    }

    const resummarizeMatch = pathname.match(/^\/api\/bookmarks\/(\d+)\/resummarize$/);
    if (resummarizeMatch && request.method === 'POST') {
      return await resummarizeBookmark(env, Number(resummarizeMatch[1]));
    }

    const itemMatch = pathname.match(/^\/api\/bookmarks\/(\d+)$/);
    if (itemMatch) {
      const id = Number(itemMatch[1]);
      if (request.method === 'PATCH') return await updateBookmark(request, env, id);
      if (request.method === 'DELETE') return await deleteBookmark(env, id);
      return methodNotAllowed();
    }

    return json({ error: '找不到這個 API' }, 404);
  } catch (error) {
    if (error instanceof HttpError) {
      return json({ error: error.message }, error.status);
    }
    throw error;
  }
}

async function listBookmarks(env, url) {
  const where = [];
  const binds = [];

  const q = (url.searchParams.get('q') || '').trim();
  if (q) {
    const like = `%${q}%`;
    where.push('(title LIKE ? OR description LIKE ? OR summary LIKE ? OR url LIKE ? OR note LIKE ?)');
    binds.push(like, like, like, like, like);
  }

  const tag = (url.searchParams.get('tag') || '').trim().toLowerCase();
  if (tag) {
    where.push('EXISTS (SELECT 1 FROM json_each(bookmarks.tags) WHERE lower(value) = ?)');
    binds.push(tag);
  }

  const status = url.searchParams.get('status');
  if (status === 'unread') where.push('is_read = 0');
  else if (status === 'read') where.push('is_read = 1');
  else if (status === 'favorite') where.push('is_favorite = 1');

  const sql = `SELECT * FROM bookmarks ${
    where.length ? `WHERE ${where.join(' AND ')}` : ''
  } ORDER BY is_favorite DESC, is_read ASC, datetime(created_at) DESC, id DESC LIMIT 300`;

  const { results } = await env.DB.prepare(sql).bind(...binds).all();
  return json({ bookmarks: (results || []).map(toPublicBookmark) });
}

async function listTags(env) {
  const { results } = await env.DB.prepare('SELECT tags FROM bookmarks').all();
  const counts = new Map();

  for (const row of results || []) {
    let tags = [];
    try {
      tags = JSON.parse(row.tags || '[]');
    } catch {
      tags = [];
    }
    if (!Array.isArray(tags)) continue;
    for (const tag of tags) {
      if (typeof tag !== 'string' || !tag) continue;
      counts.set(tag, (counts.get(tag) || 0) + 1);
    }
  }

  const tags = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([name, count]) => ({ name, count }));

  return json({ tags });
}

async function createBookmark(request, env) {
  const body = await readJson(request);
  const bookmarkUrl = normalizeUrl(body.url);
  if (!bookmarkUrl) throw new HttpError(400, '請輸入有效的 http(s) 網址');

  const existing = await env.DB.prepare('SELECT id FROM bookmarks WHERE url = ?')
    .bind(bookmarkUrl)
    .first();
  if (existing) throw new HttpError(409, '這個網址已經收藏過了');

  const note = typeof body.note === 'string' ? body.note.trim().slice(0, 500) : '';

  let meta = {
    title: new URL(bookmarkUrl).hostname,
    description: '',
    image: null,
    siteName: '',
    text: '',
  };
  let warning = null;

  try {
    meta = await fetchPage(bookmarkUrl);
  } catch (error) {
    warning = `無法讀取網頁內容：${String(error?.message || error)}`;
  }

  let summary = '';
  let tags = [];

  if (!warning && meta.text.length >= 80) {
    try {
      const ai = await summarize(env, meta, bookmarkUrl);
      summary = ai.summary;
      tags = ai.tags;
    } catch (error) {
      console.error('AI summary failed:', error);
      warning = 'AI 摘要暫時無法使用，已先收藏網址。';
    }
  }
  if (!tags.length) tags = deriveTags(meta);

  let coverKey = null;
  if (meta.image) {
    try {
      coverKey = await cacheCover(env, meta.image);
    } catch (error) {
      console.error('Cover caching failed:', error);
    }
  }

  const row = await env.DB.prepare(
    `INSERT INTO bookmarks (url, title, description, summary, tags, cover_key, site_name, note)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
     RETURNING *`
  )
    .bind(
      bookmarkUrl,
      meta.title.slice(0, 300),
      meta.description.slice(0, 1000),
      summary,
      JSON.stringify(tags),
      coverKey,
      meta.siteName.slice(0, 120),
      note
    )
    .first();

  return json({ bookmark: toPublicBookmark(row), warning }, 201);
}

async function updateBookmark(request, env, id) {
  const body = await readJson(request);
  const sets = [];
  const binds = [];

  if (typeof body.isRead === 'boolean') {
    sets.push('is_read = ?');
    binds.push(body.isRead ? 1 : 0);
  }
  if (typeof body.isFavorite === 'boolean') {
    sets.push('is_favorite = ?');
    binds.push(body.isFavorite ? 1 : 0);
  }
  if (typeof body.note === 'string') {
    sets.push('note = ?');
    binds.push(body.note.trim().slice(0, 500));
  }
  if (!sets.length) throw new HttpError(400, '沒有可更新的欄位');

  sets.push("updated_at = datetime('now')");
  binds.push(id);

  const row = await env.DB.prepare(
    `UPDATE bookmarks SET ${sets.join(', ')} WHERE id = ? RETURNING *`
  )
    .bind(...binds)
    .first();
  if (!row) throw new HttpError(404, '找不到這筆收藏');

  return json({ bookmark: toPublicBookmark(row) });
}

async function deleteBookmark(env, id) {
  const row = await env.DB.prepare('SELECT cover_key FROM bookmarks WHERE id = ?').bind(id).first();
  if (!row) throw new HttpError(404, '找不到這筆收藏');

  await env.DB.prepare('DELETE FROM bookmarks WHERE id = ?').bind(id).run();

  if (row.cover_key) {
    try {
      await env.BUCKET.delete(row.cover_key);
    } catch (error) {
      console.error('R2 delete failed:', error);
    }
  }

  return json({ ok: true });
}

async function resummarizeBookmark(env, id) {
  const row = await env.DB.prepare('SELECT * FROM bookmarks WHERE id = ?').bind(id).first();
  if (!row) throw new HttpError(404, '找不到這筆收藏');

  const meta = await fetchPage(row.url);
  const { summary, tags } = await summarize(env, meta, row.url);
  const finalTags = tags.length ? tags : deriveTags(meta);

  if (!summary && !tags.length) {
    throw new HttpError(502, 'AI 沒有回傳結果，請稍後再試');
  }

  const updated = await env.DB.prepare(
    `UPDATE bookmarks SET
       summary = ?,
       tags = ?,
       description = CASE WHEN description = '' THEN ? ELSE description END,
       title = CASE WHEN title = '' THEN ? ELSE title END,
       updated_at = datetime('now')
     WHERE id = ? RETURNING *`
  )
    .bind(summary, JSON.stringify(finalTags), meta.description, meta.title, id)
    .first();

  return json({ bookmark: toPublicBookmark(updated) });
}

async function fetchPage(pageUrl) {
  const response = await fetch(pageUrl, {
    headers: {
      'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'accept-language': 'zh-TW,zh;q=0.9,en;q=0.8',
    },
    redirect: 'follow',
    signal: AbortSignal.timeout(12_000),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const contentType = response.headers.get('content-type') || '';
  if (!/text\/html|application\/xhtml/i.test(contentType)) {
    throw new Error('目標不是 HTML 網頁');
  }

  const html = (await response.text()).slice(0, MAX_HTML_CHARS);
  return extractMeta(html, response.url || pageUrl);
}

async function summarize(env, meta, pageUrl) {
  if (!env.AI) return { summary: '', tags: [] };

  const content = [
    `Title: ${meta.title}`,
    `URL: ${pageUrl}`,
    `Description: ${meta.description}`,
    '',
    meta.text.slice(0, 6000),
  ].join('\n');

  const result = await env.AI.run(AI_MODEL, {
    messages: [
      {
        role: 'system',
        content:
          'You summarize web pages for a read-later app. Reply with ONLY compact JSON, no markdown and no code fences.',
      },
      {
        role: 'user',
        content:
          'Summarize the page in 2-3 sentences and suggest 3-5 short topical tags. ' +
          'Use the same language as the page content. ' +
          'Return JSON with this exact shape: {"summary":"...","tags":["...","..."]}\n\n' +
          content,
      },
    ],
    max_tokens: 512,
    temperature: 0.2,
  });

  return parseAiResult(result?.response ?? result?.result?.response ?? '');
}

async function cacheCover(env, imageUrl) {
  if (!env.BUCKET || !imageUrl) return null;

  const response = await fetch(imageUrl, {
    headers: {
      'user-agent': 'Mozilla/5.0 (compatible; BookmarkVault/1.0)',
      accept: 'image/avif,image/webp,image/png,image/jpeg,image/gif',
    },
    redirect: 'follow',
    signal: AbortSignal.timeout(10_000),
  });

  if (!response.ok) return null;

  const contentType = (response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (!ALLOWED_IMAGE_TYPES.has(contentType)) return null;

  const declaredLength = Number(response.headers.get('content-length') || 0);
  if (declaredLength && declaredLength > MAX_IMAGE_BYTES) return null;

  const buffer = await response.arrayBuffer();
  if (!buffer.byteLength || buffer.byteLength > MAX_IMAGE_BYTES) return null;

  const key = `cover-${crypto.randomUUID()}.${IMAGE_EXTENSIONS[contentType]}`;
  await env.BUCKET.put(key, buffer, {
    httpMetadata: {
      contentType,
      cacheControl: 'public, max-age=31536000, immutable',
    },
  });

  return key;
}

async function serveCover(env, pathname) {
  const rawKey = pathname.slice('/api/covers/'.length);
  let key;
  try {
    key = decodeURIComponent(rawKey);
  } catch {
    return new Response('Not found', { status: 404 });
  }

  if (!/^cover-[a-f0-9-]+\.[a-z0-9]+$/i.test(key)) {
    return new Response('Not found', { status: 404 });
  }

  const object = await env.BUCKET.get(key);
  if (!object) return new Response('Not found', { status: 404 });

  const headers = new Headers();
  headers.set('content-type', object.httpMetadata?.contentType || 'application/octet-stream');
  headers.set('cache-control', 'public, max-age=31536000, immutable');
  headers.set('x-content-type-options', 'nosniff');

  return new Response(object.body, { headers });
}

function isAuthorized(request, env) {
  if (!env.ACCESS_KEY) return true;
  return safeEqual(request.headers.get('x-access-key') || '', env.ACCESS_KEY);
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function readJson(request) {
  const length = Number(request.headers.get('content-length') || 0);
  if (length > MAX_REQUEST_BYTES) throw new HttpError(413, '請求內容過大');

  let body;
  try {
    body = await request.json();
  } catch {
    throw new HttpError(400, 'JSON 格式錯誤');
  }

  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new HttpError(400, 'JSON 格式錯誤');
  }
  return body;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

function methodNotAllowed() {
  return json({ error: 'Method not allowed' }, 405);
}

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
  }
}
