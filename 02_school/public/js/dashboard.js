// dashboard.js - 系統首頁邏輯

// common.js 已經處理過登入檢查，這裡讀取使用者並顯示歡迎訊息
const user = JSON.parse(sessionStorage.getItem('user'));
document.getElementById('welcome-name').textContent = user.name;