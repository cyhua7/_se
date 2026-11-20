## 作業統整（01–08）

| 編號 | 資料夾 | 主題 | 主要技術 | 重點 | 連結 |
| :---: | --- | --- | --- | --- | --- |
| 01 | `01_curl` | mycurl：自製 HTTP 用戶端 | Python、requests、click | GET/POST 等方法、標頭、Cookie、檔案上傳、Proxy、TLS 選項 | [GitHub](https://github.com/cyhua7/_se/tree/main/01_curl) · [README](01_curl/README.md) |
| 02 | `02_school` | 金門大學校務系統模擬 | Node.js、Express、JSON、HTML/CSS/JS | 登入、成績、課表、選課、畢業學分、公告 | [GitHub](https://github.com/cyhua7/_se/tree/main/02_school) · [README](02_school/README.md) |
| 03 | `03_dup_cleaner` | 重複檔案與大檔案清理助手 | Python、Tkinter、hashlib | 大小分組 + MD5 比對、GUI 勾選、移到資源回收筒 | [GitHub](https://github.com/cyhua7/_se/tree/main/03_dup_cleaner) · [README](03_dup_cleaner/README.md) |
| 04 | `04_docker` | Docker 微服務建置 | Docker Compose、Nginx、FastAPI、PostgreSQL | 多容器架構、反向代理、Volume 與 Swagger 問題排除 | [GitHub](https://github.com/cyhua7/_se/tree/main/04_docker) · [README](04_docker/app/app/README.md) |
| 05 | `05_test` | 猜數字遊戲與自動化測試 | Jest、Supertest、Playwright、Express | 單元測試、API 測試、E2E 測試三層架構 | [GitHub](https://github.com/cyhua7/_se/tree/main/05_test) · [README](05_test/README.md) |
| 06 | `06_project` | Automation Workflow Manager | FastAPI、PostgreSQL、Docker Compose、nginx | 固定/動態任務、符號生成、訊息回顯、即時日誌與歷史 | [GitHub](https://github.com/cyhua7/_se/tree/main/06_project) · [README](06_project/README.md) |
| 07 | `07_AC` | Bookmark Vault 稍後閱讀收藏夾 | Cloudflare Workers、D1、KV、Workers AI | 自動抓 metadata、AI 摘要與標籤、封面快取、搜尋與篩選 | [GitHub](https://github.com/cyhua7/_se/tree/main/07_AC) · [README](07_AC/README.md) |
| 08 | `08_package` | `@cyhua7/bookmark-vault` CLI 套件 | npm CLI、Cloudflare Workers、Web Crypto | 註冊/登入/登出、Session、使用者隔離、SSRF 防護、專案模板 | [GitHub](https://github.com/cyhua7/_se/tree/main/08_package) · [README](08_package/README.md) |

## 各作業說明

### 01 — mycurl

- 安裝：`pip install -r 01_curl/requirements.txt`
- 使用：`python -m mycurl https://example.com`
- 支援 `-X`、`-H`、`-d`、`--json`、`-b`、`-u`、`-x`、`-T`、`-F`、`-k`、`--legacy`、`-v`、`-i`、`-o`、`-s`
- 測試：`python -m unittest discover -s tests -p "test_*.py" -v`（點擊距離與手動步驟見 [TESTING.md](01_curl/TESTING.md)）

### 02 — 校務系統模擬

- 啟動：`cd 02_school && npm install && npm start`，瀏覽 `http://localhost:3000`
- 測試帳號：`A10955001` / `123456`（陳小明）、`A10955002` / `123456`（林小美）
- 所有資料皆為模擬資料，非金門大學官方系統

### 03 — 重複檔案與大檔案清理助手

- 啟動：`python 03_dup_cleaner/main.py`，僅使用 Python 標準函式庫
- 流程：選資料夾 → 開始掃描 → 勾選重複檔案 → 清理選取檔案
- 先依檔案大小分組，再對同大小檔案算 MD5；清理是移到 Windows 資源回收筒，可還原

### 04 — Docker 微服務

- 啟動：`docker-compose up -d --build`，瀏覽 `http://localhost`，API 文件在 `http://localhost/api/docs`
- 三個服務：Nginx（80，反向代理）、FastAPI（8000）、PostgreSQL（Volume `postgres_data`）
- 權限指令差異、Volume 掛載衝突、Swagger 404 等排除記錄見 [README](04_docker/app/app/README.md)

### 05 — 猜數字遊戲與自動化測試

- 啟動：`cd 05_test && npm install && npx playwright install chromium && npm start`，瀏覽 `http://localhost:3000`
- 測試：`npm run test:unit`、`npm run test:api`、`npm run test:e2e`，或 `npm test` 執行全套
- E2E 會固定 `Math.random` 為 `0.42`（答案 43），並由 `playwright.config.js` 自動啟動伺服器

### 06 — Automation Workflow Manager

- 啟動：`Copy-Item .env.example .env`，再執行 `docker compose up -d --build`
- 服務：前端 `http://localhost:8080`、Swagger `http://localhost:8000/docs`、健康檢查 `/api/health`
- 提供 `POST /api/tasks/execute` 動態任務、符號生成、訊息回顯，以及 `task_runs` / `task_logs` 紀錄

### 07 — Bookmark Vault

- 線上版本：<https://bookmark-vault.cyhua7.workers.dev>（公開存取）
- 本機：`npm install`、`npm run db:local`、`npm run dev`（`http://localhost:8787`）、`npm test`
- 使用 D1 存書籤、KV 快取封面、Workers AI 產生摘要與標籤；AI 失敗時自動降級

### 08 — `@cyhua7/bookmark-vault`

- 產生專案：`npx @cyhua7/bookmark-vault my-bookmarks && cd my-bookmarks && npm install`
- 模板內建email/密碼註冊登入（PBKDF2-SHA256 100,000 次）、D1 Session、每位使用者獨立收藏庫
- 相較 07 增加身份驗證、cookie 安全設定與 SSRF 防護

## 補充

- 每週繳交狀態與週次對應請見 [mid.md](mid.md)（第 4 週為 git flow / github flow 操作，第 5 週放假，故沒有獨立資料夾）
- 本專案 GitHub：<https://github.com/cyhua7/_se>


