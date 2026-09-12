// announcements.js - 校務公告頁邏輯

// 目前登入的學生
const user = JSON.parse(sessionStorage.getItem('user'));

// 存放所有公告資料
let allAnnouncements = [];

if (user) {
  // 向伺服器取得公告資料
  fetch('/api/announcements')
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        document.getElementById('announcements-message').textContent = data.message;
        return;
      }

      allAnnouncements = data.announcements;

      // 依公告資料建立分類選單（不重複）
      buildCategoryOptions();
      renderAnnouncements();
    })
    .catch(function () {
      document.getElementById('announcements-message').textContent = '讀取公告失敗，請確認伺服器有啟動';
    });
}

// 依照公告資料建立分類下拉選單
function buildCategoryOptions() {
  const select = document.getElementById('category-select');

  // 收集所有出現過的分類（不重複）
  const categories = [];
  allAnnouncements.forEach(function (ann) {
    if (categories.indexOf(ann.category) === -1) {
      categories.push(ann.category);
    }
  });

  // 依分類文字排序後加入選單
  categories.sort();
  categories.forEach(function (category) {
    const option = document.createElement('option');
    option.value = category;
    option.textContent = category;
    select.appendChild(option);
  });
}

// 分類選單改變時重新顯示
document.getElementById('category-select').addEventListener('change', renderAnnouncements);

// 搜尋框輸入時重新顯示
document.getElementById('search-input').addEventListener('input', renderAnnouncements);

// 依目前的分類與搜尋關鍵字顯示公告
function renderAnnouncements() {
  const selectedCategory = document.getElementById('category-select').value;
  const keyword = document.getElementById('search-input').value.trim().toLowerCase();

  // 先篩選分類
  let result = allAnnouncements;
  if (selectedCategory !== '全部') {
    result = allAnnouncements.filter(function (ann) {
      return ann.category === selectedCategory;
    });
  }

  // 再依標題或內容搜尋（不分大小寫）
  if (keyword) {
    result = result.filter(function (ann) {
      const title = ann.title.toLowerCase();
      const content = ann.content.toLowerCase();
      return title.indexOf(keyword) !== -1 || content.indexOf(keyword) !== -1;
    });
  }

  // 依照日期由新到舊排列
  result.sort(function (a, b) {
    return b.date.localeCompare(a.date);
  });

  const list = document.getElementById('announcements-list');
  const message = document.getElementById('announcements-message');

  // 沒有符合條件的公告
  if (result.length === 0) {
    message.textContent = '沒有符合條件的公告';
    list.innerHTML = '';
    return;
  }

  message.textContent = '';
  list.innerHTML = '';

  // 一筆一筆畫成卡片
  result.forEach(function (ann) {
    const card = document.createElement('div');
    card.classList.add('card', 'announcement-card');

    // 標題（重要公告加上標籤）
    const title = document.createElement('h3');
    title.classList.add('ann-title');
    if (ann.important) {
      const importantTag = document.createElement('span');
      importantTag.classList.add('tag-important');
      importantTag.textContent = '重要';
      title.appendChild(importantTag);
    }
    title.appendChild(document.createTextNode(ann.title));

    // 日期與分類
    const meta = document.createElement('p');
    meta.classList.add('ann-meta');
    const categoryTag = document.createElement('span');
    categoryTag.classList.add('tag-category');
    categoryTag.textContent = ann.category;
    const date = document.createElement('span');
    date.classList.add('ann-date');
    date.textContent = ann.date;
    meta.appendChild(categoryTag);
    meta.appendChild(date);

    const content = document.createElement('p');
    content.classList.add('ann-content');
    content.textContent = ann.content;

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(content);
    list.appendChild(card);
  });
}