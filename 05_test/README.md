# 🛒 Web Application with Full Testing Pipeline

一個包含完整自動化測試（單元測試、系統 API 測試、端到端 E2E 測試）的 Web 應用程式展示專案。

---

## 🛠 技術棧 (Tech Stack)

* **後端框架 (Backend)**: Node.js / Express
* **單元與 API 測試 (Unit & System Test)**: Jest, Supertest
* **端到端測試 (E2E Test)**: Playwright
* **開發環境 (Environment)**: Node.js v18+

---

## 📁 專案目錄結構 (Project Structure)

```text
05_test/
├── src/
│   ├── utils/
│   │   └── calculator.js      # 純邏輯函式 (單元測試目標)
│   ├── server.js               # Express Web API 伺服器 (系統測試目標)
│   └── public/
│       └── index.html          # 前端使用者介面 (E2E 測試目標)
├── tests/
│   ├── unit/
│   │   └── calculator.test.js  # 1. 單元測試 (Unit Test)
│   ├── api/
│   │   └── server.test.js      # 2. 系統 / API 測試 (System/API Test)
│   └── e2e/
│       └── app.spec.js         # 3. 端到端測試 (End-to-End Test)
├── package.json
└── README.md

```

---

## 🚀 快速開始 (Getting Started)

### 1. 安裝套件與測試環境

```bash
# 安裝專案依賴
npm install

# 安裝 Playwright 瀏覽器核心 (Chromium)
npx playwright install chromium

```

### 2. 啟動開發伺服器

```bash
npm start

```

伺服器啟動後，開啟瀏覽器造訪 `http://localhost:3000` 即可使用購物車應用。

---

## 🧪 自動化測試說明與執行 (Testing)

本專案實作了完整的三層測試金字塔架構：

### 1. 單元測試 (Unit Test)

針對商業邏輯與獨立函式（`src/utils/calculator.js`）進行純粹的單元驗證，確保計算邏輯精準。

```bash
npm run test:unit

```

### 2. 系統 / Web API 測試 (System Test)

使用 `Supertest` 模擬 HTTP 請求，直接對 Express 後端 API 進行整合測試，驗證 Endpoint 回應狀態碼與 JSON 格式。

```bash
npm run test:api

```

### 3. 端到端測試 (E2E Test)

使用 `Playwright` 啟動真實無頭瀏覽器（Headless Chrome），模擬真實使用者「開啟頁面 -> 點擊加入商品 -> 點擊結帳 -> 驗證 UI 金額顯示」的全流程。

> **註**：執行 E2E 測試前，請先確保開發伺服器已透過 `npm start` 啟動。

```bash
npm run test:e2e

```

---

## 📝 測試指令總覽 (npm scripts)

| 指令 | 說明 |
| --- | --- |
| `npm start` | 啟動 Express Web 伺服器 (Port 3000) |
| `npm run test:unit` | 執行 `tests/unit/` 下的單元測試 |
| `npm run test:api` | 執行 `tests/api/` 下的 Web API 系統測試 |
| `npm run test:e2e` | 執行 `tests/e2e/` 下的 Playwright 端到端測試 |
| `npm test` | 一鍵依序執行全套測試流程 |

```

<FollowUp label="需要幫你將 Playwright 設定成在執行 test:e2e 時自動啟動伺服器嗎？" query="請告訴我如何在 playwright.config.js 設定 webServer，讓它在執行 E2E 測試時自動啟動與關閉 Express 伺服器。"/>

```