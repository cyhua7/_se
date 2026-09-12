// grades.js - 成績查詢頁邏輯

// 目前登入的學生
const user = JSON.parse(sessionStorage.getItem('user'));

// 儲存從伺服器拿到的成績資料
let gradesData = null;

if (user) {
  // 向伺服器取得目前學生的成績
  fetch('/api/grades?studentId=' + encodeURIComponent(user.studentId))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        // 伺服器回報錯誤
        document.getElementById('grades-message').textContent = data.message;
        return;
      }

      gradesData = data.semesters;

      // 依照資料建立學期選單
      const select = document.getElementById('semester-select');
      Object.keys(gradesData).forEach(function (semester) {
        const option = document.createElement('option');
        option.value = semester;
        option.textContent = semester;
        select.appendChild(option);
      });

      // 預設顯示第一個學期
      showSemester(select.value);
    })
    .catch(function () {
      document.getElementById('grades-message').textContent = '讀取成績失敗，請確認伺服器有啟動';
    });
}

// 學期選擇改變時，重新顯示該學期的成績
document.getElementById('semester-select').addEventListener('change', function () {
  showSemester(this.value);
});

// 顯示某一個學期的成績與統計
function showSemester(semester) {
  const courses = gradesData[semester];
  const message = document.getElementById('grades-message');
  const table = document.getElementById('grades-table');
  const summary = document.getElementById('grades-summary');
  const tbody = document.getElementById('grades-tbody');

  // 清空表格內容
  tbody.innerHTML = '';

  // 這個學期沒有課程（成績）
  if (!courses || courses.length === 0) {
    message.textContent = '此學期沒有成績資料';
    table.style.display = 'none';
    summary.style.display = 'none';
    return;
  }

  message.textContent = '';
  table.style.display = 'table';
  summary.style.display = 'block';

  let totalCredits = 0;   // 學分加總
  let totalScore = 0;     // 分數 × 學分的加總（算加權平均用）

  // 逐科填入表格
  courses.forEach(function (course) {
    const tr = document.createElement('tr');

    const tdId = document.createElement('td');
    tdId.textContent = course.courseId;

    const tdName = document.createElement('td');
    tdName.textContent = course.courseName;

    const tdCredits = document.createElement('td');
    tdCredits.textContent = course.credits;

    const tdScore = document.createElement('td');
    tdScore.textContent = course.score;
    // 不及格用紅色標示
    if (course.score < 60) {
      tdScore.classList.add('fail-score');
    }

    tr.appendChild(tdId);
    tr.appendChild(tdName);
    tr.appendChild(tdCredits);
    tr.appendChild(tdScore);
    tbody.appendChild(tr);

    totalCredits += course.credits;
    totalScore += course.score * course.credits;
  });

  // 計算並顯示統計（加權平均 = 分數×學分總和 ÷ 總學分）
  const average = totalScore / totalCredits;

  document.getElementById('total-credits').textContent = totalCredits;
  document.getElementById('average-score').textContent = average.toFixed(1);
}