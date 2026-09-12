// developing.js - 功能開發中頁面邏輯

// 從網址讀取 feature 參數，例如 developing.html?feature=成績查詢
const params = new URLSearchParams(window.location.search);
const feature = params.get('feature');

if (feature) {
  document.getElementById('feature-title').textContent = feature;
  document.querySelector('.card h3').textContent = feature + '：此功能正在開發中';
}