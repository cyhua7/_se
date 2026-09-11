# mycurl 測試教學

一步一步測試 mycurl 的方法。所有指令都在專案目錄執行：

```powershell
cd C:\cyh\_se\git_se\_se\01_curl
```

## 1. 環境準備

確認 Python 和套件已安裝：

```powershell
python --version        # 應顯示 Python 3.12.10
pip list                # 應看到 click 8.5.0 和 requests 2.34.2
```

### 若找不到 pip / python 指向微軟商店

- 方法 A：關掉所有終端，開一個全新的 PowerShell。
- 方法 B：在目前視窗手動載入 PATH：

```powershell
$env:Path = "C:\Users\User\AppData\Local\Programs\Python\Python312;C:\Users\User\AppData\Local\Programs\Python\Python312\Scripts;$env:Path"
```

## 2. 自動化測試

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

預期（需要連網）：

```
test_custom_headers ... ok
test_get_request ... ok
test_json_request ... ok
test_post_request ... ok
test_status_code ... ok

----------------------------------------------------------------------
Ran 5 tests in 5.xxx s

OK
```

## 3. 手動測試

後續測試用 https://httpbin.org 這個網站驗證，它會回傳伺服器收到的請求內容。

### 步驟 1：基本 GET

```powershell
python -m mycurl https://httpbin.org/get
```

驗證：看到包含 `headers`、`origin`、`url` 的 JSON。

### 步驟 2：POST 資料 + 自訂標頭

```powershell
python -m mycurl -X POST -d "name=test&value=123" -H "X-Custom: hello" https://httpbin.org/post
```

驗證：`"form"` 顯示 `name: test, value: 123`，`"headers"` 有 `"X-Custom": "hello"`。

### 步驟 3：JSON 請求

```powershell
python -m mycurl --json '{\"key\":\"value\",\"num\":42}' -X POST https://httpbin.org/post
```

驗證：`Content-Type` 是 `application/json`，`"json"` 欄位正確解析。

> **PowerShell 引號坑**：PowerShell 5.1 會剝掉單引號內的雙引號，所以內層雙引號要用反斜線跳脫 `\"`。直接寫 `'{"key":"value"}'` 會出現 `Error: Invalid JSON data`。

### 步驟 4：發送 Cookie

```powershell
python -m mycurl -b "session=abc123" https://httpbin.org/cookies
```

驗證：`"cookies"` 欄位顯示 `{"session": "abc123"}`。

### 步驟 5：詳細模式 + 自訂 User-Agent

```powershell
python -m mycurl -v -A "MyAgent/1.0" https://httpbin.org/get
```

驗證：看到以 `*`、`>` 開頭的請求明細，且 `User-Agent` 是 `MyAgent/1.0`。

### 步驟 6：顯示回應標頭

```powershell
python -m mycurl -i https://httpbin.org/get
```

驗證：`Date`、`Content-Type`、`Server` 等回應標頭顯示在 body 前面。

### 步驟 7：重定向 + 自訂輸出格式

```powershell
python -m mycurl -L -w "code=%{http_code} url=%{url_effective} time=%{time_total}" http://httpbin.org/redirect-to?url=http://example.com
```

驗證：看到 example.com 的 HTML，結尾出現 `code=200 url=http://example.com ...`。

### 步驟 8：存檔

```powershell
python -m mycurl -o out.html https://example.com
Get-Content out.html
```

驗證：`out.html` 內容是 example.com 的 HTML。

### 步驟 9：錯誤狀態碼

```powershell
python -m mycurl https://httpbin.org/status/404
echo $LASTEXITCODE
```

驗證：`$LASTEXITCODE` 顯示 `1`（工具對 4xx/5xx 回傳失敗退出碼）。

### 步驟 10：舊 TLS 網站（--legacy）

老舊伺服器（如學校網頁）使用舊版 TLS 重新協商，會出現錯誤：
`SSLError: [SSL: UNSAFE_LEGACY_RENEGOTIATION_DISABLED]`。

解決：加 `--legacy` 允許舊 TLS 相容：

```powershell
mycurl --legacy https://select.nqu.edu.tw/
```

注意：這類網站通常需要登入（Cookie），並有防爬蟲機制，狀態碼 200 代表連線成功。

## 4. 查看完整說明

```powershell
python -m mycurl --help
python -m mycurl --version
```