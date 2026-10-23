# 猜數字遊戲（Guessing Game）

一個以「猜數字」為主題的 Web 應用，同時示範完整的自動化測試流程：單元測試、系統 API 測試與端到端（E2E）測試。

系統會隨機產生一個 1 到 100 的整數。玩家每次輸入猜測後，畫面會提示「太大」或「太小」，並動態縮小可能的數字範圍，直到猜中為止。

---

## 功能特色

- 1 到 100 的隨機答案
- 每次猜錯後顯示目前可能範圍
- 即時顯示已猜次數
- 猜中時顯示正確答案
- 「新遊戲」可重置答案、次數與範圍
- 輸入非整數或超出 1 到 100 時顯示錯誤提示
- 深色漸層介面，支援桌面與手機畫面
- 三層自動化測試：Jest 單元測試、Supertest API 測試、Playwright E2E 測試

---

## 遊戲規則與範圍提示

1. 系統隨機產生 1 到 100 的整數作為答案。
2. 玩家輸入數字並按下「猜！」。
3. 若猜測小於答案，提示「太小了」，並將範圍下限更新為該次猜測。
4. 若猜測大於答案，提示「太大了」，並將範圍上限更新為該次猜測。
5. 若猜中，顯示「恭喜猜中！答案就是 X」。
6. 畫面上的「目前範圍」會同步顯示最新範圍，「已猜次數」會累加。

例如答案是 **42**，玩家輸入 **50** 後會顯示：

```text
太大了！數字在 1 ~ 50 之間
```

接著玩家輸入 **10**，則會顯示：

```text
太小了！數字在 10 ~ 50 之間
```

> 範圍提示由前端根據每次猜測動態計算，顯示的上下限包含該次猜測的數字。

---

## 技術棧

| 類別 | 技術 |
| --- | --- |
| 執行環境 | Node.js v18+ |
| 後端框架 | Express |
| 單元測試 | Jest |
| API 測試 | Jest + Supertest |
| E2E 測試 | Playwright |
| 前端 | HTML / CSS / Vanilla JavaScript |

---

## 專案結構

```text
05_test/
├── src/
│   ├── utils/
│   │   └── gameLogic.js        # 猜數字核心邏輯（單元測試目標）
│   ├── server.js               # Express 伺服器與 API（API 測試目標）
│   └── public/
│       └── index.html          # 遊戲介面（E2E 測試目標）
├── tests/
│   ├── unit/
│   │   └── gameLogic.test.js   # 單元測試
│   ├── api/
│   │   └── server.test.js      # 系統 / API 測試
│   └── e2e/
│       └── app.spec.js         # 端到端測試
├── playwright.config.js        # Playwright 設定（自動啟動伺服器）
├── package.json
└── README.md
```

---

## 快速開始

### 1. 安裝依賴

```bash
npm install
```

### 2. 安裝 Playwright 瀏覽器

```bash
npx playwright install chromium
```

### 3. 啟動伺服器

```bash
npm start
```

開啟瀏覽器造訪 `http://localhost:3000` 即可開始遊戲。

---

## API 說明

### `GET /api/health`

健康檢查。

回應：

```json
{ "status": "ok" }
```

### `GET /api/game/config`

取得遊戲的數字範圍。

回應：

```json
{ "min": 1, "max": 100 }
```

### `POST /api/guess`

送出一次猜測。

請求內容：

```json
{
  "secret": 42,
  "guess": 30
}
```

回應：

```json
{
  "result": "higher",
  "message": "太小了！再大一點"
}
```

`result` 的可能值：

| result | 意義 |
| --- | --- |
| `higher` | 猜測太小，答案比猜測大 |
| `lower` | 猜測太大，答案比猜測小 |
| `correct` | 猜中答案 |

若 `secret` 或 `guess` 不是 1 到 100 的整數，回傳 HTTP 400：

```json
{
  "error": "secret 與 guess 必須是 1 到 100 之間的整數"
}
```

> 本專案為測試流程展示，答案由前端產生並隨請求傳送。若要用於正式產品，應將答案保存在伺服器端，避免玩家直接得知答案。

---

## 核心邏輯

`src/utils/gameLogic.js` 提供以下函式：

| 函式 | 說明 |
| --- | --- |
| `validateGuess(guess)` | 驗證是否為 1 到 100 的整數 |
| `checkGuess(secret, guess)` | 比對答案與猜測，回傳 `higher`、`lower` 或 `correct` |
| `generateSecret(random)` | 產生 1 到 100 的隨機答案，可注入亂數函式以便測試 |

`checkGuess` 在收到非法數字時會拋出 `RangeError`。

---

## 自動化測試

本專案採用三層測試架構：

### 1. 單元測試

檔案：`tests/unit/gameLogic.test.js`

針對 `src/utils/gameLogic.js` 的純邏輯進行驗證，包含：

- 猜測太小回傳 `higher`
- 猜測太大回傳 `lower`
- 猜中回傳 `correct`
- 非法數字驗證
- 非法輸入拋出 `RangeError`
- `generateSecret` 產生範圍內的整數

執行：

```bash
npm run test:unit
```

### 2. 系統 / API 測試

檔案：`tests/api/server.test.js`

使用 Supertest 直接對 Express 應用程式發出 HTTP 請求，驗證：

- `GET /api/health` 回應狀態與內容
- `GET /api/game/config` 回傳正確範圍
- `POST /api/guess` 的 `correct`、`higher`、`lower` 情境
- 缺少參數或超出範圍時回傳 HTTP 400

執行：

```bash
npm run test:api
```

### 3. 端到端測試

檔案：`tests/e2e/app.spec.js`

使用 Playwright 啟動無頭 Chromium 瀏覽器，模擬真實使用者操作。測試會先將 `Math.random` 固定為 `0.42`，使答案固定為 **43**，確保結果可重現。

目前涵蓋以下情境：

1. **逐步猜中答案**
   - 輸入 50，驗證提示「太大了！數字在 1 ~ 50 之間」與範圍顯示
   - 輸入 10，驗證提示「太小了！數字在 10 ~ 50 之間」與範圍顯示
   - 輸入 43，驗證「恭喜猜中！答案就是 43」與已猜次數為 3
2. **新遊戲重置**
   - 猜中後按下「新遊戲」，驗證提示、次數與範圍都回到初始狀態
3. **範圍外輸入**
   - 輸入 150，驗證顯示「請輸入 1 到 100 的整數」

`playwright.config.js` 已設定 `webServer`，執行 E2E 測試時會自動啟動與關閉 Express 伺服器，不需要手動執行 `npm start`。

執行：

```bash
npm run test:e2e
```

---

## npm 指令總覽

| 指令 | 說明 |
| --- | --- |
| `npm start` | 啟動 Express 伺服器（Port 3000） |
| `npm run test:unit` | 執行單元測試 |
| `npm run test:api` | 執行系統 / API 測試 |
| `npm run test:e2e` | 執行 Playwright 端到端測試 |
| `npm test` | 依序執行單元、API、E2E 全套測試 |
