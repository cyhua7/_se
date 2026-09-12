// common.js - 所有頁面共用的功能（顯示使用者、登出）

// 從 sessionStorage 讀取登入的學生資料
function getCurrentUser() {
  const data = sessionStorage.getItem('user');
  return data ? JSON.parse(data) : null;
}

// 如果沒有登入資訊，就導回登入頁
function checkLogin() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = 'index.html';
  }
  return user;
}

// 登出：清除 sessionStorage 並回到登入頁
function logout() {
  sessionStorage.removeItem('user');
  window.location.href = 'index.html';
}

// 依照目前頁面，把側邊選單對應項目高亮
function highlightMenu() {
  // 取得目前在瀏覽器開啟的檔名，例如 dashboard.html
  const currentPage = window.location.pathname.split('/').pop();

  document.querySelectorAll('.sidebar a[data-page]').forEach(function (link) {
    // 例如目前是 dashboard.html，則 data-page="dashboard" 的項目加上 active
    if (currentPage.indexOf(link.dataset.page) === 0) {
      link.classList.add('active');
    }
  });
}

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', function () {
  const user = checkLogin();

  // 顯示右上角的使用者名稱
  const topbarUser = document.getElementById('topbar-user');
  if (topbarUser) {
    topbarUser.textContent = user.name;
  }

  highlightMenu();

  // 綁定登出按鈕
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', logout);
  }

  const sidebarLogout = document.getElementById('sidebar-logout');
  if (sidebarLogout) {
    sidebarLogout.addEventListener('click', logout);
  }
});