// schedule.js - 我的課表頁邏輯

// 目前登入的學生
const user = JSON.parse(sessionStorage.getItem('user'));

// 星期與節次順序
const days = ['星期一', '星期二', '星期三', '星期四', '星期五'];
const periods = [1, 2, 3, 4, 5, 6, 7, 8];

if (user) {
  // 向伺服器取得目前學生的課表
  fetch('/api/schedule?studentId=' + encodeURIComponent(user.studentId))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        document.getElementById('schedule-message').textContent = data.message;
        return;
      }
      buildScheduleTable(data.courses);
    })
    .catch(function () {
      document.getElementById('schedule-message').textContent = '讀取課表失敗，請確認伺服器有啟動';
    });
}

// 依照課程資料畫出星期 × 節次的表格
function buildScheduleTable(courses) {
  const table = document.getElementById('schedule-table');

  // 建立對照表：key 是「星期-節次」，例如「星期一-3」
  // 這樣放課程進格子時可以直接找到位置
  const grid = {};
  courses.forEach(function (course) {
    const key = course.day + '-' + course.period;
    grid[key] = course;
  });

  // 第一列：時間 + 星期
  let html = '<tr><th>時間</th>';
  days.forEach(function (day) {
    html += '<th>' + day + '</th>';
  });
  html += '</tr>';

  // 每一節一列
  periods.forEach(function (period) {
    html += '<tr><th>第' + period + '節</th>';

    days.forEach(function (day) {
      const course = grid[day + '-' + period];

      if (course) {
        // 有課：顯示課程名稱、教室、教師
        html += '<td class="schedule-cell">' +
          '<span class="course-name">' + course.courseName + '</span>' +
          '<span class="course-room">' + course.classroom + '</span>' +
          '<span class="course-teacher">' + course.teacher + '</span>' +
          '</td>';
      } else {
        // 沒課：空的格子
        html += '<td></td>';
      }
    });

    html += '</tr>';
  });

  table.innerHTML = html;
}