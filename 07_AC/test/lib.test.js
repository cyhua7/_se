import test from 'node:test';
import assert from 'node:assert/strict';

import {
  decodeEntities,
  deriveTags,
  extractMeta,
  normalizeUrl,
  parseAiResult,
  toPublicBookmark,
} from '../src/lib.js';

test('decodeEntities handles named, decimal and hex entities', () => {
  assert.equal(decodeEntities('a &amp; b &#39;c&#x27; &lt; &#x1F516;'), "a & b 'c' < 🔖");
  assert.equal(decodeEntities('&unknown;'), '&unknown;');
});

test('normalizeUrl accepts bare domains and rejects unsafe schemes', () => {
  assert.equal(normalizeUrl('example.com/posts/1'), 'https://example.com/posts/1');
  assert.equal(normalizeUrl('  https://example.com  '), 'https://example.com/');
  assert.equal(normalizeUrl('ftp://example.com/file'), null);
  assert.equal(normalizeUrl('javascript:alert(1)'), null);
  assert.equal(normalizeUrl('not a real url'), null);
  assert.equal(normalizeUrl(''), null);
  assert.equal(normalizeUrl(null), null);
});

test('extractMeta prefers Open Graph fields and resolves relative images', () => {
  const html = `<!doctype html>
    <html><head>
      <title>Fallback &amp; Title</title>
      <meta property="og:title" content="OG &amp; Title" />
      <meta name="description" content="Plain description" />
      <meta property="og:description" content="OG description" />
      <meta property="og:image" content="/img/cover.png" />
      <meta property="og:site_name" content="Example" />
    </head><body>
      <script>alert('should not appear')</script>
      <article><p>Hello world, this is the article body.</p></article>
    </body></html>`;

  const meta = extractMeta(html, 'https://example.com/posts/1');

  assert.equal(meta.title, 'OG & Title');
  assert.equal(meta.description, 'OG description');
  assert.equal(meta.image, 'https://example.com/img/cover.png');
  assert.equal(meta.siteName, 'Example');
  assert.match(meta.text, /Hello world/);
  assert.doesNotMatch(meta.text, /should not appear/);
});

test('extractMeta falls back to hostname when no title exists', () => {
  const meta = extractMeta('<html><body>text</body></html>', 'https://example.com/x');
  assert.equal(meta.title, 'example.com');
});

test('parseAiResult handles plain JSON, code fences and garbage', () => {
  assert.deepEqual(parseAiResult('{"summary":"A short summary","tags":["#AI"," ai ","Web Dev"]}'), {
    summary: 'A short summary',
    tags: ['ai', 'web-dev'],
  });

  assert.deepEqual(parseAiResult('```json\n{"summary":"Fenced","tags":["x"]}\n```'), {
    summary: 'Fenced',
    tags: ['x'],
  });

  assert.deepEqual(parseAiResult('Here you go: {"summary":"Embedded","tags":["y"]} done'), {
    summary: 'Embedded',
    tags: ['y'],
  });

  assert.deepEqual(parseAiResult('not json at all'), { summary: '', tags: [] });
  assert.deepEqual(parseAiResult(''), { summary: '', tags: [] });
});

test('deriveTags extracts frequent words and caps the list at five', () => {
  const tags = deriveTags({
    description: 'Cloudflare Workers and D1 database',
    text: 'Cloudflare Workers run JavaScript. Cloudflare D1 is a database. Workers are fast.',
    siteName: 'Cloudflare Blog',
  });

  assert.ok(tags.length > 0 && tags.length <= 5);
  assert.ok(tags.includes('cloudflare'));
  assert.ok(tags.includes('cloudflare-blog'));
});

test('toPublicBookmark maps database rows to API objects', () => {
  const bookmark = toPublicBookmark({
    id: 7,
    url: 'https://example.com',
    title: 'Example',
    description: null,
    summary: null,
    tags: '["ai","web"]',
    cover_key: 'cover-123.jpg',
    site_name: 'Example',
    note: null,
    is_read: 1,
    is_favorite: 0,
    created_at: '2025-01-01 00:00:00',
    updated_at: '2025-01-01 00:00:00',
  });

  assert.equal(bookmark.coverUrl, '/api/covers/cover-123.jpg');
  assert.deepEqual(bookmark.tags, ['ai', 'web']);
  assert.equal(bookmark.isRead, true);
  assert.equal(bookmark.isFavorite, false);
  assert.equal(bookmark.description, '');
  assert.equal(bookmark.note, '');
});

test('toPublicBookmark survives broken tag JSON', () => {
  const bookmark = toPublicBookmark({ id: 1, url: 'https://example.com', tags: 'not-json' });
  assert.deepEqual(bookmark.tags, []);
  assert.equal(bookmark.coverUrl, null);
});
