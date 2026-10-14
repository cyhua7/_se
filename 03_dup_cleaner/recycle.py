"""把檔案移到 Windows「資源回收筒」。

這裡直接呼叫 Windows 系統 API（shell32.dll 的 SHFileOperationW），
檔案會出現在你桌面上的資源回收筒，可以隨時還原，
而不是被永久刪除，也不是移到某個自己建的資料夾。

只支援 Windows。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import List, Tuple

# SHFileOperation 的動作代碼
FO_DELETE = 0x0003

# 選項
FOF_SILENT = 0x0004  # 不顯示進度視窗
FOF_NOCONFIRMATION = 0x0010  # 不跳「確定要刪除嗎」
FOF_ALLOWUNDO = 0x0040  # ★ 送到資源回收筒，而不是永久刪除
FOF_NOERRORUI = 0x0400  # 不顯示錯誤視窗，錯誤由程式自己處理
FOF_NOCONFIRMMKDIR = 0x0200  # 不對資料夾跳確認

FLAGS = (
    FOF_ALLOWUNDO
    | FOF_NOCONFIRMATION
    | FOF_SILENT
    | FOF_NOERRORUI
    | FOF_NOCONFIRMMKDIR
)


class SHFILEOPSTRUCTW(ctypes.Structure):
    """SHFileOperation 需要的參數結構。"""

    _fields_ = [
        ("hwnd", wintypes.HWND),  # 父視窗，這裡不用
        ("wFunc", wintypes.UINT),  # 要做的動作
        ("pFrom", wintypes.LPCWSTR),  # 來源（要刪除的路徑）
        ("pTo", wintypes.LPCWSTR),  # 目的地，刪除時不用
        ("fFlags", ctypes.c_uint16),  # 選項旗標
        ("fAnyOperationsAborted", wintypes.BOOL),  # 有沒有被中止
        ("hNameMappings", ctypes.c_void_p),  # 不用
        ("lpszProgressTitle", wintypes.LPCWSTR),  # 進度標題，沒有視窗所以不用
    ]


def _shell32():
    """取得 shell32.dll 的函式指標。"""
    return ctypes.WinDLL("shell32")


def _describe_error(path: Path, error: OSError) -> str:
    """把 Windows 錯誤碼翻成使用者看得懂的原因。"""
    code = getattr(error, "winerror", None) or getattr(error, "errno", 0)

    if code == 2:
        return "檔案或資料夾不存在"
    if code == 3:
        return "找不到指定的路徑"
    if code == 5:
        return "沒有權限"
    if code == 32:  # ERROR_SHARING_VIOLATION
        return "檔案正在被其他程式使用"
    if code == 19:  # ERROR_WRITE_PROTECT
        return "檔案或資料夾有保護，不能刪除"
    if code == 123:
        return "檔案名稱或路徑語法錯誤"
    return f"系統錯誤（代碼 {code}）" if code else str(error)


def send_to_recycle_bin(path: Path) -> Tuple[bool, str]:
    """把一個檔案移到資源回收筒。

    一次只處理一個檔案，這樣才能知道「是哪一個檔案失敗」。

    Args:
        path: 要清理的檔案

    Returns:
        (是否成功, 失敗原因)。成功時原因為空字串。
    """
    path = Path(path)

    if not path.exists():
        return False, "檔案不存在"

    try:
        # Windows 要求路徑清單用兩個 \0 結尾
        double_null_path = f"{path}\0\0"

        operation = SHFILEOPSTRUCTW()
        operation.hwnd = None
        operation.wFunc = FO_DELETE
        operation.pFrom = double_null_path
        operation.pTo = None
        operation.fFlags = FLAGS
        operation.fAnyOperationsAborted = False
        operation.hNameMappings = None
        operation.lpszProgressTitle = None

        shell32 = _shell32()
        shell32.SHFileOperationW.restype = ctypes.c_int
        result = shell32.SHFileOperationW(ctypes.byref(operation))
    except OSError as error:
        return False, _describe_error(path, error)
    except Exception as error:  # 連 API 都叫不到也要回報，不能讓程式崩潰
        return False, f"無法呼叫 Windows 資源回收筒：{error}"

    if result != 0:
        # 沒有權限或檔案被佔用時，這裡會回傳非 0
        try:
            detail = _describe_error(path, OSError(result))
        except Exception:
            detail = f"Windows 回傳錯誤碼 {result}"
        return False, detail

    if operation.fAnyOperationsAborted:
        return False, "操作被中止"

    # 檔案還在 → 沒有真的移到資源回收筒
    if path.exists():
        return False, "檔案仍存在，可能無法移到資源回收筒"

    return True, ""


def send_many_to_recycle_bin(paths: List[Path]) -> Tuple[List[Path], List[Tuple[Path, str]]]:
    """依序把多個檔案移到資源回收筒。

    就算某些檔案失敗，其他的檔案還是會繼續處理。

    Returns:
        (成功清單, [(失敗的檔案, 原因), ...])
    """
    succeeded: List[Path] = []
    failed: List[Tuple[Path, str]] = []

    for path in paths:
        ok, reason = send_to_recycle_bin(path)
        if ok:
            succeeded.append(path)
        else:
            failed.append((path, reason))

    return succeeded, failed