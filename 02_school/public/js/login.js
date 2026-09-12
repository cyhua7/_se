// login.js - 登入頁邏輯

document.getElementById('login-form').addEventListener('submit', function (event) {
  // 阻止表單自動送出（重整頁面）
  event.preventDefault();

  const studentId = document.getElementById('studentId').value.trim();
  const password = document.getElementById('password').value.trim();

  // 打 API 到伺服器驗證帳號密碼
  fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentId: studentId, password: password })
  })
    .then(function (response) {
      // 先轉成 JSON
      return response.json();
    })
    .then(function (data) {
      if (data.success) {
        // 把學生資料存到 sessionStorage，之後頁面都可用
        sessionStorage.setItem('user', JSON.stringify(data.user));
        // 跳轉到系統首頁
        window.location.href = 'dashboard.html';
      } else {
        // 登入失敗，顯示錯誤訊息
        document.getElementById('error-message').textContent = data.message;
      }
    })
    .catch(function (error) {
      document.getElementById('error-message').textContent = '伺服器連線錯誤，請確認伺服器有啟動';
    });
});