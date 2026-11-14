# @cyhua7/bookmark-vault

以 **Cloudflare Workers + D1 + KV + Workers AI** 打造的稍後閱讀收藏夾 scaffolding 工具，內建 **電子郵件／密碼註冊、登入、登出** 與每位使用者獨立的收藏庫。

## 快速開始

```bash
npx @cyhua7/bookmark-vault my-bookmarks
cd my-bookmarks
npm install
```

接著建立 Cloudflare 資源並部署：

```bash
npx wrangler login
npx wrangler d1 create bookmark-db
npx wrangler kv namespace create bookmark-covers
# 把輸出的 database_id 與 id 填進 wrangler.toml
npm run db:remote
npm run deploy
```

本機開發：

```bash
npm run db:local
npm run dev
```

## 功能

- 註冊／登入／登出，密碼以 **PBKDF2-SHA256（100,000 次迭代）** 加鹽雜湊
- Session 存於 D1，瀏覽器使用 `HttpOnly; SameSite=Lax` cookie
- 每位使用者只能看到自己的收藏（`bookmarks.user_id`）
- 貼上網址自動抓取 `og:title`、描述、站名與封面
- Workers AI 產生摘要與 3–5 個標籤，失敗時自動降級為本地關鍵字
- 封面圖快取到 Workers KV（可選 R2）
- 搜尋、標籤篩選、已讀／收藏切換、重新摘要、刪除

## 專案結構（產生的專案）

```
my-bookmarks/
├─ src/
│  ├─ index.js      # Worker 進入點、API 路由與權限檢查
│  ├─ auth.js       # 密碼雜湊、session、cookie 工具
│  └─ lib.js        # HTML metadata 解析、AI 輸出解析等純函式
├─ public/          # 無框架前端（index.html / app.js / styles.css）
├─ test/            # node:test 單元測試
├─ schema.sql       # users / sessions / bookmarks 建表語法
├─ wrangler.toml
└─ package.json
```

## API

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 註冊 `{ "email": "...", "password": "..." }` |
| POST | `/api/auth/login` | 登入，成功後設定 session cookie |
| POST | `/api/auth/logout` | 登出並清除 cookie |
| GET | `/api/auth/me` | 取得目前登入者（未登入回傳 `null`） |
| GET | `/api/bookmarks?q=&tag=&status=` | 列出目前使用者的收藏 |
| POST | `/api/bookmarks` | 新增收藏 `{ "url": "...", "note": "..." }` |
| PATCH | `/api/bookmarks/:id` | 更新已讀／收藏／備註 |
| DELETE | `/api/bookmarks/:id` | 刪除收藏與封面 |
| POST | `/api/bookmarks/:id/resummarize` | 重新產生摘要 |
| GET | `/api/tags` | 標籤與使用次數 |
| GET | `/api/covers/:key` | 讀取快取封面 |
| GET | `/api/health` | 健康檢查 |

除了 `/api/health`、`/api/covers/*` 與 `/api/auth/*`，其餘 API 都需要有效的登入 session。

## 安全性

- 密碼不落地明文，使用 Web Crypto 的 PBKDF2 雜湊
- Session token 只存雜湊值於 D1，cookie 為 `HttpOnly`、`SameSite=Lax`，HTTPS 下加上 `Secure`
- 所有收藏查詢都帶 `user_id` 條件，避免跨使用者存取
- 抓取外部網址前擋掉私有 IP／內部主機名稱（SSRF 防護）
- 封面只接受 JPEG/PNG/WebP/GIF/AVIF，拒絕 SVG

## 授權

MIT
