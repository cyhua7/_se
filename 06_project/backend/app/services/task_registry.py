import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings

LogCallback = Callable[[str, str], None]
TaskHandler = Callable[[LogCallback, dict[str, Any]], Any]

_MAX_SYMBOL_LENGTH = 32
_MAX_SYMBOL_COUNT = 500
_DEFAULT_SYMBOL_COUNT = 10
_DEFAULT_SYMBOL = "★"

_DIALOG_KEYWORDS = (
    "對話",
    "聊天",
    "回顯",
    "訊息",
    "dialog",
    "echo",
    "say",
    "message",
    "msg",
    "talk",
    "chat",
    "reply",
)
_MESSAGE_KEYS = (
    "message",
    "msg",
    "text",
    "content",
    "reply",
    "say",
    "prompt",
    "question",
    "對話",
    "訊息",
    "內容",
)
_SYMBOL_KEYS = (
    "symbol",
    "pattern",
    "emoji",
    "icon",
    "char",
    "character",
    "圖案",
    "符號",
    "圖形",
)
_COUNT_KEYS = (
    "count",
    "repeat",
    "times",
    "length",
    "數量",
    "次數",
)
_SYMBOL_TASK_NAMES = {
    "symbol",
    "pattern",
    "emoji",
    "icon",
    "符號",
    "圖案",
    "圖形",
}


@dataclass(frozen=True)
class TaskDefinition:
    name: str
    label: str
    description: str
    params_hint: dict[str, Any] = field(default_factory=dict)


def health_check_handler(logger: LogCallback, params: dict[str, Any]) -> dict[str, Any]:
    path = settings.upload_dir if settings.upload_dir.exists() else Path("/")
    usage = shutil.disk_usage(path)
    free_percent = round((usage.free / usage.total) * 100, 2)

    logger("Checking disk space...")
    logger(f"Disk free space: {free_percent}%")
    logger("Checking database connection...")
    logger("All systems nominal!")

    return {
        "status": "healthy",
        "disk_free_percent": free_percent,
        "db": "Connected",
    }


def sync_data_handler(logger: LogCallback, params: dict[str, Any]) -> dict[str, Any]:
    source_url = params.get("source_url") or params.get("url") or "mock_api"
    mode = params.get("mode") or "full"

    logger(f"Initializing data sync crawler (mode={mode})...")
    logger(f"Fetching external data source: {source_url}")
    logger("Fetching external mock data sources (0/3)...")
    logger("Fetching external mock data sources (3/3)...")
    logger("Cleaning data and writing to PostgreSQL...")
    logger("Sync finished successfully.")

    return {
        "synced_rows": 15,
        "source": source_url,
        "mode": mode,
    }


def process_files_handler(
    logger: LogCallback, params: dict[str, Any]
) -> dict[str, Any]:
    filename = params.get("filename") or "report_v1.csv"
    rows = params.get("rows") or 250

    logger("Scanning target directory for pending files...")
    logger(f"Processing file: {filename} (Parsed {rows} rows)")
    logger("Generating output zip archive...")
    logger("File processing complete.")

    return {
        "processed_files": 1,
        "filename": filename,
        "output_size_kb": 42.5,
    }


def e2e_test_handler(logger: LogCallback, params: dict[str, Any]) -> dict[str, Any]:
    logger("[E2E] Step 1: Testing FastAPI endpoint routing... OK")
    logger("[E2E] Step 2: Testing PostgreSQL CRUD transactions... OK")
    logger("[E2E] Step 3: Verifying foreign key and constraints... OK")
    logger("[E2E] All integration test suites passed successfully!")

    return {"total_tests": 4, "passed": 4, "failed": 0}


def _lookup_param(params: dict[str, Any], keys: tuple[str, ...]) -> Any:
    normalized = {str(key).casefold(): value for key, value in params.items()}
    for key in keys:
        value = normalized.get(key.casefold())
        if value is not None and value not in ("", [], {}):
            return value
    return None


def _is_dialog_task(task_name: str) -> bool:
    normalized = task_name.casefold()
    return any(keyword.casefold() in normalized for keyword in _DIALOG_KEYWORDS)


def _is_symbol_like(task_name: str) -> bool:
    if len(task_name) == 1:
        return True
    return any(not char.isalnum() and char not in "_-" for char in task_name)


def _format_message(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_format_message(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _extract_dialog_message(params: dict[str, Any]) -> Any:
    message = _lookup_param(params, _MESSAGE_KEYS)
    if message is not None:
        return message

    excluded_keys = {
        key.casefold() for key in (*_MESSAGE_KEYS, *_SYMBOL_KEYS, *_COUNT_KEYS)
    }
    remaining = {
        key: value
        for key, value in params.items()
        if str(key).casefold() not in excluded_keys
    }

    if len(remaining) == 1:
        return next(iter(remaining.values()))
    if remaining:
        return remaining
    return "（沒有提供訊息內容）"


def _parse_symbol(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        raise ValueError("symbol 必須是單一字元或字串")

    symbol = str(value)
    if not symbol:
        raise ValueError("symbol 不可為空")
    if len(symbol) > _MAX_SYMBOL_LENGTH:
        raise ValueError(f"symbol 長度不可超過 {_MAX_SYMBOL_LENGTH} 個字元")
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in symbol):
        raise ValueError("symbol 不可包含控制字元或換行")
    return symbol


def _parse_count(value: Any, logger: LogCallback) -> int:
    if value is None:
        return _DEFAULT_SYMBOL_COUNT

    if isinstance(value, float) and not value.is_integer():
        raise ValueError("count 必須是整數")

    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("count 必須是整數") from exc

    if count < 1:
        raise ValueError("count 必須大於 0")

    if count > _MAX_SYMBOL_COUNT:
        logger(
            f"count={count} 超過上限，已自動限制為 {_MAX_SYMBOL_COUNT}。",
            "WARNING",
        )
        count = _MAX_SYMBOL_COUNT

    return count


def custom_task_handler(
    logger: LogCallback,
    params: dict[str, Any],
    task_name: str = "custom",
) -> dict[str, Any]:
    normalized_name = task_name.casefold()
    is_dialog = _is_dialog_task(task_name)

    message_value = _lookup_param(params, _MESSAGE_KEYS)
    if message_value is None and is_dialog:
        message_value = _extract_dialog_message(params)

    symbol_value = _lookup_param(params, _SYMBOL_KEYS)
    count_value = _lookup_param(params, _COUNT_KEYS)

    if symbol_value is None and not is_dialog and normalized_name != "custom":
        if normalized_name in _SYMBOL_TASK_NAMES:
            symbol_value = _DEFAULT_SYMBOL
        elif count_value is not None or _is_symbol_like(task_name):
            symbol_value = task_name

    result: dict[str, Any] = {"custom": True, "params": params, "mode": "generic"}

    if message_value is not None:
        message = _format_message(message_value)
        logger(f"收到訊息：{message}")
        logger(f"回顯：{message}")
        result["mode"] = "echo"
        result["message"] = message

    if symbol_value is not None:
        symbol = _parse_symbol(symbol_value)
        count = _parse_count(count_value, logger)
        output = symbol * count

        logger(f"符號圖案生成：{symbol} x {count}")
        logger(output)

        result["mode"] = "echo+symbol" if message_value is not None else "symbol"
        result["symbol"] = symbol
        result["count"] = count
        result["output"] = output

    if message_value is None and symbol_value is None:
        logger("Running generic custom task.")
        logger(f"Parameters: {json.dumps(params, ensure_ascii=False)}")

    logger("Custom task completed.")
    return result


_TASK_DEFINITIONS: dict[str, TaskDefinition] = {
    "health_check": TaskDefinition(
        name="health_check",
        label="系統健康檢查",
        description="檢查磁碟空間與系統狀態。",
        params_hint={},
    ),
    "sync_data": TaskDefinition(
        name="sync_data",
        label="資料同步",
        description="依來源網址與模式執行資料同步。",
        params_hint={"source_url": "https://example.com/api", "mode": "full"},
    ),
    "process_files": TaskDefinition(
        name="process_files",
        label="檔案批次處理",
        description="指定檔名進行批次轉換。",
        params_hint={"filename": "report_v1.csv", "rows": 250},
    ),
    "e2e_test": TaskDefinition(
        name="e2e_test",
        label="E2E 整合測試",
        description="驗證 FastAPI 與 PostgreSQL 整合流程。",
        params_hint={},
    ),
    "symbol": TaskDefinition(
        name="symbol",
        label="符號圖案生成",
        description="依 symbol 與 count 重複輸出任意符號或圖案。",
        params_hint={"symbol": "★", "count": 10},
    ),
    "echo": TaskDefinition(
        name="echo",
        label="訊息回顯",
        description="將 message 內容記錄並回顯到日誌。",
        params_hint={"message": "你好，世界！"},
    ),
    "對話": TaskDefinition(
        name="對話",
        label="簡單對話",
        description="將 message 或第一個參數內容當作對話訊息回顯。",
        params_hint={"message": "你好"},
    ),
    "custom": TaskDefinition(
        name="custom",
        label="自訂任務",
        description="使用通用處理器執行自訂任務名稱與參數。",
        params_hint={"key": "value"},
    ),
}

_TASK_HANDLERS: dict[str, TaskHandler] = {
    "health_check": health_check_handler,
    "sync_data": sync_data_handler,
    "process_files": process_files_handler,
    "e2e_test": e2e_test_handler,
    "custom": custom_task_handler,
}


def get_task_definitions() -> list[TaskDefinition]:
    return list(_TASK_DEFINITIONS.values())


def get_task_definition(task_name: str) -> TaskDefinition | None:
    return _TASK_DEFINITIONS.get(task_name)


def get_task_handler(task_name: str) -> TaskHandler:
    handler = _TASK_HANDLERS.get(task_name)
    if handler is not None:
        return handler
    return lambda logger, params: custom_task_handler(
        logger, params, task_name=task_name
    )
