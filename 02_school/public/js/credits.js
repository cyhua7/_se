// credits.js - 畢業學分頁邏輯

// 目前登入的學生
const user = JSON.parse(sessionStorage.getItem('user'));

if (user) {
  // 向伺服器取得目前學生的畢業學分資料
  fetch('/api/graduation?studentId=' + encodeURIComponent(user.studentId))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        document.getElementById('credit-total').textContent = '無法取得資料';
        return;
      }
      renderCredits(data.graduation);
    })
    .catch(function () {
      document.getElementById('credit-total').textContent = '讀取失敗，請確認伺服器有啟動';
    });
}

// 依照畢業學分資料畫出總覽、進度條與分類表格
function renderCredits(graduation) {
  const totalRequired = graduation.totalRequired;
  const categories = graduation.categories;

  // 把四個分類的已完成學分加總
  let totalCompleted = 0;
  Object.keys(categories).forEach(function (name) {
    totalCompleted += categories[name].completed;
  });

  // 尚缺學分（不可以是負數）
  let remaining = totalRequired - totalCompleted;
  if (remaining < 0) {
    remaining = 0;
  }

  // 完成百分比（最多 100%）
  let percent = (totalCompleted / totalRequired) * 100;
  if (percent > 100) {
    percent = 100;
  }

  // 總覽卡片
  document.getElementById('credit-total').textContent = totalRequired;
  document.getElementById('credit-completed').textContent = totalCompleted;
  document.getElementById('credit-remaining').textContent = remaining;
  document.getElementById('credit-percent').textContent = percent.toFixed(1) + '%';

  // 進度條
  document.getElementById('progress-fill').style.width = percent.toFixed(1) + '%';
  document.getElementById('progress-text').textContent = totalCompleted + ' / ' + totalRequired + ' 學分';

  // 分類表格
  const tbody = document.getElementById('credits-tbody');
  tbody.innerHTML = '';

  Object.keys(categories).forEach(function (name) {
    const category = categories[name];

    // 尚缺：達到要求或超過都是 0
    let categoryRemaining = category.required - category.completed;
    if (categoryRemaining < 0) {
      categoryRemaining = 0;
    }

    // 完成率：最多 100%
    let categoryPercent = (category.completed / category.required) * 100;
    if (categoryPercent > 100) {
      categoryPercent = 100;
    }

    const tr = document.createElement('tr');
    tr.appendChild(makeTd(name));
    tr.appendChild(makeTd(category.required));
    tr.appendChild(makeTd(category.completed));
    tr.appendChild(makeTd(categoryRemaining));
    tr.appendChild(makeTd(categoryPercent.toFixed(1) + '%'));

    tbody.appendChild(tr);
  });
}

// 建立一個簡單的表格儲存格
function makeTd(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}