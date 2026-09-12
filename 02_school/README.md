# 金門大學校務系統模擬專案

## 專案介紹

這是一個模擬大學校務系統的學生課程專案，以「國立金門大學學生校務系統（簡易版）」為藍本，實作學生常用的校務功能。

本專案為模擬系統，並非金門大學官方校務系統。所有學生、成績、課表、公告資料皆為模擬資料，僅供學習展示。

## 使用技術

- HTML
- CSS
- JavaScript
- Node.js
- Express
- JSON

## 系統功能

- 登入
- 首頁
- 個人資料
- 成績查詢
- 我的課表
- 選課系統
- 畢業學分
- 校務公告
- 登出
- 登入保護

## 專案結構

```
02_school/
├── server.js              # Express 伺服器與所有 API
├── package.json           # 專案設定與依賴
├── data/                  # 所有模擬資料（JSON）
│   ├── users.json         # 學生帳號資料
│   ├── grades.json        # 成績資料
│   ├── schedule.json      # 課表資料
│   ├── courses.json       # 課程清單與選課人數
│   ├── enrollments.json   # 學生選課記錄
│   ├── graduation.json    # 畢業學分規則
│   └── announcements.json # 校務公告
└── public/                # 前端頁面
    ├── index.html         # 登入頁
    ├── dashboard.html     # 系統首頁
    ├── profile.html       # 個人資料
    ├── grades.html        # 成績查詢
    ├── schedule.html      # 我的課表
    ├── courses.html       # 選課系統
    ├── credits.html       # 畢業學分
    ├── announcements.html # 校務公告
    ├── css/style.css      # 全站樣式
    └── js/                # 各頁面 JavaScript
```

## 安裝方式

```bash
npm install
```

## 啟動方式

```bash
npm start
```

啟動後開啟瀏覽器輸入：

```
http://localhost:3000
```

## 測試帳號

| 學號 | 密碼 | 姓名 |
|------|------|------|
| A10955001 | 123456 | 陳小明（資訊工程學系 二年級） |
| A10955002 | 123456 | 林小美（資訊工程學系 一年級） |

## 注意事項

- 本系統為模擬校務系統，並非金門大學官方校務系統
- 畢業學分資料為模擬資料
- 公告資料為模擬資料
- 成績、課表、選課資料皆為模擬，不代表金門大學實際校規或官方資料