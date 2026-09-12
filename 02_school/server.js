// 國立金門大學學生校務系統（簡易版）
// server.js - Express 伺服器

const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// 讓伺服器可以讀取 POST 送過來的 JSON 資料
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// 將 public 資料夾設為靜態檔案資料夾
// 使用者可以直接在瀏覽器存取 public 裡面的檔案
app.use(express.static(path.join(__dirname, 'public')));

// 首頁：導向登入頁面
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 登入 API：檢查帳號密碼
app.post('/api/login', (req, res) => {
  const { studentId, password } = req.body;

  // 讀取使用者的資料檔案
  const users = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'users.json'), 'utf-8'));

  // 在陣列中尋找符合的學生
  const user = users.find(function (u) {
    return u.studentId === studentId && u.password === password;
  });

  // 找不到就回傳登入失敗
  if (!user) {
    return res.json({ success: false, message: '帳號或密碼錯誤' });
  }

  // 成功時回傳學生基本資料（不含密碼）
  res.json({
    success: true,
    message: '登入成功',
    user: {
      studentId: user.studentId,
      name: user.name,
      department: user.department,
      grade: user.grade,
      studentClass: user.studentClass,
      email: user.email,
      enrollmentYear: user.enrollmentYear,
      phone: user.phone || '',
      address: user.address || '',
      note: user.note || ''
    }
  });
});

// 成績查詢 API：依照學號回傳學生各學期的成績
app.get('/api/grades', (req, res) => {
  const studentId = req.query.studentId;

  // 沒有傳學號就回傳錯誤
  if (!studentId) {
    return res.json({ success: false, message: '缺少學號' });
  }

  // 讀取所有學生的成績資料
  const allGrades = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'grades.json'), 'utf-8'));

  // 找目前學生的成績（格式：{ "學期": [課程...] }）
  const semesters = allGrades[studentId];

  if (!semesters) {
    return res.json({ success: false, message: '查無此學生的成績資料' });
  }

  res.json({ success: true, semesters: semesters });
});

// 我的課表 API：依照學號回傳學生的課表
app.get('/api/schedule', (req, res) => {
  const studentId = req.query.studentId;

  if (!studentId) {
    return res.json({ success: false, message: '缺少學號' });
  }

  // 讀取所有學生的課表資料
  const allSchedules = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'schedule.json'), 'utf-8'));

  const courses = allSchedules[studentId];

  if (!courses) {
    return res.json({ success: false, message: '查無此學生的課表資料' });
  }

  res.json({ success: true, courses: courses });
});

// 選課系統 API
// ========================================

// 課程列表 API：依學號回傳所有課程，並標記該學生的選課狀態
app.get('/api/courses', (req, res) => {
  const studentId = req.query.studentId;

  if (!studentId) {
    return res.json({ success: false, message: '缺少學號' });
  }

  // 讀取課程與選課記錄
  const courses = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'courses.json'), 'utf-8'));
  const enrollments = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'enrollments.json'), 'utf-8'));

  // 目前這個學生的已選課號
  const myCourses = enrollments[studentId] || [];

  // 在每門課加上前端需要的狀態
  const result = courses.map(function (course) {
    return {
      courseId: course.courseId,
      courseName: course.courseName,
      credits: course.credits,
      teacher: course.teacher,
      time: course.time,
      classroom: course.classroom,
      department: course.department,
      status: course.status,
      maxStudents: course.maxStudents,
      enrolled: course.enrolled,
      isEnrolled: myCourses.indexOf(course.courseId) !== -1,
      isFull: course.enrolled >= course.maxStudents
    };
  });

  res.json({ success: true, courses: result, myCourseIds: myCourses });
});

// 選課 API
app.post('/api/enroll', (req, res) => {
  const { studentId, courseId } = req.body;

  // 檢查是否有送學號與課號
  if (!studentId || !courseId) {
    return res.json({ success: false, message: '缺少學號或課號' });
  }

  // 讀取三個資料檔
  const users = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'users.json'), 'utf-8'));
  const courses = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'courses.json'), 'utf-8'));
  const enrollments = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'enrollments.json'), 'utf-8'));

  // 檢查學生是否存在
  const user = users.find(function (u) { return u.studentId === studentId; });
  if (!user) {
    return res.json({ success: false, message: '查無此學生' });
  }

  // 檢查課程是否存在
  const course = courses.find(function (c) { return c.courseId === courseId; });
  if (!course) {
    return res.json({ success: false, message: '查無此課程' });
  }

  // 確保這個學生的選課清單存在
  if (!enrollments[studentId]) {
    enrollments[studentId] = [];
  }

  // 檢查是否已經選過
  if (enrollments[studentId].indexOf(courseId) !== -1) {
    return res.json({ success: false, message: '你已經選過這門課了' });
  }

  // 檢查課程是否額滿
  if (course.enrolled >= course.maxStudents) {
    return res.json({ success: false, message: '這門課已額滿，無法選課' });
  }

  // 選課：把課號加入學生的清單
  enrollments[studentId].push(courseId);

  // 選課人數 +1
  course.enrolled = course.enrolled + 1;

  // 把更新後的資料寫回檔案
  fs.writeFileSync(path.join(__dirname, 'data', 'enrollments.json'), JSON.stringify(enrollments, null, 2));
  fs.writeFileSync(path.join(__dirname, 'data', 'courses.json'), JSON.stringify(courses, null, 2));

  res.json({ success: true, message: '已成功選修：' + course.courseName });
});

// 退選 API
app.post('/api/drop', (req, res) => {
  const { studentId, courseId } = req.body;

  if (!studentId || !courseId) {
    return res.json({ success: false, message: '缺少學號或課號' });
  }

  const users = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'users.json'), 'utf-8'));
  const courses = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'courses.json'), 'utf-8'));
  const enrollments = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'enrollments.json'), 'utf-8'));

  // 檢查學生是否存在
  const user = users.find(function (u) { return u.studentId === studentId; });
  if (!user) {
    return res.json({ success: false, message: '查無此學生' });
  }

  // 檢查課程是否存在
  const course = courses.find(function (c) { return c.courseId === courseId; });
  if (!course) {
    return res.json({ success: false, message: '查無此課程' });
  }

  // 這個學生的已選清單
  const myCourses = enrollments[studentId] || [];

  // 檢查是否真的有選這門課
  const index = myCourses.indexOf(courseId);
  if (index === -1) {
    return res.json({ success: false, message: '你沒有選這門課，無法退選' });
  }

  // 退選：從清單移除課號
  myCourses.splice(index, 1);
  enrollments[studentId] = myCourses;

  // 選課人數 -1（最少不會低於 0）
  if (course.enrolled > 0) {
    course.enrolled = course.enrolled - 1;
  }

  // 把更新後的資料寫回檔案
  fs.writeFileSync(path.join(__dirname, 'data', 'enrollments.json'), JSON.stringify(enrollments, null, 2));
  fs.writeFileSync(path.join(__dirname, 'data', 'courses.json'), JSON.stringify(courses, null, 2));

  res.json({ success: true, message: '已退選：' + course.courseName });
});

// 畢業學分 API：依學號回傳學生的畢業學分資料
app.get('/api/graduation', (req, res) => {
  const studentId = req.query.studentId;

  // 檢查是否有學號
  if (!studentId) {
    return res.json({ success: false, message: '缺少學號' });
  }

  // 檢查學生是否存在
  const users = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'users.json'), 'utf-8'));
  const user = users.find(function (u) { return u.studentId === studentId; });
  if (!user) {
    return res.json({ success: false, message: '查無此學生' });
  }

  // 讀取畢業學分資料
  const graduation = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'graduation.json'), 'utf-8'));

  // 檢查是否有對應的畢業學分資料
  const data = graduation[studentId];
  if (!data) {
    return res.json({ success: false, message: '查無此學生的畢業學分資料' });
  }

  res.json({ success: true, graduation: data });
});

// 校務公告 API：回傳所有公告（不需要學號）
app.get('/api/announcements', (req, res) => {
  try {
    const announcements = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'announcements.json'), 'utf-8'));
    res.json({ success: true, announcements: announcements });
  } catch (error) {
    res.json({ success: false, message: '公告資料讀取失敗' });
  }
});

// 個人資料 API：依學號回傳學生個人資料
app.get('/api/profile', (req, res) => {
  const studentId = req.query.studentId;

  // 沒有傳學號就回傳錯誤
  if (!studentId) {
    return res.json({ success: false, message: '缺少學號' });
  }

  // 讀取所有使用者的資料
  const users = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'users.json'), 'utf-8'));

  // 尋找符合的學生
  const user = users.find(function (u) { return u.studentId === studentId; });

  if (!user) {
    return res.json({ success: false, message: '查無此學生' });
  }

  // 回傳個人資料（不含密碼）
  res.json({
    success: true,
    user: {
      studentId: user.studentId,
      name: user.name,
      department: user.department,
      grade: user.grade,
      studentClass: user.studentClass,
      email: user.email,
      enrollmentYear: user.enrollmentYear,
      phone: user.phone || '',
      address: user.address || '',
      note: user.note || ''
    }
  });
});

// 更新個人資料 API：只允許修改 Email、電話、聯絡地址、個人備註
app.put('/api/profile', (req, res) => {
  const { studentId, email, phone, address, note } = req.body;

  // 檢查是否有學號
  if (!studentId) {
    return res.status(400).json({ success: false, message: '缺少學號' });
  }

  const usersFile = path.join(__dirname, 'data', 'users.json');

  // 讀取所有使用者的資料
  const users = JSON.parse(fs.readFileSync(usersFile, 'utf-8'));

  // 檢查學生是否存在
  const user = users.find(function (u) { return u.studentId === studentId; });
  if (!user) {
    return res.status(404).json({ success: false, message: '查無此學生' });
  }

  // 檢查 Email 是否為合理格式
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (typeof email !== 'string' || !emailPattern.test(email.trim())) {
    return res.status(400).json({ success: false, message: 'Email 格式不正確' });
  }

  // 只更新可修改欄位（不改姓名、學號、系所、年級、班級、入學年度）
  user.email = email.trim();
  user.phone = (typeof phone === 'string' ? phone : '').trim();
  user.address = (typeof address === 'string' ? address : '').trim();
  user.note = (typeof note === 'string' ? note : '').trim();

  // 把更新後的資料寫回檔案
  fs.writeFileSync(usersFile, JSON.stringify(users, null, 2));

  res.json({
    success: true,
    message: '個人資料已更新',
    user: {
      email: user.email,
      phone: user.phone,
      address: user.address,
      note: user.note
    }
  });
});

// 啟動伺服器
app.listen(PORT, () => {
  console.log('校務系統已啟動：http://localhost:' + PORT);
});