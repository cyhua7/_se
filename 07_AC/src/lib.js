const ENTITIES = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
};

export function decodeEntities(input = '') {
  return String(input).replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (match, code) => {
    if (code[0] === '#') {
      const hex = code[1] === 'x' || code[1] === 'X';
      const value = Number.parseInt(code.slice(hex ? 2 : 1), hex ? 16 : 10);
      if (Number.isFinite(value) && value > 0 && value <= 0x10ffff) {
        try {
          return String.fromCodePoint(value);
        } catch {
          return match;
        }
      }
      return match;
    }
    return ENTITIES[code.toLowerCase()] ?? match;
  });
}

export function normalizeUrl(input) {
  if (typeof input !== 'string') return null;
  let raw = input.trim();
  if (!raw) return null;
  if (!/^[a-z][a-z0-9+.-]*:/i.test(raw)) raw = `https://${raw}`;
  try {
    const url = new URL(raw);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    if (!url.hostname || !url.hostname.includes('.')) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export function resolveUrl(href, baseUrl) {
  if (!href) return null;
  try {
    return new URL(href, baseUrl).toString();
  } catch {
    return null;
  }
}

function attr(tag, name) {
  const pattern = new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i');
  const match = tag.match(pattern);
  if (!match) return null;
  return decodeEntities(match[2] ?? match[3] ?? match[4] ?? '');
}

export function extractText(html) {
  const source = String(html || '');
  const scoped =
    source.match(/<article\b[^>]*>([\s\S]*?)<\/article>/i)?.[1] ||
    source.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)?.[1] ||
    source;

  const cleaned = scoped
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/(p|div|li|h[1-6]|section|article|tr)>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return decodeEntities(cleaned).slice(0, 8000);
}

export function extractMeta(html, pageUrl) {
  const source = String(html || '');
  const metas = {};

  for (const tag of source.match(/<meta\b[^>]*>/gi) || []) {
    const key = (attr(tag, 'property') || attr(tag, 'name') || '').trim().toLowerCase();
    const content = attr(tag, 'content');
    if (key && content != null && metas[key] === undefined) metas[key] = content;
  }

  const titleTag = source.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  const rawTitle =
    metas['og:title'] ||
    metas['twitter:title'] ||
    (titleTag ? decodeEntities(titleTag[1]) : '');

  let fallbackTitle = '';
  try {
    fallbackTitle = new URL(pageUrl).hostname;
  } catch {
    fallbackTitle = '';
  }

  return {
    title: rawTitle.replace(/\s+/g, ' ').trim() || fallbackTitle,
    description: (metas['og:description'] || metas['description'] || metas['twitter:description'] || '')
      .replace(/\s+/g, ' ')
      .trim(),
    image: resolveUrl(
      metas['og:image'] || metas['og:image:url'] || metas['twitter:image'] || null,
      pageUrl
    ),
    siteName: (metas['og:site_name'] || '').replace(/\s+/g, ' ').trim(),
    text: extractText(source),
  };
}

const STOP_WORDS = new Set(
  (
    'the and for with that this from are was were will have has had not but you your our ' +
    'their they them his her its can could should would about into over under more most ' +
    'other some such only own same than too very just also then there here what when where ' +
    'which who whom why how all any both each few nor off on out so up down'
  ).split(' ')
);

export function deriveTags({ text = '', description = '', siteName = '' } = {}) {
  const counts = new Map();
  const words = `${description} ${text}`.toLowerCase().match(/[\p{L}\p{N}][\p{L}\p{N}_-]{2,}/gu) || [];

  for (const word of words) {
    if (STOP_WORDS.has(word) || /^\d+$/.test(word)) continue;
    counts.set(word, (counts.get(word) || 0) + 1);
  }

  const top = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 5)
    .map(([word]) => word.slice(0, 24));

  if (siteName) {
    top.unshift(siteName.toLowerCase().replace(/\s+/g, '-').slice(0, 24));
  }

  return [...new Set(top)].slice(0, 5);
}

export function parseAiResult(raw) {
  const text = String(raw || '').trim();
  if (!text) return { summary: '', tags: [] };

  const candidates = [];
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) candidates.push(fenced[1].trim());
  candidates.push(text);
  const objectMatch = text.match(/\{[\s\S]*\}/);
  if (objectMatch) candidates.push(objectMatch[0]);

  for (const candidate of candidates) {
    try {
      const data = JSON.parse(candidate);
      if (!data || typeof data !== 'object' || Array.isArray(data)) continue;

      const summary = typeof data.summary === 'string' ? data.summary.trim().slice(0, 800) : '';
      const rawTags = Array.isArray(data.tags) ? data.tags : [];
      const tags = [
        ...new Set(
          rawTags
            .filter((tag) => typeof tag === 'string')
            .map((tag) =>
              tag
                .trim()
                .toLowerCase()
                .replace(/^#+/, '')
                .replace(/\s+/g, '-')
                .slice(0, 24)
            )
            .filter(Boolean)
        ),
      ].slice(0, 6);

      if (summary || tags.length) return { summary, tags };
    } catch {
      // try the next candidate
    }
  }

  return { summary: '', tags: [] };
}

export function toPublicBookmark(row = {}) {
  let tags = [];
  try {
    const parsed = JSON.parse(row.tags || '[]');
    if (Array.isArray(parsed)) tags = parsed.filter((tag) => typeof tag === 'string');
  } catch {
    tags = [];
  }

  const coverKey = typeof row.cover_key === 'string' ? row.cover_key : '';

  return {
    id: row.id,
    url: row.url || '',
    title: row.title || row.url || '',
    description: row.description || '',
    summary: row.summary || '',
    tags,
    siteName: row.site_name || '',
    note: row.note || '',
    coverUrl: coverKey ? `/api/covers/${encodeURIComponent(coverKey)}` : null,
    isRead: Boolean(row.is_read),
    isFavorite: Boolean(row.is_favorite),
    createdAt: row.created_at || '',
    updatedAt: row.updated_at || '',
  };
}
