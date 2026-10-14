"""掃描檔案的邏輯。

這個檔案只負責「找出檔案並統計」，不碰 Tkinter，
所以可以單獨拿來測試或重複使用。

第二階段加入了重複檔案搜尋：
    先用檔案大小篩選，只有大小相同的檔案才去算 MD5。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

# 最大的檔案要顯示幾筆
TOP_FILE_COUNT = 20

# 計算 MD5 時一次讀多少資料（1 MB）
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileInfo:
    """一個檔案的基本資料。"""

    path: Path  # 完整路徑
    size: int  # 檔案大小（bytes）


@dataclass
class DuplicateGroup:
    """一組內容完全相同的檔案。"""

    files: List[FileInfo]
    size: int  # 每個檔案的容量（同一組內大小必然相同）

    @property
    def count(self) -> int:
        """這組有幾個檔案。"""
        return len(self.files)

    @property
    def reclaimable(self) -> int:
        """保留一個就夠了，所以其他重複的容量都可以釋放。"""
        return self.size * (len(self.files) - 1)


@dataclass
class ScanResult:
    """一次掃描的結果。"""

    folder: Path  # 被掃描的資料夾
    file_count: int = 0  # 檔案總數
    total_size: int = 0  # 總容量（bytes）
    largest_files: List[FileInfo] = None  # 最大的前 20 個檔案
    skipped_count: int = 0  # 因為權限不足被跳過的數量
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)  # 重複檔案群組
    all_files: List[FileInfo] = field(default_factory=list)  # 掃描到的所有檔案

    def __post_init__(self) -> None:
        if self.largest_files is None:
            self.largest_files = []

    @property
    def duplicate_group_count(self) -> int:
        """重複檔案群組數。"""
        return len(self.duplicate_groups)

    @property
    def duplicate_file_count(self) -> int:
        """重複檔案總數。"""
        return sum(group.count for group in self.duplicate_groups)

    @property
    def reclaimable_size(self) -> int:
        """所有重複檔案加起來可以釋放的容量。"""
        return sum(group.reclaimable for group in self.duplicate_groups)

    def find_file(self, path: Path):
        """查一個檔案的 FileInfo，找不到回傳 None。"""
        target = Path(path)
        for info in self.all_files:
            if info.path == target:
                return info
        return None

    def remove_files(self, paths) -> int:
        """把已經清理掉的檔案從結果中移除，並重算所有統計。

        第三階段：檔案被移到資源回收筒後呼叫這個，
        畫面上的數字才會跟實際狀況一致。

        Args:
            paths: 要移除的檔案路徑集合

        Returns:
            實際移除的檔案數
        """
        targets = {Path(path) for path in paths}

        # 1. 從所有檔案清單中移除，重算檔案總數與總容量
        kept = [info for info in self.all_files if info.path not in targets]
        removed_count = len(self.all_files) - len(kept)
        self.all_files = kept
        self.file_count = len(kept)
        self.total_size = sum(info.size for info in kept)

        # 2. 重算最大的前 20 個
        #    不能只從舊的前 20 名裡過濾，因為原本排在第 21 名的檔案
        #    現在可能應該補進來。
        largest: List[FileInfo] = []
        for info in kept:
            _add_to_top(largest, info, TOP_FILE_COUNT)
        self.largest_files = largest

        # 3. 重算重複群組，只剩一個檔案的群組就不再是重複
        groups: List[DuplicateGroup] = []
        for group in self.duplicate_groups:
            remaining = [info for info in group.files if info.path not in targets]
            if len(remaining) < 2:
                continue  # 第 13 點：只剩一個就不算重複群組了
            groups.append(DuplicateGroup(files=remaining, size=group.size))
        self.duplicate_groups = groups

        return removed_count


def format_size(size: int) -> str:
    """把 bytes 轉成看得懂的文字，例如 1536 -> '1.5 KB'。"""
    if size < 1024:
        return f"{size} B"

    value = float(size)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f} {unit}"

    return f"{value:.1f} PB"


def _iter_files(folder: Path, on_skip) -> Iterator[FileInfo]:
    """依序走出資料夾裡的每個檔案。

    重點：遇到沒有權限讀取的資料夾或檔案時，只記錄下來然後繼續走，
    絕對不讓例外往外冒，否則整個程式會崩潰。

    Args:
        folder: 要掃描的資料夾
        on_skip: 每跳過一個項目就呼叫一次，用來統計
    """
    # 用清單當待辦，依序處理資料夾
    pending: List[Path] = [folder]

    while pending:
        current = pending.pop()

        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            # 讀不到這個資料夾（例如系統資料夾），跳過整個資料夾
            on_skip()
            continue

        for entry in entries:
            try:
                if entry.is_dir():
                    # 是資料夾就排進待辦，稍後再處理
                    pending.append(entry)
                elif entry.is_file():
                    size = entry.stat().st_size
                    yield FileInfo(path=entry, size=size)
                else:
                    # 符號連結或特殊檔案，第一階段先不處理
                    on_skip()
            except (PermissionError, OSError):
                # 檔案可能剛好被鎖住或已被刪除，跳過繼續
                on_skip()


def _add_to_top(largest: List[FileInfo], item: FileInfo, limit: int) -> None:
    """把檔案放進「最大的前 N 筆」清單，並維持由大到小排序。"""
    largest.append(item)
    largest.sort(key=lambda info: info.size, reverse=True)

    # 超過上限就把最後面（最小）的丟掉
    if len(largest) > limit:
        del largest[limit:]


def file_md5(path: Path) -> Optional[str]:
    """算出檔案的 MD5 雜湊值。

    一次只讀 1 MB，不會把整個檔案塞進記憶體。
    讀不到（沒有權限或檔案被鎖住）就回傳 None，呼叫者自行跳過。
    """
    digest = hashlib.md5(usedforsecurity=False)

    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:  # 讀完了
                    break
                digest.update(chunk)
    except (PermissionError, OSError):
        return None

    return digest.hexdigest()


def find_duplicate_groups(
    same_size_files: Dict[int, List[FileInfo]],
    on_hash_progress: Optional[Callable[[int, int], None]] = None,
) -> List[DuplicateGroup]:
    """從「大小相同的檔案」找出內容完全相同的群組。

    因為大小已經不一樣的檔案不可能重複，所以這裡只處理
    大小至少出現兩次的檔案，減少計算 MD5 的次數。

    Args:
        same_size_files: {檔案大小: [檔案, 檔案, ...]}，每個清單至少有 2 個檔案
        on_hash_progress: 每算完一個檔案就呼叫，參數是 (已完成, 總數)
    """
    # 用 MD5 當 key，把內容相同的檔案收集在一起
    hash_to_files: Dict[str, List[FileInfo]] = {}

    total = sum(len(files) for files in same_size_files.values())
    done = 0

    # 由小到大處理，硬碟讀取會比較快
    for size in sorted(same_size_files):
        for info in same_size_files[size]:
            digest = file_md5(info.path)
            done += 1

            if on_hash_progress is not None:
                on_hash_progress(done, total)

            if digest is None:  # 讀不到就跳過，不要影響別的檔案
                continue

            hash_to_files.setdefault(digest, []).append(info)

    groups: List[DuplicateGroup] = []

    for files in hash_to_files.values():
        if len(files) < 2:  # 只有一個不算重複
            continue
        # 路徑排序，讓畫面顯示順序固定
        files.sort(key=lambda info: str(info.path))
        groups.append(DuplicateGroup(files=files, size=files[0].size))

    # 可釋放空間多的群組排在前面
    groups.sort(key=lambda group: group.reclaimable, reverse=True)
    return groups


def scan_directory(
    folder: Path,
    on_progress: Optional[Callable[[int], None]] = None,
    on_hash_progress: Optional[Callable[[int, int], None]] = None,
) -> ScanResult:
    """掃描資料夾，回傳統計結果（第一階段 + 第二階段）。

    Args:
        folder: 要掃描的資料夾
        on_progress: 每找到一個檔案就呼叫一次，參數是目前已找到的檔案數。
        on_hash_progress: 第二階段，每算完一個 MD5 就呼叫一次，
                          參數是 (已完成數, 總數)。
    """
    folder = Path(folder)

    result = ScanResult(folder=folder)
    largest: List[FileInfo] = []

    # 用檔案大小當 key，把檔案分組。
    # 第一階段只維護「最大的 20 筆」，這裡則需要保留所有檔案的路徑，
    # 因為要比對哪些檔案大小相同。
    size_to_files: Dict[int, List[FileInfo]] = {}

    def handle_skip() -> None:
        result.skipped_count += 1

    for file_info in _iter_files(folder, on_skip=handle_skip):
        result.file_count += 1
        result.total_size += file_info.size

        # 保留所有檔案，第三階段清理後才能重算「最大的前 20 個」
        result.all_files.append(file_info)

        _add_to_top(largest, file_info, TOP_FILE_COUNT)
        size_to_files.setdefault(file_info.size, []).append(file_info)

        if on_progress is not None:
            on_progress(result.file_count)

    result.largest_files = largest

    # 第二階段：先篩出「大小至少出現兩次」的檔案，其餘的不用算 MD5
    same_size_files = {
        size: files for size, files in size_to_files.items() if len(files) >= 2
    }
    result.duplicate_groups = find_duplicate_groups(
        same_size_files,
        on_hash_progress=on_hash_progress,
    )

    return result