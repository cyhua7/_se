# Automation Workflow Manager

Automation Workflow Manager（自動化任務管家）是一個以 FastAPI、PostgreSQL 與 Docker Compose 建立的任務管理範例專案。提供固定任務、動態任務、任意符號圖案生成、訊息回顯、即時日誌與執行歷史。

## 功能特色

- 一鍵執行固定任務：健康檢查、資料同步、檔案處理、E2E 測試
- 動態任務接收器：`POST /api/tasks/execute`
- 任意符號／圖案生成：透過 `symbol` 與 `count` 重複輸出
- 文字對話／訊息回顯：透過 `message` 將內容寫入日誌
- 任務執行紀錄與日誌寫入 PostgreSQL
- 前端即時日誌與歷史表格
- Task Registry 架構，易於新增自訂任務處理器
- Docker Compose 一鍵啟動
- 前端對動態內容進行 HTML escaping，降低 XSS 風險

## 技術棧

| 層級 | 技術 |
| --- | --- |
| Backend | Python 3.12, FastAPI 0.115.6, SQLAlchemy 2.0.36, Pydantic Settings 2.7.0 |
| Database | PostgreSQL 16 |
| Frontend | HTML, Tailwind CSS (CDN), Vanilla JavaScript |
| Web Server | nginx 1.27 |
| Container | Docker Compose |

## 專案結構

```text
06_project/
├─ backend/
│  ├─ app/
│  │  ├─ api/routes/
│  │  │  ├─ health.py
│  │  │  └─ tasks.py
│  │  ├─ core/config.py
│  │  ├─ db/
│  │  │  ├─ base.py
│  │  │  └─ session.py
│  │  ├─ models/
│  │  │  ├─ task_log.py
│  │  │  └─ task_run.py
│  │  ├─ schemas/task.py
│  │  ├─ services/
│  │  │  ├─ task_registry.py
│  │  │  └─ task_runner.py
│  │  └─ main.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ db/
│  ├─ init/001_schema.sql
│  └─ migrations/002_allow_dynamic_task_types.sql
├─ frontend/
│  ├─ css/styles.css
│  ├─ index.html
│  ├─ nginx.conf
│  └─ Dockerfile
├─ data/
│  ├─ processed/
│  └─ uploads/
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

## 快速啟動

### 前置需求

- Docker Desktop（Windows / macOS）或 Docker Engine + Docker Compose
- 可用連接埠：`8080`（前端）、`8000`（後端）、`5432`（PostgreSQL）
- 前端使用 Tailwind CSS CDN，首次載入需要網路

### 1. 建立環境變數

PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

必要時修改 `.env` 內的帳號、密碼與連接埠。

### 2. 啟動服務

```powershell
docker compose up -d --build
```

### 3. 確認狀態

```powershell
docker compose ps
```

正常情況下會看到：

- `awm-db`：healthy
- `awm-backend`：healthy
- `awm-frontend`：Up

### 4. 開啟服務

| 服務 | URL |
| --- | --- |
| 前端儀表板 | http://localhost:8080 |
| FastAPI Swagger UI | http://localhost:8000/docs |
| FastAPI ReDoc | http://localhost:8000/redoc |
| 健康檢查 | http://localhost:8000/api/health |

### 停止服務

```powershell
docker compose down
```

### 重置資料庫

以下指令會刪除 PostgreSQL volume，所有任務紀錄與日誌都會消失：

```powershell
docker compose down -v
```

## 環境變數

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `APP_ENV` | `development` | 執行環境名稱 |
| `POSTGRES_DB` | `workflow` | PostgreSQL 資料庫名稱 |
| `POSTGRES_USER` | `workflow` | PostgreSQL 使用者 |
| `POSTGRES_PASSWORD` | `workflow_dev_pw` | PostgreSQL 密碼（開發用） |
| `POSTGRES_PORT` | `5432` | 宿主機 PostgreSQL 連接埠 |
| `BACKEND_PORT` | `8000` | 宿主機後端連接埠 |
| `FRONTEND_PORT` | `8080` | 宿主機前端連接埠 |
| `DATABASE_URL` | `postgresql+psycopg://workflow:workflow_dev_pw@localhost:5432/workflow` | 在宿主機直接執行 backend 時使用 |

> Docker Compose 內的 backend 會使用 `postgresql+psycopg://...@db:5432/...` 連線到 `db` 服務，並覆寫 `.env` 中的 `DATABASE_URL`。

## API 一覽

Base URL：

- 直接呼叫 backend：`http://localhost:8000/api`
- 經前端 nginx proxy：`http://localhost:8080/api`

| Method | Path | 說明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康檢查（PostgreSQL + 磁碟） |
| `GET` | `/api/tasks/definitions` | 取得所有任務定義 |
| `GET` | `/api/tasks/history?skip=0&limit=10` | 取得任務歷史（`limit` 最大 100） |
| `POST` | `/api/tasks/health-check` | 執行健康檢查任務 |
| `POST` | `/api/tasks/sync` | 執行資料同步任務，可選擇帶入 `params` |
| `POST` | `/api/tasks/process-files` | 執行檔案批次處理任務 |
| `POST` | `/api/tasks/e2e-test` | 執行 E2E 整合測試任務 |
| `POST` | `/api/tasks/execute` | 動態任務接收器 |

`POST /api/tasks/sync` 可選擇帶入：

```json
{
  "params": {
    "source_url": "https://example.com/api",
    "mode": "full"
  }
}
```

## 任務定義

`GET /api/tasks/definitions` 目前回傳以下任務：

| 名稱 | 說明 | 範例參數 |
| --- | --- | --- |
| `health_check` | 系統健康檢查 | `{}` |
| `sync_data` | 資料同步 | `{"source_url": "https://example.com/api", "mode": "full"}` |
| `process_files` | 檔案批次處理 | `{"filename": "report_v1.csv", "rows": 250}` |
| `e2e_test` | E2E 整合測試 | `{}` |
| `symbol` | 符號圖案生成 | `{"symbol": "★", "count": 10}` |
| `echo` | 訊息回顯 | `{"message": "你好，世界！"}` |
| `對話` | 簡單對話 | `{"message": "你好"}` |
| `custom` | 通用自訂任務 | `{"key": "value"}` |

## 動態任務

### Request 格式

```json
{
  "task_name": "symbol",
  "params": {
    "symbol": "★",
    "count": 12
  }
}
```

- `task_name`：1–32 字元，支援英數、中文、符號與 emoji，不可包含控制字元
- `params`：任意 JSON 物件

### 符號／圖案生成

符號參數別名：

```text
symbol, pattern, emoji, icon, char, character, 圖案, 符號, 圖形
```

數量參數別名：

```text
count, repeat, times, length, 數量, 次數
```

範例：

```json
{
  "task_name": "symbol",
  "params": {
    "symbol": "♥",
    "count": 7
  }
}
```

日誌輸出：

```text
符號圖案生成：♥ x 7
♥♥♥♥♥♥♥
```

其他用法：

```json
{
  "task_name": "★",
  "params": {
    "count": 12
  }
}
```

```json
{
  "task_name": "abc",
  "params": {
    "count": 5
  }
}
```

第二個範例會輸出 `abcabcabcabcabc`。

規則：

- 若 `task_name` 是 `symbol`、`pattern`、`emoji`、`icon`、`符號`、`圖案`、`圖形`，未提供 `symbol` 時預設使用 `★`
- 若 `task_name` 是單一字元、emoji、或包含非英數符號（例如 `★`、`♥`、`#`），會直接將 `task_name` 當作圖案
- 若非對話任務、`task_name` 不是 `custom`，且有提供 `count`，也會將 `task_name` 當作圖案重複
- 預設 `count` 為 `10`
- `count` 上限為 `500`，超過會自動限制並在日誌留下 warning
- `symbol` 長度上限為 `32` 個字元
- 支援多字元圖案與複雜 emoji，例如 `★☆`、`👨‍👩‍👧‍👦`

### 對話／訊息回顯

訊息參數別名：

```text
message, msg, text, content, reply, say, prompt, question, 對話, 訊息, 內容
```

當 `task_name` 包含以下關鍵字時，也會被視為對話任務：

```text
對話, 聊天, 回顯, 訊息, dialog, echo, say, message, msg, talk, chat, reply
```

範例：

```json
{
  "task_name": "對話",
  "params": {
    "message": "你好，很高興見到你！"
  }
}
```

日誌輸出：

```text
收到訊息：你好，很高興見到你！
回顯：你好，很高興見到你！
```

其他行為：

- 若 `task_name` 是 `custom`，但 `params` 有 `message`，也會直接回顯
- 若對話任務沒有 `message`，會取非 symbol/count 的參數作為訊息；若有多個則以 JSON 形式回顯
- 若同時提供 `message` 與 `symbol`，會同時回顯並生成圖案，回傳 `mode` 為 `echo+symbol`
- 若沒有訊息也沒有圖案參數，會使用通用模式，將完整 `params` 寫入日誌

### 錯誤處理

- `count` 不是整數、小於 1、或 `symbol` 包含控制字元時，任務狀態會是 `failed`，並在 `error_message` 提供原因
- `count` 超過 500 時不會失敗，而是自動截斷並記錄 warning
- 未註冊的 `task_name` 不會執行任意程式碼，會使用通用處理器，依參數進行符號生成、訊息回顯或記錄 `params`

## 新增自訂任務

任務處理器集中在 `backend/app/services/task_registry.py`。新增任務時：

1. 建立 handler
2. 加入 `_TASK_DEFINITIONS`
3. 加入 `_TASK_HANDLERS`

範例：

```python
def my_task_handler(logger: LogCallback, params: dict[str, Any]) -> dict[str, Any]:
    logger("Running my custom task...")
    return {"ok": True, "params": params}


_TASK_DEFINITIONS["my_task"] = TaskDefinition(
    name="my_task",
    label="My Task",
    description="我的自訂任務。",
    params_hint={"foo": "bar"},
)

_TASK_HANDLERS["my_task"] = my_task_handler
```

變更後，開發環境的 uvicorn `--reload` 會自動載入。若是正式環境或修改了 `requirements.txt` / `Dockerfile`，請重新建置：

```powershell
docker compose up -d --build
```

## 資料庫

### 資料表

| 資料表 | 說明 |
| --- | --- |
| `task_runs` | 任務主記錄：狀態、進度、參數、結果、錯誤訊息、時間 |
| `task_logs` | 任務日誌：等級、訊息、context、時間 |

`task_runs` 與 `task_logs` 為一對多關聯，刪除 `task_runs` 時會連帶刪除 `task_logs`。

### 初始化與 Migration

- 全新資料庫：`db/init/001_schema.sql` 會在 PostgreSQL volume 首次建立時自動執行
- 既有資料庫：若曾經建立舊版 `task_runs_task_type_check` constraint，需手動套用：

```powershell
docker compose exec -T db psql -U workflow -d workflow `
  -c "ALTER TABLE task_runs DROP CONSTRAINT IF EXISTS task_runs_task_type_check;"
```

也可以使用 migration 檔案：

```powershell
Get-Content db/migrations/002_allow_dynamic_task_types.sql | docker compose exec -T db psql -U workflow -d workflow
```

進入 psql：

```powershell
docker compose exec db psql -U workflow -d workflow
```

## 快速驗證

以下為 PowerShell 範例。

健康檢查：

```powershell
Invoke-RestMethod "http://localhost:8000/api/health"
```

取得任務定義：

```powershell
Invoke-RestMethod "http://localhost:8080/api/tasks/definitions"
```

執行符號圖案生成：

```powershell
$body = @{
    task_name = "symbol"
    params = @{
        symbol = "★"
        count = 10
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8080/api/tasks/execute" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

執行對話回顯：

```powershell
$body = @{
    task_name = "對話"
    params = @{
        message = "你好，很高興見到你！"
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8080/api/tasks/execute" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

查看歷史：

```powershell
Invoke-RestMethod "http://localhost:8080/api/tasks/history?limit=5" |
    ConvertTo-Json -Depth 5
```

目前專案沒有內建自動化測試套件，以上指令可作為 API 冒煙測試。

## 開發注意事項

- `backend/app` 以 bind mount 掛載，uvicorn 使用 `--reload`，修改 Python 程式通常會自動重啟
- `frontend/index.html` 與 `frontend/css` 以 bind mount 掛載，修改前端檔案不需要重建 image
- 修改 `frontend/nginx.conf`、`frontend/Dockerfile`、`backend/Dockerfile` 或 `requirements.txt` 後需重新建置
- 請透過 nginx 的 `http://localhost:8080` 開啟前端，不要直接以 `file://` 開啟 `index.html`，否則 `/api` proxy 不會生效
- 前端使用 Tailwind CSS CDN；離線環境需自行改為本地建置
- `db/init` 只會在空 volume 首次啟動時執行；既有 volume 請手動套用 migration

## 安全性

- 動態任務採 handler registry 設計，不會執行任意 shell 指令或 `eval`
- 未註冊的任務名稱會走通用處理器，依參數進行符號生成、訊息回顯或記錄參數，不會執行任意程式碼
- 若要新增可執行外部程式的能力，請建立專用 handler，並自行加入嚴格的 allowlist、參數驗證與權限控管
- 前端日誌使用 `textContent` 輸出，動態任務名稱與歷史資料有 HTML escaping
- 預設資料庫密碼僅供開發使用，正式環境請務必修改
- 正式環境請調整 CORS 允許來源，不要長期開放所有 localhost 連接埠

## 常見問題

### 任務名稱寫入失敗，出現 `task_runs_task_type_check`

舊版資料庫仍有 `task_type` CHECK constraint。請套用 `db/migrations/002_allow_dynamic_task_types.sql`，或執行上面的 `ALTER TABLE` 指令。

### 前端修改沒有生效

`index.html` 與 CSS 是 bind mount，通常重新整理即可。若是修改 `nginx.conf` 或 Dockerfile，請執行：

```powershell
docker compose up -d --build
```

### 後端沒有自動重載

確認 backend 啟動指令包含 `--reload`，並檢查 `docker compose logs -f backend`。若修改了套件依賴，請重新建置。

### 連接埠被占用

修改 `.env` 內的 `FRONTEND_PORT`、`BACKEND_PORT` 或 `POSTGRES_PORT` 後重新啟動。

### PowerShell 傳送中文或 emoji 出現亂碼

請使用 UTF-8 bytes 作為 request body，例如：

```powershell
-Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```
