// courses.js - 選課系統頁邏輯

// 目前登入的學生
const user = JSON.parse(sessionStorage.getItem('user'));

// 儲存課程資料
let coursesData = [];

if (user) {
  // 頁面載入時先讀一次課程資料
  loadCourses();
}

// 向伺服器取得課程與目前選課狀態
function loadCourses() {
  fetch('/api/courses?studentId=' + encodeURIComponent(user.studentId))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (!data.success) {
        document.getElementById('courses-message').textContent = data.message;
        return;
      }
      coursesData = data.courses;
      renderCourses();
    })
    .catch(function () {
      document.getElementById('courses-message').textContent = '讀取課程失敗，請確認伺服器有啟動';
    });
}

// 畫出課程表格與統計
function renderCourses() {
  updateSummary();
  buildTable();
}

// 更新「目前已選課程／學分」統計
function updateSummary() {
  let countCourse = 0;
  let countCredits = 0;

  coursesData.forEach(function (course) {
    if (course.isEnrolled) {
      countCourse = countCourse + 1;
      countCredits = countCredits + course.credits;
    }
  });

  document.getElementById('count-courses').textContent = countCourse;
  document.getElementById('count-credits').textContent = countCredits;
}

// 建立課程表格
function buildTable() {
  const tbody = document.getElementById('courses-tbody');
  tbody.innerHTML = '';

  coursesData.forEach(function (course) {
    const tr = document.createElement('tr');

    tr.appendChild(makeTd(course.courseId));
    tr.appendChild(makeTd(course.courseName));
    tr.appendChild(makeTd(course.credits));
    tr.appendChild(makeTd(course.teacher));
    tr.appendChild(makeTd(course.time));
    tr.appendChild(makeTd(course.classroom));

    // 狀態：額滿紅底、開放藍底
    const tdStatus = document.createElement('td');
    const statusTag = document.createElement('span');
    statusTag.textContent = course.status;
    if (course.isFull) {
      statusTag.classList.add('tag-full');
    } else {
      statusTag.classList.add('tag-open');
    }
    tdStatus.appendChild(statusTag);
    tr.appendChild(tdStatus);

    // 操作按鈕
    const tdAction = document.createElement('td');
    tdAction.appendChild(makeActionButton(course));
    tr.appendChild(tdAction);

    tbody.appendChild(tr);
  });
}

// 建立要放入表格的按鈕
function makeActionButton(course) {
  const button = document.createElement('button');

  // 已額滿：不能選
  if (course.isFull && !course.isEnrolled) {
    button.textContent = '已額滿';
    button.disabled = true;
    button.classList.add('btn-full');
    return button;
  }

  // 已選過：可以退選
  if (course.isEnrolled) {
    button.textContent = '退選';
    button.classList.add('btn-drop');
    button.onclick = function () { dropCourse(course); };
    return button;
  }

  // 一般：可以選課
  button.textContent = '選課';
  button.classList.add('btn-enroll');
  button.onclick = function () { enrollCourse(course); };
  return button;
}

// 選課
function enrollCourse(course) {
  fetch('/api/enroll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentId: user.studentId, courseId: course.courseId })
  })
    .then(function (response) { return response.json(); })
    .then(function (data) {
      // 顯示伺服器回傳的訊息（成功或失敗）
      document.getElementById('courses-message').textContent = data.message;
      if (data.success) {
        // 重新讀取課程資料，更新按鈕與統計
        loadCourses();
      }
    });
}

// 退選
function dropCourse(course) {
  fetch('/api/drop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentId: user.studentId, courseId: course.courseId })
  })
    .then(function (response) { return response.json(); })
    .then(function (data) {
      document.getElementById('courses-message').textContent = data.message;
      if (data.success) {
        loadCourses();
      }
    });
}

// 建立一個簡單的表格儲存格
function makeTd(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}