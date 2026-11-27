# 10_gemini-agent

以 Google Gemini API 示範最小可用的 Agent 迴圈：模型負責決定「要用哪個工具」，Python 程式負責真正執行工具，再把 observation 放回訊息歷史，讓模型繼續推理直到給出最終回覆。

本專案的重點不是聊天，而是把 LLM API 的 tool calling 流程落實成一個不會因網路或模型狀態無限期卡住的程式。

## Agent 迴圈是怎麼運作的

從 LLM API 的角度，一次 Agent 任務可拆成以下步驟：

1. 建立 `messages`，放入使用者需求。
2. 呼叫模型時同時註冊工具 schema。本範例註冊 `get_current_time` 與 `calculate_math`。
3. 模型可能有兩種回覆：
   - `function_calls`：要求程式代為執行工具。
   - 純文字：代表模型已完成任務。
4. 若在 Agent 端手動處理工具（本範例停用 `automatic_function_calling`），程式要依 `call.name` 與 `call.args` 呼叫本地函式。
5. 把工具結果包成 `types.Part.from_function_response(...)`，以 `role="user"` 追加回 `messages`。
6. 回到步驟 2，直到出現最終文字或達到 `AGENT_MAX_STEPS` 上限。

關鍵觀念：模型本身不會真的「計算」或「看時鐘」；它只會輸出結構化的工具呼叫意圖，真正的副作用與精確計算發生在我們的 Python 程式裡。

## 檔案說明

| 檔案 | 用途 |
| --- | --- |
| `agent_demo.py` | Agent 迴圈、工具實作、逾時/重試/模型備援、離線模擬模式 |
| `requirements.txt` | 唯一相依套件：`google-genai` |
| `.gitignore` | 忽略 `.env`、`__pycache__/`、`*.pyc` |
| `README.md` | 本說明與實測紀錄 |

## 安裝與執行

需求：Python 3.10+（程式碼使用 `tuple[str, ...]` 型別標註）。

```powershell
python -m pip install -r requirements.txt
```

### 設定 API Key（真實 API 模式）

在 PowerShell 設定環境變數：

```powershell
$env:GEMINI_API_KEY='你的金鑰'
python agent_demo.py
```

或在本資料夾（`agent_demo.py` 旁邊）建立 `.env`：

```text
GEMINI_API_KEY=你的金鑰
```

程式會優先讀取既有環境變數，再從腳本所在目錄讀 `.env`，因此不會因為從專案根目錄執行而找不到設定。`.env` 已被 git 忽略，請勿提交真實金鑰。

### 路徑注意事項

以下兩種方式都可以，程式不依賴目前工作目錄：

```powershell
python 10_gemini-agent/agent_demo.py
```

```powershell
cd 10_gemini-agent
python agent_demo.py
```

先前遇到過「從錯誤目錄執行导致相对路径找不到檔案」的問題，因此腳本使用 `Path(__file__).resolve().parent` 定位 `.env`。

### 只看 Agent 迴圈（離線模擬）

沒有 API Key 也能驗證完整工具呼叫流程：

```powershell
$env:AGENT_DEMO_MODE='offline'
python agent_demo.py
```

離線模式完全不送出網路請求，最終回覆會標示 `[離線模擬最終回覆]`，不會冒充真實模型輸出。

## 防止卡住與模型錯誤的設計

| 問題 | 處理方式 |
| --- | --- |
| 網路或伺服器無回應 | `types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)`，預設 15000 ms（SDK 的單位是毫秒） |
| 429 / 500 / 502 / 503 / 504 / timeout / 連線異常 | 同一模型最多重試 `GEMINI_RETRIES` 次，指數式等待 `GEMINI_BACKOFF_SECONDS * attempt` |
| 404 模型不存在或帳號無存取權 | 不盲目重試，直接切換下一個候選模型 |
| 400 / 401 / 403 | 視為設定錯誤，立即結束並顯示原因，不浪費時間換模型 |
| 所有模型都失敗 | 印出摘要後以非零 exit code 結束，不會無限迴圈 |
| 模型持續不回傳最終文字 | `AGENT_MAX_STEPS` 強制結束 |

預設模型順序：

1. `gemini-4-hydrogen`
2. `gemini-3.8-flash`
3. `gemini-3.6-flash`
4. `gemini-3.5-flash-lite`
5. `gemini-flash-latest`

依 Google 目前模型文件，Gemini 4 系列是新專案建議選項，`gemini-3.8-flash` 仍是可用的穩定模型；但 404 也可能是金鑰沒有該模型存取權，不一定代表模型名稱寫錯。可用環境變數覆蓋：

| 環境變數 | 預設值 | 說明 |
| --- | --- | --- |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | 無 | 二選一 |
| `GEMINI_MODEL` | 無 | 指定首選模型，後面仍接預設備援清單 |
| `GEMINI_MODELS` | 無 | 以逗號分隔自訂完整模型順序 |
| `GEMINI_TIMEOUT_MS` | `15000` | 單次 HTTP 請求逾時（毫秒） |
| `GEMINI_RETRIES` | `2` | 每個模型最多嘗試次數 |
| `GEMINI_BACKOFF_SECONDS` | `1.0` | 重試等待基準秒數 |
| `AGENT_MAX_STEPS` | `5` | Agent 迴圈最大輪數 |
| `AGENT_DEMO_MODE` | `api` | 設為 `offline` 或 `mock` 可離線驗證 |

另外，`calculate_math` 改用 `ast` 白名單運算，而不是直接 `eval` 任意字串，避免工具呼叫變成程式碼注入入口。

## 實測輸出紀錄

以下紀錄在 Windows PowerShell、`google-genai 3.6.1` 環境實際執行。為避免干擾，命令加上 `python -X utf8`；沒有使用或印出任何真實 API Key。

### 1. 語法檢查

```powershell
python -m py_compile agent_demo.py
```

```text
py_compile OK
```

### 2. 沒有 API Key 時直接執行

```powershell
python -X utf8 agent_demo.py
```

```text
[系統提示] 找不到 GEMINI_API_KEY / GOOGLE_API_KEY，已安全結束（未送出網路請求）。
  設定方式 A：$env:GEMINI_API_KEY='你的金鑰'; python agent_demo.py
  設定方式 B：在本檔同資料夾建立 .env，內容 GEMINI_API_KEY=你的金鑰
  只看 Agent 迴圈：$env:AGENT_DEMO_MODE='offline'; python agent_demo.py
exit_code=2
```

這代表未設定金鑰時會立即結束，不會卡在網路層等待。

### 3. 離線模式完整 Agent 迴圈

```powershell
$env:AGENT_DEMO_MODE='offline'
python -X utf8 agent_demo.py
```

```text
[系統提示] 離線模擬模式：不送出任何網路請求。
[設定] 單次請求逾時 15000 ms；每個模型最多 2 次；最多 5 輪。

[使用者任務] 現在幾點了？另外請幫我精確計算 (365 * 24) + 1280 等於多少？
==================================================

--- 第 1 輪迴圈 ---
[模型] 嘗試 offline-mock
[模型] 本次使用 offline-mock
[Agent 決策] 呼叫工具 -> get_current_time({})
[工具回傳結果] 2026-11-27 11:05:18
[Agent 決策] 呼叫工具 -> calculate_math({'expression': '(365 * 24) + 1280'})
[工具回傳結果] 10040

--- 第 2 輪迴圈 ---
[模型] 嘗試 offline-mock
[模型] 本次使用 offline-mock

[Agent 最終回覆]
[離線模擬最終回覆] 目前時間：2026-11-27 11:05:18；(365 * 24) + 1280 = 10040
==================================================
exit_code=0
```

時間會隨執行時刻不同；`(365 * 24) + 1280 = 10040` 是工具實際計算結果。這段證明「模型決策 → 工具執行 → 結果回灌 → 下一輪」的迴圈成立。

### 4. 以假用戶端驗證 404 換模型與 503 重試

這項測試直接替換 `client.models.generate_content`，不經過網路：第一個模型回 404，第二個模型第一次回 503、第二次成功。

```text
[模型] 嘗試 bad-model
[系統提示] 模型 bad-model 不存在或無存取權（404），切換下一個模型。
[模型] 嘗試 busy-model
[系統提示] busy-model 暫時失敗（503），0.0 秒後重試 2/2 ...
[模型] 本次使用 busy-model
calls: ['bad-model', 'busy-model', 'busy-model']
final text: ok
```

### 5. 真實 Gemini API 實測紀錄

以下是**真實 API 呼叫**的輸出，不是離線模擬。金鑰只從 Windows 使用者環境變數讀取後注入單一 PowerShell 命令，執行完立即清除；沒有建立 `.env`，也沒有把金鑰寫入任何檔案或輸出。

```powershell
$env:GEMINI_API_KEY=[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')
python -X utf8 agent_demo.py
Remove-Item Env:GEMINI_API_KEY
```

實際結果：

```text
[設定] 單次請求逾時 15000 ms；每個模型最多 2 次；最多 5 輪。

[使用者任務] 現在幾點了？另外請幫我精確計算 (365 * 24) + 1280 等於多少？
==================================================

--- 第 1 輪迴圈 ---
[模型] 嘗試 gemini-4-hydrogen
[系統提示] gemini-4-hydrogen 暫時失敗（503），1.0 秒後重試 2/2 ...
[系統提示] gemini-4-hydrogen 失敗：503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': '...，切換下一個模型。
[模型] 嘗試 gemini-3.8-flash
[系統提示] gemini-3.8-flash 暫時失敗（503），1.0 秒後重試 2/2 ...
[系統提示] gemini-3.8-flash 失敗：504 DEADLINE_EXCEEDED. {'error': {'code': 504, 'message': 'Deadline expired before operation could complete.', 'status': 'DEADLINE_EXCEEDED'}}，切換下一個模型。
[模型] 嘗試 gemini-3.6-flash
[系統提示] gemini-3.6-flash 暫時失敗（504），1.0 秒後重試 2/2 ...
[模型] 本次使用 gemini-3.6-flash
[Agent 決策] 呼叫工具 -> get_current_time({})
[工具回傳結果] 2026-11-27 11:16:33
[Agent 決策] 呼叫工具 -> calculate_math({'expression': '(365 * 24) + 1280'})
[工具回傳結果] 10040

--- 第 2 輪迴圈 ---
[模型] 嘗試 gemini-4-hydrogen
[模型] 本次使用 gemini-4-hydrogen

[Agent 最終回覆]
目前的時間是 **2026年11月27日 11:16:33**。

算式 `(365 * 24) + 1280` 的計算結果為 **10040**。
==================================================
exit_code=0
```

這一次同時驗證到的行為：

| 模型 | 實際狀況 | 程式處理 |
| --- | --- | --- |
| `gemini-4-hydrogen` | 第 1 輪兩次 503 | 重試後仍失敗，自動切換下一個模型 |
| `gemini-3.8-flash` | 先 503、再 504 | 重試後仍失敗，自動切換下一個模型 |
| `gemini-3.6-flash` | 第一次 504，第二次成功 | 完成兩個工具呼叫並回灌 observation |
| `gemini-4-hydrogen` | 第 2 輪恢復正常 | 成功產生最終文字回覆 |

因此沒有發生無限卡住；503/504 都在重試或換模型後被消化，最終仍完成 Agent 迴圈。時間與模型可用性會隨執行時刻不同，重跑時不一定會看到完全一樣的錯誤順序。

## 疑難排解

- **404**：確認模型名稱拼字，或改用 `GEMINI_MODELS` 指定帳號有權限的模型。
- **503 / 卡住**：降低 `GEMINI_TIMEOUT_MS`、提高 `GEMINI_RETRIES`，或暫時用 `AGENT_DEMO_MODE=offline` 確認是本機迴圈還是 API 問題。
- **401 / 403**：金鑰無效、過期或沒有模型存取權；重新產生金鑰，不要把金鑰寫進 README 或程式。
- **中文亂碼**：PowerShell 先執行 `[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`，並使用 `python -X utf8`。
- **找不到 `.env`**：確認檔案放在 `agent_demo.py` 同一層，或直接用環境變數設定。
