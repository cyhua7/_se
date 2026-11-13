# Bookmark Vault · Cloudflare 稍後閱讀收藏夾

一個部署在 Cloudflare 上的個人書籤／稍後閱讀應用，支援**註冊、登入、登出**。貼上網址就會自動抓取標題與描述、用 Workers AI 產生摘要與標籤，並把網頁封面圖快取到 Workers KV。每位使用者的收藏彼此隔離。

## 使用到的 Cloudflare 服務

| 服務 | 用途 |
| --- | --- |
| Workers + Static Assets | 提供前端靜態檔案與 `/api/*` 後端 |
| D1 (SQLite) | 存放使用者、session、書籤、摘要、標籤與狀態 |
| Workers KV | 快取網頁的 Open Graph 封面圖（免費、免綁卡） |
| Workers AI | 自動產生摘要與 3–5 個標籤 |

## 功能

- 電子郵件＋密碼註冊、登入、登出
- 每位使用者只會看到自己的收藏
- 貼上網址即可收藏，自動抓取 `og:title`、描述、站名與封面圖
- Workers AI 產生 2–3 句摘要與主題標籤
- 封面圖下載後存入 Workers KV，透過不可猜測的 key 提供
- 搜尋（標題／摘要／網址／備註）
- 標籤篩選、全部／未讀／已讀／收藏分頁
- 切換已讀、收藏、重新產生摘要、刪除
- 外部網站抓取失敗或 AI 暫時不可用時仍可收藏，並在 UI 顯示警告

## 專案結構

```
.
├─ src/
│  ├─ index.js      # Worker 進入點與 API 路由
│  ├─ auth.js       # 密碼雜湊、session 與 cookie 工具
│  └─ lib.js        # HTML metadata 解析、AI 輸出解析等純函式
├─ public/
│  ├─ index.html
│  ├─ styles.css
│  └─ app.js
├─ test/
│  ├─ lib.test.js
│  └─ auth.test.js
├─ schema.sql       # users / sessions / bookmarks 建表語法
├─ wrangler.toml
└─ package.json
```

## 本機開發

需求：Node.js 22+、Cloudflare 帳號。

```bash
npm install

# 建立本機 D1 資料表（使用 .wrangler/state，不會動到雲端）
npm run db:local

# 啟動本機 Worker（http://localhost:8787）
npm run dev
```

本機的 D1 與 KV 由 Wrangler 模擬，不需要先建立雲端資源。Workers AI 沒有本機模擬，`wrangler.toml` 已設定 `remote = true`，因此本機新增書籤時仍會連到 Cloudflare 產生摘要（需登入）；若未登入或 AI 失敗，會自動改用本地關鍵字推導標籤。

## 執行測試

```bash
npm test
```

測試涵蓋網址正規化、HTML metadata 解析、AI 回應解析、標籤推導、密碼雜湊驗證與 cookie 工具。

## 部署到 Cloudflare

```bash
# 1. 登入
npx wrangler login

# 2. 建立 D1，記下輸出的 database_id
npx wrangler d1 create bookmark-db
# 把 database_id 填進 wrangler.toml

# 3. 建立 KV namespace，記下輸出的 id
npx wrangler kv namespace create bookmark-covers
# 把 id 填進 wrangler.toml

# 4. 在雲端資料庫建表
npm run db:remote

# 5. 部署
npm run deploy
```

部署完成後 Wrangler 會印出 `https://<你的專案名>.<你的子網域>.workers.dev`，開啟後即可註冊第一個帳號。

## API

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 註冊 `{ "email": "...", "password": "..." }` |
| POST | `/api/auth/login` | 登入，成功後設定 session cookie |
| POST | `/api/auth/logout` | 登出並清除 cookie |
| GET | `/api/auth/me` | 取得目前登入者 |
| GET | `/api/bookmarks?q=&tag=&status=` | 列出收藏 |
| POST | `/api/bookmarks` | 新增書籤 `{ "url": "...", "note": "..." }` |
| PATCH | `/api/bookmarks/:id` | 更新 `isRead` / `isFavorite` / `note` |
| DELETE | `/api/bookmarks/:id` | 刪除書籤與封面 |
| POST | `/api/bookmarks/:id/resummarize` | 重新抓取並產生摘要 |
| GET | `/api/tags` | 取得標籤與使用次數 |
| GET | `/api/covers/:key` | 讀取快取封面圖 |
| GET | `/api/health` | 健康檢查 |

## 安全性設計

- 密碼以 **PBKDF2-SHA256（100,000 次迭代）** 加隨機鹽雜湊，不儲存明文
- Session token 只把 SHA-256 雜湊存進 D1；cookie 使用 `HttpOnly`、`SameSite=Lax`，HTTPS 時加上 `Secure`
- 書籤查詢一律附加 `user_id`，避免跨使用者讀寫
- 抓取外部網址與封面前會阻擋私有 IP 與內部主機名稱
- 封面只接受 JPEG/PNG/WebP/GIF/AVIF，拒絕 SVG 以降低 XSS 風險

## 授權

MIT
