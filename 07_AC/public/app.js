const $ = (selector) => document.querySelector(selector);

const state = {
  q: '',
  tag: '',
  status: '',
  bookmarks: [],
  loading: false,
};

let accessKey = localStorage.getItem('bookmark_access_key') || '';

const grid = $('#grid');
const empty = $('#empty');
const tagBar = $('#tag-bar');
const addForm = $('#add-form');
const addStatus = $('#add-status');
const addButton = $('#add-button');
const urlInput = $('#url-input');
const noteInput = $('#note-input');
const searchInput = $('#search-input');
const statusTabs = $('#status-tabs');
const lockButton = $('#lock-button');
const toast = $('#toast');
const cardTemplate = $('#card-template');

let toastTimer = null;

function showToast(message, kind = 'info') {
  toast.textContent = message;
  toast.dataset.kind = kind;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 4200);
}

async function api(path, options = {}, retried = false) {
  const headers = new Headers(options.headers || {});
  if (accessKey) headers.set('x-access-key', accessKey);
  if (options.body && !headers.has('content-type')) headers.set('content-type', 'application/json');

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    if (retried) throw new Error('存取金鑰錯誤，請按右上角「重設金鑰」後再試');
    const key = window.prompt('此網站已啟用存取保護，請輸入金鑰：');
    if (!key) throw new Error('需要存取金鑰才能使用');
    accessKey = key.trim();
    localStorage.setItem('bookmark_access_key', accessKey);
    return api(path, options, true);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function refresh() {
  return Promise.all([loadBookmarks(), loadTags()]);
}

async function loadBookmarks() {
  state.loading = true;
  render();
  try {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.tag) params.set('tag', state.tag);
    if (state.status) params.set('status', state.status);

    const query = params.toString();
    const data = await api(`/api/bookmarks${query ? `?${query}` : ''}`);
    state.bookmarks = data.bookmarks || [];
  } catch (error) {
    state.bookmarks = [];
    showToast(error.message, 'error');
  } finally {
    state.loading = false;
    render();
  }
}

async function loadTags() {
  try {
    const data = await api('/api/tags');
    renderTags(data.tags || []);
  } catch {
    renderTags([]);
  }
}

function renderTags(tags) {
  tagBar.replaceChildren();
  if (!tags.length) {
    tagBar.hidden = true;
    return;
  }
  tagBar.hidden = false;

  const all = document.createElement('button');
  all.type = 'button';
  all.className = `chip${state.tag ? '' : ' active'}`;
  all.textContent = '全部標籤';
  all.addEventListener('click', () => {
    state.tag = '';
    refresh();
  });
  tagBar.append(all);

  for (const { name, count } of tags) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `chip${state.tag === name ? ' active' : ''}`;
    chip.textContent = `${name} ${count}`;
    chip.addEventListener('click', () => {
      state.tag = state.tag === name ? '' : name;
      refresh();
    });
    tagBar.append(chip);
  }
}

function render() {
  grid.replaceChildren();
  empty.hidden = state.bookmarks.length > 0 || state.loading;

  if (!state.bookmarks.length) {
    empty.textContent = '';
    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = state.loading ? '⏳' : '🗂️';
    empty.append(icon, state.loading ? '載入中…' : '還沒有符合條件的收藏，貼一個網址開始吧。');
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const bookmark of state.bookmarks) fragment.append(renderCard(bookmark));
  grid.append(fragment);
}

function renderCard(bookmark) {
  const node = cardTemplate.content.firstElementChild.cloneNode(true);
  node.dataset.id = String(bookmark.id);
  node.classList.toggle('is-read', bookmark.isRead);
  node.classList.toggle('is-favorite', bookmark.isFavorite);

  const titleLink = node.querySelector('.title a');
  titleLink.href = bookmark.url;
  titleLink.textContent = bookmark.title || bookmark.url;
  titleLink.target = '_blank';
  titleLink.rel = 'noopener noreferrer';

  const coverLink = node.querySelector('.cover');
  coverLink.href = bookmark.url;
  coverLink.target = '_blank';
  coverLink.rel = 'noopener noreferrer';

  const img = node.querySelector('.cover img');
  const fallback = node.querySelector('.cover-fallback');
  const label = (bookmark.siteName || bookmark.title || bookmark.url || '?').trim().charAt(0);
  fallback.textContent = label.toUpperCase() || '?';
  fallback.style.setProperty('--h', String(hashString(bookmark.url) % 360));

  if (bookmark.coverUrl) {
    img.alt = `${bookmark.title} 的封面`;
    img.addEventListener('load', () => {
      img.hidden = false;
      fallback.hidden = true;
    });
    img.addEventListener('error', () => {
      img.hidden = true;
      fallback.hidden = false;
    });
    img.src = bookmark.coverUrl;
  } else {
    img.hidden = true;
  }

  node.querySelector('.site').textContent = bookmark.siteName || hostnameOf(bookmark.url);
  node.querySelector('.date').textContent = formatDate(bookmark.createdAt);
  node.querySelector('.summary').textContent =
    bookmark.summary || bookmark.description || '尚未產生摘要。';

  if (bookmark.note) {
    const note = node.querySelector('.note');
    note.textContent = `📝 ${bookmark.note}`;
    note.hidden = false;
  }

  const tags = node.querySelector('.tags');
  for (const tag of bookmark.tags) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'tag';
    chip.textContent = `#${tag}`;
    chip.addEventListener('click', () => {
      state.tag = tag;
      refresh();
    });
    tags.append(chip);
  }

  const readButton = node.querySelector('[data-action="read"]');
  readButton.textContent = bookmark.isRead ? '標為未讀' : '標為已讀';
  readButton.addEventListener('click', () => toggleRead(bookmark));

  const favoriteButton = node.querySelector('[data-action="favorite"]');
  favoriteButton.textContent = bookmark.isFavorite ? '★' : '☆';
  favoriteButton.classList.toggle('favorited', bookmark.isFavorite);
  favoriteButton.title = bookmark.isFavorite ? '取消收藏' : '收藏';
  favoriteButton.addEventListener('click', () => toggleFavorite(bookmark));

  node
    .querySelector('[data-action="resummarize"]')
    .addEventListener('click', (event) => resummarize(bookmark, event.currentTarget));

  node.querySelector('[data-action="delete"]').addEventListener('click', () => removeBookmark(bookmark));

  return node;
}

async function toggleRead(bookmark) {
  try {
    await api(`/api/bookmarks/${bookmark.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ isRead: !bookmark.isRead }),
    });
    await refresh();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function toggleFavorite(bookmark) {
  try {
    await api(`/api/bookmarks/${bookmark.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ isFavorite: !bookmark.isFavorite }),
    });
    await refresh();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function resummarize(bookmark, button) {
  button.disabled = true;
  const original = button.textContent;
  button.textContent = '摘要中…';
  try {
    await api(`/api/bookmarks/${bookmark.id}/resummarize`, { method: 'POST' });
    showToast('已重新產生摘要與標籤', 'success');
    await refresh();
  } catch (error) {
    showToast(error.message, 'error');
    button.disabled = false;
    button.textContent = original;
  }
}

async function removeBookmark(bookmark) {
  if (!window.confirm(`確定要刪除「${bookmark.title || bookmark.url}」嗎？`)) return;
  try {
    await api(`/api/bookmarks/${bookmark.id}`, { method: 'DELETE' });
    showToast('已刪除', 'success');
    await refresh();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function formatDate(value) {
  if (!value) return '';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T') + 'Z';
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-TW', { month: 'short', day: 'numeric' }).format(date);
}

function hostnameOf(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

addForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  addButton.disabled = true;
  addStatus.dataset.kind = 'busy';
  addStatus.textContent = '抓取網頁、產生 AI 摘要與封面中…（約 3–10 秒）';

  try {
    const data = await api('/api/bookmarks', {
      method: 'POST',
      body: JSON.stringify({ url, note: noteInput.value.trim() }),
    });
    addForm.reset();
    urlInput.focus();
    addStatus.dataset.kind = data.warning ? 'warn' : 'ok';
    addStatus.textContent = data.warning ? `已收藏（${data.warning}）` : '已加入收藏 ✓';
    await refresh();
  } catch (error) {
    addStatus.dataset.kind = 'error';
    addStatus.textContent = error.message;
  } finally {
    addButton.disabled = false;
  }
});

let searchTimer = null;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = searchInput.value.trim();
    loadBookmarks();
  }, 280);
});

statusTabs.addEventListener('click', (event) => {
  const button = event.target.closest('.tab');
  if (!button) return;
  state.status = button.dataset.status || '';
  for (const tab of statusTabs.querySelectorAll('.tab')) {
    tab.classList.toggle('active', tab === button);
  }
  loadBookmarks();
});

lockButton.addEventListener('click', () => {
  localStorage.removeItem('bookmark_access_key');
  accessKey = '';
  showToast('已清除本機金鑰，下次請求會重新詢問');
});

refresh();
