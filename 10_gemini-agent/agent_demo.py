import ast
import operator
import os
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import errors, types

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS = (
    "gemini-4-hydrogen",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
)
BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ModelUnavailable(RuntimeError):
    pass


class FatalApiError(RuntimeError):
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


REQUEST_TIMEOUT_MS = _env_int("GEMINI_TIMEOUT_MS", 15000)
RETRIES_PER_MODEL = max(1, _env_int("GEMINI_RETRIES", 2))
BACKOFF_SECONDS = max(0.0, _env_float("GEMINI_BACKOFF_SECONDS", 1.0))
MAX_STEPS = max(1, _env_int("AGENT_MAX_STEPS", 5))


def _load_env_file() -> None:
    env_path = SCRIPT_DIR / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _brief(exc: Exception, limit: int = 180) -> str:
    text = " ".join(str(exc).split())
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "***")
    return text if len(text) <= limit else text[:limit] + "..."


def _model_candidates() -> tuple[str, ...]:
    raw = os.getenv("GEMINI_MODELS")
    if raw:
        models = tuple(item.strip() for item in raw.split(",") if item.strip())
    elif os.getenv("GEMINI_MODEL"):
        models = (os.environ["GEMINI_MODEL"].strip(),) + DEFAULT_MODELS
    else:
        models = DEFAULT_MODELS
    return tuple(dict.fromkeys(models))


def get_current_time() -> str:
    """取得目前的系統日期與時間。當使用者詢問現在幾點、今天幾號或時間相關問題時呼叫。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _eval_node(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指數過大")
        return BIN_OPS[type(node.op)](_eval_node(node.left), right)
    raise ValueError("不支援的算式")


def calculate_math(expression: str) -> str:
    """計算基礎數學四則運算算式。

    Args:
        expression: 要計算的數學算式字串，例如 '125 * 48 + 300'
    """
    try:
        result = _eval_node(ast.parse(expression, mode="eval"))
        return str(result)
    except Exception as exc:
        return f"計算失敗：{exc}"


TOOL_MAP = {
    "get_current_time": get_current_time,
    "calculate_math": calculate_math,
}


def _is_retryable(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if code in (408, 409, 429, 500, 502, 503, 504):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    return "timeout" in name or "connect" in name


def call_with_retry(client, model_name: str, messages: list, config, retries: int = RETRIES_PER_MODEL):
    """遇到短暫錯誤時重試；404 直接交給上一層換模型。"""
    for attempt in range(1, retries + 1):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=messages,
                config=config,
            )
        except errors.APIError as exc:
            code = exc.code
            if code == 404:
                raise ModelUnavailable(f"模型 {model_name} 不存在或無存取權（404）") from exc
            if code in (400, 401, 403):
                label = {400: "請求格式", 401: "API Key", 403: "權限"}[code]
                raise FatalApiError(f"{label}錯誤（{code}）：{_brief(exc)}") from exc
            if _is_retryable(exc) and attempt < retries:
                wait_sec = BACKOFF_SECONDS * attempt
                print(
                    f"[系統提示] {model_name} 暫時失敗（{code}），"
                    f"{wait_sec:.1f} 秒後重試 {attempt + 1}/{retries} ..."
                )
                time.sleep(wait_sec)
                continue
            raise
        except Exception as exc:
            if _is_retryable(exc) and attempt < retries:
                wait_sec = BACKOFF_SECONDS * attempt
                print(
                    f"[系統提示] {model_name} 連線異常（{_brief(exc, 80)}），"
                    f"{wait_sec:.1f} 秒後重試 {attempt + 1}/{retries} ..."
                )
                time.sleep(wait_sec)
                continue
            raise
    raise RuntimeError(f"{model_name} 重試 {retries} 次後仍失敗")


def generate_with_fallback(client, models: tuple[str, ...], messages: list, config):
    last_error = None
    for model_name in models:
        print(f"[模型] 嘗試 {model_name}")
        try:
            response = call_with_retry(client, model_name, messages, config)
        except ModelUnavailable as exc:
            last_error = exc
            print(f"[系統提示] {exc}，切換下一個模型。")
            continue
        except FatalApiError:
            raise
        except Exception as exc:
            last_error = exc
            print(f"[系統提示] {model_name} 失敗：{_brief(exc)}，切換下一個模型。")
            continue
        print(f"[模型] 本次使用 {model_name}")
        return response
    raise RuntimeError(f"所有模型都無法使用：{_brief(last_error) if last_error else '未知錯誤'}")


def _collect_observations(messages: list) -> dict:
    observations = {}
    for content in messages:
        for part in getattr(content, "parts", None) or []:
            function_response = getattr(part, "function_response", None)
            if function_response is None:
                continue
            name = getattr(function_response, "name", None)
            if name:
                response = getattr(function_response, "response", None) or {}
                observations[name] = response.get("result", "")
    return observations


class OfflineClient:
    def __init__(self):
        self.models = self

    def generate_content(self, *, model: str, contents: list, config):
        observations = _collect_observations(contents)
        if observations:
            text = (
                "[離線模擬最終回覆] "
                f"目前時間：{observations.get('get_current_time', '未知')}；"
                f"(365 * 24) + 1280 = {observations.get('calculate_math', '未知')}"
            )
            content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=text)],
            )
        else:
            content = types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(name="get_current_time", args={}),
                    types.Part.from_function_call(
                        name="calculate_math",
                        args={"expression": "(365 * 24) + 1280"},
                    ),
                ],
            )
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=content)]
        )


def run_agent(user_prompt: str, client, models: tuple[str, ...], max_steps: int = MAX_STEPS):
    print(f"\n[使用者任務] {user_prompt}")
    print("=" * 50)

    messages = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)],
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction="你是一個務實的 AI 助手。遇到需要即時時間或精確數學計算的問題時，務必使用工具，不要自己心算猜測。",
        tools=[get_current_time, calculate_math],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
    )

    for step in range(1, max_steps + 1):
        print(f"\n--- 第 {step} 輪迴圈 ---")
        response = generate_with_fallback(client, models, messages, config)

        if not response.candidates:
            print("[系統提示] 模型沒有回傳候選內容，結束迴圈。")
            return

        candidate_content = response.candidates[0].content
        messages.append(candidate_content)

        function_calls = response.function_calls or []
        if function_calls:
            for call in function_calls:
                func_name = call.name
                func_args = call.args or {}
                print(f"[Agent 決策] 呼叫工具 -> {func_name}({func_args})")

                if func_name in TOOL_MAP:
                    observation = TOOL_MAP[func_name](**func_args)
                else:
                    observation = f"找不到工具：{func_name}"

                print(f"[工具回傳結果] {observation}")

                messages.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=func_name,
                                response={"result": observation},
                            )
                        ],
                    )
                )
        else:
            print(f"\n[Agent 最終回覆]\n{response.text}")
            print("=" * 50)
            return

    print("\n[系統提示] 已達最大執行步數上限，強制結束迴圈。")


def main() -> int:
    _load_env_file()
    mode = os.getenv("AGENT_DEMO_MODE", "api").strip().lower()

    if mode in ("offline", "mock"):
        print("[系統提示] 離線模擬模式：不送出任何網路請求。")
        client = OfflineClient()
        models = ("offline-mock",)
    else:
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            print("[系統提示] 找不到 GEMINI_API_KEY / GOOGLE_API_KEY，已安全結束（未送出網路請求）。")
            print("  設定方式 A：$env:GEMINI_API_KEY='你的金鑰'; python agent_demo.py")
            print("  設定方式 B：在本檔同資料夾建立 .env，內容 GEMINI_API_KEY=你的金鑰")
            print("  只看 Agent 迴圈：$env:AGENT_DEMO_MODE='offline'; python agent_demo.py")
            return 2
        try:
            client = genai.Client(
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
            )
        except Exception as exc:
            print(f"[系統提示] 初始化失敗：{_brief(exc)}")
            return 1
        models = _model_candidates()

    print(f"[設定] 單次請求逾時 {REQUEST_TIMEOUT_MS} ms；每個模型最多 {RETRIES_PER_MODEL} 次；最多 {MAX_STEPS} 輪。")

    try:
        run_agent(
            "現在幾點了？另外請幫我精確計算 (365 * 24) + 1280 等於多少？",
            client,
            models,
        )
    except Exception as exc:
        print(f"\n[系統提示] 執行結束：{_brief(exc)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
