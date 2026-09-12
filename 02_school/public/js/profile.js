// profile.js - 個人資料頁邏輯

// 目前登入的學生（從 sessionStorage 讀取，不寫死學生帳號）
const userData = JSON.parse(sessionStorage.getItem('user'));

// 保存從伺服器讀取的最新個人資料
let currentUser = null;

// 顯示訊息：isSuccess 為 true 時用綠色成功訊息
function showMessage(text, isSuccess) {
  const el = document.getElementById('profile-message');
  el.textContent = text;
  el.classList.toggle('message-success', !!isSuccess);
}

// 載入目前登入學生的個人資料
function loadProfile() {
  if (!userData) {
    return;
  }

  fetch('/api/profile?studentId=' + encodeURIComponent(userData.studentId))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        showMessage(data.message, false);
        return;
      }

      currentUser = data.user;
      renderProfile();
    })
    .catch(function () {
      showMessage('讀取個人資料失敗，請確認伺服器有啟動', false);
    });
}

// 將個人資料填入畫面（一般顯示模式）
function renderProfile() {
  document.getElementById('student-id').textContent = currentUser.studentId;
  document.getElementById('student-name').textContent = currentUser.name;
  document.getElementById('student-department').textContent = currentUser.department;
  document.getElementById('student-grade').textContent = currentUser.grade;
  document.getElementById('student-class').textContent = currentUser.studentClass;
  document.getElementById('student-email').textContent = currentUser.email;
  document.getElementById('student-enrollment').textContent = currentUser.enrollmentYear;
  document.getElementById('student-phone').textContent = currentUser.phone || '';
  document.getElementById('student-address').textContent = currentUser.address || '';
  document.getElementById('student-note').textContent = currentUser.note || '';
}

// 進入編輯模式：可修改欄位（Email、電話、聯絡地址、個人備註）變成輸入框
function enterEditMode() {
  // 資料還沒載入就無法編輯
  if (!currentUser) {
    return;
  }

  // 用目前資料填入輸入框
  document.getElementById('input-email').value = currentUser.email || '';
  document.getElementById('input-phone').value = currentUser.phone || '';
  document.getElementById('input-address').value = currentUser.address || '';
  document.getElementById('input-note').value = currentUser.note || '';

  // 隱藏純文字顯示，顯示輸入框
  document.getElementById('student-email').hidden = true;
  document.getElementById('student-phone').hidden = true;
  document.getElementById('student-address').hidden = true;
  document.getElementById('student-note').hidden = true;

  document.getElementById('input-email').hidden = false;
  document.getElementById('input-phone').hidden = false;
  document.getElementById('input-address').hidden = false;
  document.getElementById('input-note').hidden = false;

  // 切換按鈕：顯示儲存與取消
  document.getElementById('edit-btn').hidden = true;
  document.getElementById('save-btn').hidden = false;
  document.getElementById('cancel-btn').hidden = false;

  showMessage('', false);
}

// 離開編輯模式，恢復一般顯示
function exitEditMode() {
  // 隱藏輸入框，顯示純文字
  document.getElementById('student-email').hidden = false;
  document.getElementById('student-phone').hidden = false;
  document.getElementById('student-address').hidden = false;
  document.getElementById('student-note').hidden = false;

  document.getElementById('input-email').hidden = true;
  document.getElementById('input-phone').hidden = true;
  document.getElementById('input-address').hidden = true;
  document.getElementById('input-note').hidden = true;

  // 切換按鈕：改回顯示「編輯資料」
  document.getElementById('edit-btn').hidden = false;
  document.getElementById('save-btn').hidden = true;
  document.getElementById('cancel-btn').hidden = true;
}

// 取消編輯：放棄修改，恢復原本資料
function cancelEdit() {
  exitEditMode();
  // 用原本資料重新填回畫面
  renderProfile();
  showMessage('', false);
}

// 儲存個人資料：呼叫後端 API
function saveProfile() {
  const email = document.getElementById('input-email').value.trim();
  const phone = document.getElementById('input-phone').value.trim();
  const address = document.getElementById('input-address').value.trim();
  const note = document.getElementById('input-note').value;

  fetch('/api/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      studentId: currentUser.studentId,
      email: email,
      phone: phone,
      address: address,
      note: note
    })
  })
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        showMessage(data.message, false);
        return;
      }

      // 同步更新 sessionStorage 的登入資料，避免其他地方顯示舊資料
      const stored = JSON.parse(sessionStorage.getItem('user'));
      if (stored) {
        stored.email = email;
        stored.phone = phone;
        stored.address = address;
        stored.note = note;
        sessionStorage.setItem('user', JSON.stringify(stored));
      }

      showMessage(data.message, true);
      exitEditMode();

      // 儲存成功後重新載入資料
      loadProfile();
    })
    .catch(function () {
      showMessage('儲存失敗，請確認伺服器有啟動', false);
    });
}

// 綁定按鈕事件
document.getElementById('edit-btn').addEventListener('click', enterEditMode);
document.getElementById('save-btn').addEventListener('click', saveProfile);
document.getElementById('cancel-btn').addEventListener('click', cancelEdit);

// 頁面載入時讀取個人資料
loadProfile();