# Docker 微服務建置記錄與系統說明

本專案使用 Docker 與 Docker Compose 建立一套多容器（Microservices）架構的 Web 系統。

---

## 🏗️ 系統微服務架構

本系統由三個主要服務組成：

1. **Nginx (Web Server & Reverse Proxy)**
   * 對外監聽 Port `80`。
   * 負責提供靜態 Web 介面 (`http://localhost`)。
   * 將 `/api/` 請求反向代理轉發給 Python 後端服務。
2. **Backend (Python FastAPI)**
   * 執行於 Python 3.11 環境。
   * 提供 RESTful API，並處理資料庫連線邏輯。
   * 提供 Swagger API 文件頁面 (`http://localhost/api/docs`)。
3. **Database (PostgreSQL)**
   * 負責資料持久化儲存，使用 Docker Volume (`postgres_data`) 掛載資料。

---

## 🛠️ 啟動與執行方式

### 1. 啟動所有微服務
在 Windows PowerShell 或終端機中執行：
```powershell
docker-compose up -d --build
```

### 2. 存取系統與服務測試

* **Web 展示介面**：瀏覽器開啟 `http://localhost`
* **API 文件頁面 (Swagger UI)**：瀏覽器開啟 `http://localhost/api/docs`

### 3. 停止與清理容器

```powershell
docker-compose down

```

---

## 📝 Docker 學習記錄與問題排除 (Troubleshooting)

### 1. Windows 與 Linux/Mac 環境權限指令差異

* **問題**：在 Windows PowerShell 執行 `chmod +x *.sh` 會提示 `CommandNotFoundException`。
* **原因**：`chmod` 為 Linux/Unix 專屬指令，Windows 原生 PowerShell 無法辨識。
* **解決**：Windows 環境上記錄 `.sh` 執行權限可透由 `git update-index --chmod=+x filename.sh` 或改在 Git Bash 中執行。

### 2. Volume 掛載類型衝突 (Directory vs File)

* **問題**：`docker-compose up` 時跳出 `runc create failed: ... not a directory: Are you trying to mount a directory onto a file?` 錯誤。
* **原因**：`docker-compose.yml` 將 `./app/index.html` 掛載為檔案，但本機當時尚未建立該檔案，導致 Docker 自動建立了同名的 `index.html` 資料夾。
* **解決**：刪除本機的 `index.html` 資料夾，並重新建立真正的 `index.html` 檔案後重新啟動。

### 3. Nginx 反向代理下 FastAPI Swagger UI 404 錯誤

* **問題**：開啟 `http://localhost/api/docs` 時顯示 `Fetch error Not Found /openapi.json`。
* **原因**：Swagger UI 預設會往網域根目錄 `/openapi.json` 抓取 API 規格，而在 Nginx 反向代理架構下，該請求並未經過 `/api/` 轉發。
* **解決**：
1. 在 FastAPI 中設定 `app = FastAPI(root_path="/api")` 明確告訴後端其基底路徑。
2. 在 `nginx.conf` 中將 `proxy_pass` 設定為 `http://backend:8000`（不帶結尾斜線），確保完整傳遞子路徑。
