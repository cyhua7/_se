# Bookmark Vault · Cloudflare 稍後閱讀收藏夾

一個部署在 Cloudflare 上的個人書籤／稍後閱讀應用，貼上網址就會自動抓取標題與描述、用 Workers AI 產生摘要與標籤，並把網頁封面圖快取到 R2。

## 使用到的 Cloudflare 服務

| 服務 | 用途 |
| --- | --- |
| Workers + Static Assets | 提供前端靜態檔案與 `/api/*` 後端 |
| D1 (SQLite) | 存放書籤、摘要、標籤、已讀／收藏狀態 |
| R2 | 快取網頁的 Open Graph 封面圖 |
| Workers AI | 自動產生摘要與 3–5 個標籤 |
| 選用：Secret | 以 `ACCESS_KEY` 保護私人收藏庫 |

## 功能

- 貼上網址即可收藏，自動抓取 `og:title`、描述、站名與封面圖
- Workers AI 產生 2–3 句摘要與主題標籤
- 封面圖下載後存入 R2，透過不可猜測的 key 提供
- 搜尋（標題／摘要／網址／備註）
- 標籤篩選、全部／未讀／已讀／收藏分頁
- 切換已讀、收藏、重新產生摘要、刪除
- 可選的存取金鑰保護（前端會提示輸入並存在 localStorage）
- 外部網站抓取失敗或 AI 暫時不可用時仍可收藏，並在 UI 顯示警告

## 專案結構

```
07_AC/
├─ src/
│  ├─ index.js      # Worker 進入點與 API 路由
│  └─ lib.js        # HTML metadata 解析、AI 輸出解析等純函式
├─ public/
│  ├─ index.html
│  ├─ styles.css
│  └─ app.js
├─ test/
│  └─ lib.test.js   # node:test 單元測試
├─ schema.sql       # D1 建表語法
├─ wrangler.toml
└─ package.json
```

## 本機開發

需求：Node.js 18+、Cloudflare 帳號（Workers AI 本機開發需要登入）。

```bash
cd 07_AC
npm install

# 建立本機 D1 資料表（使用 .wrangler/state，不會動到雲端）
npm run db:local

# 啟動本機 Worker（http://localhost:8787）
npm run dev
```

本機的 D1 與 R2 由 Wrangler 模擬，不需要先建立雲端資源。Workers AI 會走遠端，需要先 `npx wrangler login`；若未登入或沒有權限，收藏功能仍可用，只是不會有 AI 摘要。

### 選用：本機啟用存取金鑰

```bash
cp .dev.vars.example .dev.vars
# 編輯 .dev.vars，填入 ACCESS_KEY=你的金鑰
```

## 執行測試

```bash
npm test
```

測試涵蓋網址正規化、HTML metadata 解析、AI 回應 JSON 解析、標籤推導與資料列轉換。

## 部署到 Cloudflare

```bash
# 1. 登入
npx wrangler login

# 2. 建立 D1，記下輸出的 database_id
npx wrangler d1 create bookmark-db

# 3. 把 database_id 填進 wrangler.toml
#    [[d1_databases]]
#    database_id = "貼上真實 UUID"

# 4. 建立 R2 bucket
npx wrangler r2 bucket create bookmark-covers

# 5. 在雲端資料庫建表
npm run db:remote

# 6. 選用：設定存取金鑰（公開部署強烈建議）
npx wrangler secret put ACCESS_KEY

# 7. 部署
npm run deploy
```

部署完成後 Wrangler 會印出 `https://bookmark-vault.<你的子網域>.workers.dev`。

> 注意：`wrangler.toml` 內的 `database_id` 是預留值，只供本機開發使用；部署前一定要換成 `wrangler d1 create` 產生的真實 ID。

## API

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/api/bookmarks?q=&tag=&status=` | 列出書籤（status: `unread` / `read` / `favorite`） |
| POST | `/api/bookmarks` | 新增書籤 `{ "url": "...", "note": "..." }` |
| PATCH | `/api/bookmarks/:id` | 更新 `isRead` / `isFavorite` / `note` |
| DELETE | `/api/bookmarks/:id` | 刪除書籤與 R2 封面 |
| POST | `/api/bookmarks/:id/resummarize` | 重新抓取並產生摘要 |
| GET | `/api/tags` | 取得標籤與使用次數 |
| GET | `/api/covers/:key` | 讀取 R2 封面圖 |
| GET | `/api/health` | 健康檢查 |

若設定了 `ACCESS_KEY`，除了 `/api/health` 與 `/api/covers/*` 外，所有 API 都需要 `x-access-key` 標頭。

## 設計取捨

- **Worker + Static Assets**：比 Pages + Functions 少一層設定，`wrangler deploy` 一次同時部署前端與 API。
- **封面存 R2**：不直接熱連外部圖片，避免來源網站擋 `Referer` 或圖片消失；只接受 JPEG/PNG/WebP/GIF/AVIF，拒絕 SVG 以降低 XSS 風險。
- **AI 失敗可降級**：AI 或外部網頁抓取失敗時仍建立書籤，並用本地關鍵字推導標籤。
- **無框架前端**：單一 `app.js`，沒有建置步驟，方便閱讀與部署。
