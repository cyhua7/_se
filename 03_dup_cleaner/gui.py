"""Tkinter 圖形介面。

分工：
    scanner.py   負責找檔案、算數量、找重複檔案
    recycle.py   負責把檔案移到 Windows 資源回收筒
    gui.py       本檔案，負責畫面與按鈕
    main.py      程式入口
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Set, Tuple

import recycle
import scanner

# 結果表格的欄位：(欄位代號, 標題, 寬度)
TABLE_COLUMNS = (
    ("name", "檔名", 240),
    ("size", "檔案大小", 120),
    ("path", "完整路徑", 520),
)

# 重複檔案表格的欄位：(欄位代號, 標題, 寬度)
# 選取欄放檔案的核取方塊；群組操作欄放該群組的全選／取消全選
DUPLICATE_COLUMNS = (
    ("pick", "選取", 66),
    ("group_action", "群組操作", 100),
    ("detail", "完整路徑 / 摘要", 560),
    ("size", "檔案大小", 150),
)

# 核取方塊符號
BOX_UNCHECKED = "☐"
BOX_CHECKED = "☑"

# Treeview 的「顯示欄位」編號。
# 最左邊的展開箭頭欄固定是 #0，所以第一個 columns 欄位是 #1。
COLUMN_PICK = "#1"  # 選取
COLUMN_GROUP_ACTION = "#2"  # 群組操作

# 中文字型（Windows 內建）
UI_FONT = ("Microsoft JhengHei", 10)


class CleanerApp:
    """主畫面。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("重複檔案與大檔案清理助手")
        self.root.geometry("1000x900")
        self.root.minsize(820, 640)

        # 執行緒之間共用的資料。掃描在背景執行緒跑，
        # 主執行緒用 after() 定時回來讀這些值。
        self._result: Optional[scanner.ScanResult] = None
        self._error: Optional[str] = None
        self._progress = 0
        self._hash_progress = (0, 0)
        self._scanning = False
        self._phase = "scan"  # 目前階段："scan" 數檔案／"hash" 算 MD5

        # 選取狀態：使用者勾選的檔案，以及它們的大小
        # （iid = 表格列代號 → 路徑；path → 大小）
        self._row_paths: Dict[str, Path] = {}
        self._selected: Dict[Path, int] = {}
        # 路徑 → 大小，避免查大小時還要一個一個線性搜尋
        self._size_by_path: Dict[Path, int] = {}
        # 群組列代號 → 該群組包含的檔案列代號
        self._group_rows: Dict[str, List[str]] = {}

        # 清理（第三階段）在背景執行緒執行時使用的狀態
        self._clean_running = False
        self._clean_done = False
        self._clean_succeeded: List[Path] = []
        self._clean_failed: List[Tuple[Path, str]] = []

        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="請先選擇要掃描的資料夾。")
        self.file_count_var = tk.StringVar(value="-")
        self.total_size_var = tk.StringVar(value="-")
        self.skipped_var = tk.StringVar(value="-")
        self.duplicate_group_var = tk.StringVar(value="-")
        self.duplicate_file_var = tk.StringVar(value="-")
        self.reclaimable_var = tk.StringVar(value="-")
        self.selected_count_var = tk.StringVar(value="0 個")
        self.selected_size_var = tk.StringVar(value=scanner.format_size(0))

        self._build_widgets()

    # ---------------------------------------------------------------
    # 建立畫面
    # ---------------------------------------------------------------
    def _build_widgets(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        # 標題
        title = ttk.Label(
            outer,
            text="重複檔案與大檔案清理助手",
            font=("Microsoft JhengHei", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            outer,
            text="統計檔案數量、總容量，找出最大的前 20 個檔案與內容相同的重複檔案。",
            font=UI_FONT,
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 10))

        # 資料夾選擇區
        folder_frame = ttk.LabelFrame(outer, text="掃描資料夾", padding=10)
        folder_frame.grid(row=2, column=0, sticky="ew")
        folder_frame.columnconfigure(0, weight=1)

        self.folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self.folder_var,
            font=UI_FONT,
            state="readonly",
        )
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.choose_button = ttk.Button(
            folder_frame,
            text="選擇資料夾",
            command=self.on_choose_folder,
        )
        self.choose_button.grid(row=0, column=1)

        self.scan_button = ttk.Button(
            folder_frame,
            text="開始掃描",
            command=self.on_start_scan,
        )
        self.scan_button.grid(row=0, column=2, padx=(8, 0))

        # 統計結果區
        stats_frame = ttk.LabelFrame(outer, text="掃描統計", padding=10)
        stats_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        for column in (1, 3, 5):
            stats_frame.columnconfigure(column, weight=1)

        # 第一階段：檔案總數、總容量、權限不足跳過
        self._add_stat(stats_frame, "檔案總數：", self.file_count_var, column=0)
        self._add_stat(stats_frame, "總容量：", self.total_size_var, column=2)
        self._add_stat(stats_frame, "權限不足跳過：", self.skipped_var, column=4)

        # 第二階段：重複檔案統計
        duplicate_stats = ttk.Frame(stats_frame)
        duplicate_stats.grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))

        ttk.Label(duplicate_stats, text="重複檔案群組：", font=UI_FONT).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(duplicate_stats, textvariable=self.duplicate_group_var, font=UI_FONT).grid(
            row=0, column=1, sticky="w", padx=(0, 24)
        )
        ttk.Label(duplicate_stats, text="重複檔案總數：", font=UI_FONT).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(duplicate_stats, textvariable=self.duplicate_file_var, font=UI_FONT).grid(
            row=0, column=3, sticky="w", padx=(0, 24)
        )
        ttk.Label(duplicate_stats, text="可釋放容量：", font=UI_FONT).grid(
            row=0, column=4, sticky="w"
        )
        ttk.Label(duplicate_stats, textvariable=self.reclaimable_var, font=UI_FONT).grid(
            row=0, column=5, sticky="w"
        )

        # 第三階段：選取統計
        selected_stats = ttk.Frame(stats_frame)
        selected_stats.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))

        ttk.Label(selected_stats, text="已選擇檔案：", font=UI_FONT).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            selected_stats, textvariable=self.selected_count_var, font=UI_FONT
        ).grid(row=0, column=1, sticky="w", padx=(0, 24))
        ttk.Label(selected_stats, text="預計釋放空間：", font=UI_FONT).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(
            selected_stats, textvariable=self.selected_size_var, font=UI_FONT
        ).grid(row=0, column=3, sticky="w")

        # 結果區：上下兩個面板，可以用中間的把手調整高度
        paned = ttk.Panedwindow(outer, orient="vertical")
        paned.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        paned.add(self._build_largest_frame(paned), weight=1)
        paned.add(self._build_duplicate_frame(paned), weight=2)

        # 狀態列
        status_label = ttk.Label(
            outer,
            textvariable=self.status_var,
            font=UI_FONT,
            relief="sunken",
            anchor="w",
            padding=(6, 3),
        )
        status_label.grid(row=5, column=0, sticky="ew", pady=(10, 0))

    def _add_stat(self, parent: ttk.Frame, caption: str, variable, column: int) -> None:
        """在統計區放一組「標籤：數值」。"""
        ttk.Label(parent, text=caption, font=UI_FONT).grid(
            row=0, column=column, sticky="w"
        )
        ttk.Label(parent, textvariable=variable, font=UI_FONT).grid(
            row=0, column=column + 1, sticky="w", padx=(0, 24)
        )

    def _build_largest_frame(self, parent) -> ttk.LabelFrame:
        """第一階段：最大的前 20 個檔案。"""
        frame = ttk.LabelFrame(
            parent, text=f"最大的前 {scanner.TOP_FILE_COUNT} 個檔案", padding=10
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(
            frame,
            columns=[code for code, _, _ in TABLE_COLUMNS],
            show="headings",
            selectmode="browse",
        )

        for code, heading, width in TABLE_COLUMNS:
            self.table.heading(code, text=heading)
            self.table.column(code, width=width, anchor="w")

        vertical_bar = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        horizontal_bar = ttk.Scrollbar(
            frame, orient="horizontal", command=self.table.xview
        )
        self.table.configure(
            yscrollcommand=vertical_bar.set,
            xscrollcommand=horizontal_bar.set,
        )

        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_bar.grid(row=0, column=1, sticky="ns")
        horizontal_bar.grid(row=1, column=0, sticky="ew")
        return frame

    def _build_duplicate_frame(self, parent) -> ttk.LabelFrame:
        """第二、三階段：重複檔案清單（可勾選清理）。"""
        frame = ttk.LabelFrame(parent, text="重複檔案（內容完全相同）", padding=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # 第三階段：整體操作工具列
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.select_all_button = ttk.Button(
            toolbar, text="全部選取", command=self.on_select_all
        )
        self.select_all_button.pack(side="left")

        self.unselect_all_button = ttk.Button(
            toolbar, text="全部取消", command=self.on_unselect_all
        )
        self.unselect_all_button.pack(side="left", padx=(6, 0))

        self.clean_button = ttk.Button(
            toolbar, text="清理選取檔案", command=self.on_clean_selected
        )
        self.clean_button.pack(side="right")

        tip = ttk.Label(
            toolbar,
            text="　點擊左方「選取」欄的方塊即可勾選檔案",
            font=UI_FONT,
        )
        tip.pack(side="left", padx=(12, 0))

        self.duplicate_table = ttk.Treeview(
            frame,
            columns=[code for code, _, _ in DUPLICATE_COLUMNS],
            show="tree headings",
            selectmode="browse",
        )
        # 最左邊的展開箭頭欄位
        self.duplicate_table.heading("#0", text="重複群組")
        self.duplicate_table.column("#0", width=120, minwidth=120, stretch=False)

        for code, heading, width in DUPLICATE_COLUMNS:
            self.duplicate_table.heading(code, text=heading)
            # 核取方塊置中，其他靠左
            anchor = "center" if code == "pick" else "w"
            self.duplicate_table.column(code, width=width, anchor=anchor)

        # 群組標題用粗體，看起來跟檔案清單有層級差異
        self.duplicate_table.tag_configure(
            "group", font=("Microsoft JhengHei", 10, "bold")
        )

        # 點擊切換勾選
        self.duplicate_table.bind("<Button-1>", self.on_duplicate_click)
        self.duplicate_table.bind("<Double-Button-1>", lambda event: None)

        vertical_bar = ttk.Scrollbar(
            frame, orient="vertical", command=self.duplicate_table.yview
        )
        horizontal_bar = ttk.Scrollbar(
            frame, orient="horizontal", command=self.duplicate_table.xview
        )
        self.duplicate_table.configure(
            yscrollcommand=vertical_bar.set,
            xscrollcommand=horizontal_bar.set,
        )

        self.duplicate_table.grid(row=1, column=0, sticky="nsew")
        vertical_bar.grid(row=1, column=1, sticky="ns")
        horizontal_bar.grid(row=2, column=0, sticky="ew")
        return frame

    # ---------------------------------------------------------------
    # 第三階段：勾選
    # ---------------------------------------------------------------
    def on_duplicate_click(self, event) -> None:
        """點擊表格切換勾選狀態。

        點「選取」欄 → 勾選／取消勾選單一檔案，或整組全選／取消
        點「群組操作」欄 → 該群組取消全選
        """
        row_id = self.duplicate_table.identify_row(event.y)
        if not row_id:
            return

        # identify_column() 回傳的是「顯示欄位」編號：
        #   #0 = 左邊的展開箭頭（群組名稱）
        #   #1 = 選取、#2 = 群組操作、#3 = 完整路徑、#4 = 檔案大小
        column_id = self.duplicate_table.identify_column(event.x)
        click_pick = column_id == COLUMN_PICK
        click_group_action = column_id == COLUMN_GROUP_ACTION

        if not click_pick and not click_group_action:
            return  # 點其他地方不做任何事

        # 群組標題列：全選 / 取消全選
        if row_id in self._group_rows:
            if click_pick:
                self._select_group(row_id, True)
            else:
                self._select_group(row_id, False)
            return "break"

        # 檔案列：切換這一個檔案
        if click_pick:
            self._toggle_file(row_id)
            return "break"

        return "break"

    def _toggle_file(self, row_id: str) -> None:
        """勾選或取消勾選一個檔案。"""
        path = self._row_paths.get(row_id)
        if path is None:
            return

        size = self._file_size(path)

        if path in self._selected:
            del self._selected[path]
        else:
            self._selected[path] = size

        self._refresh_checkbox(row_id)
        self._update_selected_stats()

    def _select_group(self, group_row: str, checked: bool) -> None:
        """全選或取消全選一個群組。"""
        for row_id in self._group_rows.get(group_row, []):
            path = self._row_paths.get(row_id)
            if path is None:
                continue

            if checked:
                self._selected[path] = self._file_size(path)
            else:
                self._selected.pop(path, None)

            self._refresh_checkbox(row_id)

        self._update_selected_stats()

    def on_select_all(self) -> None:
        """全部選取。"""
        for row_id, path in self._row_paths.items():
            self._selected[path] = self._file_size(path)
            self._refresh_checkbox(row_id)
        self._update_selected_stats()

    def on_unselect_all(self) -> None:
        """全部取消。"""
        self._selected.clear()
        for row_id in self._row_paths:
            self._refresh_checkbox(row_id)
        self._update_selected_stats()

    def _file_size(self, path: Path) -> int:
        """查一個檔案的大小（用掃描結果，避免重新讀硬碟）。"""
        return self._size_by_path.get(path, 0)

    def _refresh_checkbox(self, row_id: str) -> None:
        """更新某一列的方塊符號。"""
        path = self._row_paths.get(row_id)
        if path is None:
            return
        symbol = BOX_CHECKED if path in self._selected else BOX_UNCHECKED
        self.duplicate_table.set(row_id, "pick", symbol)

    def _update_selected_stats(self) -> None:
        """更新「已選擇檔案數量」與「預計釋放空間」。"""
        count = len(self._selected)
        total = sum(self._selected.values())

        self.selected_count_var.set(f"{count:,} 個")
        self.selected_size_var.set(scanner.format_size(total))

    # ---------------------------------------------------------------
    # 第三階段：清理
    # ---------------------------------------------------------------
    def on_clean_selected(self) -> None:
        """把使用者勾選的檔案移到資源回收筒。"""
        if self._scanning or self._clean_running or not self._selected:
            messagebox.showwarning("尚未選擇檔案", "請先勾選要清理的檔案。")
            return

        count = len(self._selected)
        total = sum(self._selected.values())

        # 第 9 點：先確認，內容要講清楚
        confirmed = messagebox.askyesno(
            "確認清理",
            f"確定要清理 {count} 個檔案嗎？\n\n"
            f"預計釋放 {scanner.format_size(total)} 空間\n\n"
            "檔案會移到 Windows 資源回收筒，可以隨時還原。",
        )
        if not confirmed:
            self.status_var.set("已取消清理。")
            return

        self.clean_button.configure(state="disabled")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        self._clean_done = False
        self._clean_succeeded = []
        self._clean_failed = []
        self._clean_running = True

        paths = list(self._selected.keys())

        # 搬到背景執行緒，避免畫面卡住
        worker = threading.Thread(target=self._clean_worker, args=(paths,))
        worker.daemon = True
        worker.start()

        self._poll_clean()

    def _clean_worker(self, paths: List[Path]) -> None:
        """在背景執行緒把檔案移到資源回收筒。

        注意：這個函式不能碰任何 Tkinter 元件，
        Tkinter 只允許在主執行緒操作。
        """
        succeeded, failed = recycle.send_many_to_recycle_bin(paths)
        self._clean_succeeded = succeeded
        self._clean_failed = failed
        self._clean_done = True

    def _poll_clean(self) -> None:
        """在主執行緒等待清理完成。"""
        if not self._clean_running:
            return

        if not self._clean_done:
            self.root.after(100, self._poll_clean)
            return

        self._clean_running = False
        self._finish_clean()

    def _finish_clean(self) -> None:
        """清理完成，重算統計並更新畫面。"""
        self.root.config(cursor="")
        self.clean_button.configure(state="normal")

        succeeded: List[Path] = self._clean_succeeded
        failed: List[Tuple[Path, str]] = self._clean_failed

        result = self._result
        if result is None:
            return

        # 第 12 點：從結果中移除並重算所有統計
        removed = result.remove_files(succeeded)

        # 已清理的不再算在選取中
        for path in succeeded:
            self._selected.pop(path, None)

        self._refresh_all_displays()

        # 第 11 點：失敗的檔案要告訴使用者是哪些、為什麼
        if failed:
            lines = [f"• {path.name}\n  {reason}" for path, reason in failed[:10]]
            if len(failed) > 10:
                lines.append(f"…還有 {len(failed) - 10} 個")
            messagebox.showwarning(
                "部分檔案清理失敗",
                f"成功 {removed} 個，失敗 {len(failed)} 個。\n\n"
                + "\n".join(lines),
            )

        if result.duplicate_group_count == 0:
            summary = "目前沒有找到重複檔案。"
        else:
            summary = (
                f"目前剩下 {result.duplicate_group_count:,} 組重複檔案，"
                f"可釋放 {scanner.format_size(result.reclaimable_size)}。"
            )

        self.status_var.set(
            f"已清理 {removed} 個檔案到資源回收筒"
            + (f"，{len(failed)} 個失敗。" if failed else "。")
            + summary
        )

    def _refresh_all_displays(self) -> None:
        """把最新統計畫到畫面上（第一、二、三階段的數字）。"""
        result = self._result
        if result is None:
            return

        # 第一階段統計
        self.file_count_var.set(f"{result.file_count:,} 個")
        self.total_size_var.set(scanner.format_size(result.total_size))

        for row in self.table.get_children():
            self.table.delete(row)
        for row_index, file_info in enumerate(result.largest_files, start=1):
            self.table.insert(
                "",
                "end",
                values=(
                    row_index,
                    file_info.path.name,
                    f"{scanner.format_size(file_info.size)}"
                    f"（{file_info.size:,} bytes）",
                    str(file_info.path),
                ),
            )

        # 第二階段統計
        self.duplicate_group_var.set(f"{result.duplicate_group_count:,} 組")
        self.duplicate_file_var.set(f"{result.duplicate_file_count:,} 個")
        self.reclaimable_var.set(scanner.format_size(result.reclaimable_size))

        # 重複檔案表格（會重建列，還沒被清理掉的選取要保留）
        previously_selected = dict(self._selected)
        self._fill_duplicate_table(result)
        self._selected = {
            path: size
            for path, size in previously_selected.items()
            if path.exists()
        }
        for row_id, path in self._row_paths.items():
            if path in self._selected:
                self.duplicate_table.set(row_id, "pick", BOX_CHECKED)

        self._update_selected_stats()

    # ---------------------------------------------------------------
    # 按鈕事件
    # ---------------------------------------------------------------
    def on_choose_folder(self) -> None:
        """跳出資料夾選擇視窗。"""
        folder = filedialog.askdirectory(title="請選擇要掃描的資料夾")

        if not folder:  # 使用者按了取消
            return

        self.folder_var.set(folder)
        self.status_var.set(f"已選擇：{folder}")

    def on_start_scan(self) -> None:
        """開始掃描。把實際工作丟到背景執行緒，畫面才不會卡住。"""
        if self._scanning:
            return

        folder_text = self.folder_var.get().strip()
        if not folder_text:
            messagebox.showwarning("尚未選擇資料夾", "請先按「選擇資料夾」。")
            return

        folder = Path(folder_text)
        if not folder.is_dir():
            messagebox.showerror("資料夾不存在", f"找不到這個資料夾：\n{folder}")
            return

        self._result = None
        self._error = None
        self._progress = 0
        self._hash_progress = (0, 0)
        self._scanning = True
        self._phase = "scan"

        self._set_buttons_enabled(False)
        self._clear_table()
        self.file_count_var.set("0")
        self.total_size_var.set(scanner.format_size(0))
        self.skipped_var.set("0")
        self.duplicate_group_var.set("0")
        self.duplicate_file_var.set("0")
        self.reclaimable_var.set(scanner.format_size(0))

        worker = threading.Thread(target=self._scan_worker, args=(folder,))
        worker.daemon = True  # 主程式關閉時不卡住
        worker.start()

        self._poll_progress()

    # ---------------------------------------------------------------
    # 掃描（背景執行緒）
    # ---------------------------------------------------------------
    def _scan_worker(self, folder: Path) -> None:
        """在背景執行緒執行掃描。"""
        try:
            result = scanner.scan_directory(
                folder,
                on_progress=self._record_progress,
                on_hash_progress=self._record_hash_progress,
            )
        except Exception as error:  # 保證 GUI 不會整個崩掉
            self._error = str(error)
        else:
            self._result = result

    def _record_progress(self, count: int) -> None:
        """由背景執行緒呼叫，只記錄目前找到幾個檔案。"""
        self._progress = count

    def _record_hash_progress(self, done: int, total: int) -> None:
        """由背景執行緒呼叫，記錄 MD5 比對進度。"""
        self._phase = "hash"  # 進入第二階段，狀態列換成比對訊息
        self._hash_progress = (done, total)

    def _poll_progress(self) -> None:
        """在主執行緒定期檢查掃描是否完成。"""
        if not self._scanning:
            return

        if self._error is not None:
            self._scanning = False
            self._finish_scan()
            return

        if self._result is not None:
            self._scanning = False
            self._finish_scan()
            return

        # 依照目前階段顯示不同的進度訊息
        if self._phase == "scan":
            self.status_var.set(f"正在掃描…已找到 {self._progress:,} 個檔案")
        else:
            done, total = self._hash_progress
            self.status_var.set(
                f"正在比對重複檔案…（MD5 {done:,} / {total:,}）"
            )

        self.root.after(200, self._poll_progress)

    def _finish_scan(self) -> None:
        """掃描結束，把結果畫到畫面上。"""
        self._set_buttons_enabled(True)

        if self._error is not None:
            messagebox.showerror("掃描失敗", self._error)
            self.status_var.set("掃描失敗。")
            return

        result = self._result

        # 第一階段統計
        self.file_count_var.set(f"{result.file_count:,} 個")
        self.total_size_var.set(scanner.format_size(result.total_size))
        self.skipped_var.set(f"{result.skipped_count:,} 個")

        for row_index, file_info in enumerate(result.largest_files, start=1):
            self.table.insert(
                "",
                "end",
                values=(
                    row_index,
                    file_info.path.name,
                    f"{scanner.format_size(file_info.size)}"
                    f"（{file_info.size:,} bytes）",
                    str(file_info.path),
                ),
            )

        # 第二階段統計
        self.duplicate_group_var.set(f"{result.duplicate_group_count:,} 組")
        self.duplicate_file_var.set(f"{result.duplicate_file_count:,} 個")
        self.reclaimable_var.set(scanner.format_size(result.reclaimable_size))

        self._fill_duplicate_table(result)

        # 狀態列
        if result.duplicate_group_count == 0:
            summary = "沒有找到重複檔案。"
        else:
            summary = (
                f"找到 {result.duplicate_group_count:,} 組重複檔案，"
                f"共 {result.duplicate_file_count:,} 個檔案，"
                f"可釋放 {scanner.format_size(result.reclaimable_size)}。"
            )

        self.status_var.set(f"掃描完成：共找到 {result.file_count:,} 個檔案。{summary}")

    def _fill_duplicate_table(self, result: scanner.ScanResult) -> None:
        """把重複檔案依群組填進表格。"""
        for row in self.duplicate_table.get_children():
            self.duplicate_table.delete(row)

        self._row_paths = {}
        self._group_rows = {}
        self._size_by_path = (
            {info.path: info.size for info in result.all_files} if result else {}
        )

        # 沒有重複檔案時要說清楚
        if result.duplicate_group_count == 0:
            self.duplicate_table.insert(
                "",
                "end",
                text="沒有找到重複檔案",
                values=("", "", "", ""),
            )
            return

        for group_index, group in enumerate(result.duplicate_groups, start=1):
            group_row = f"group{group_index}"
            member_rows: List[str] = []

            # 群組標題列：數量、大小、可釋放空間
            self.duplicate_table.insert(
                "",
                "end",
                iid=group_row,
                text=f"重複群組 {group_index}",
                values=(
                    "全選",
                    "取消全選",
                    f"{group.count} 個檔案 · 每個 {scanner.format_size(group.size)}",
                    f"可釋放 {scanner.format_size(group.reclaimable)}",
                ),
                open=True,
                tags=("group",),
            )

            # 群組內的每個檔案
            for file_index, file_info in enumerate(group.files):
                row_id = f"{group_row}_{file_index}"
                self.duplicate_table.insert(
                    group_row,
                    "end",
                    iid=row_id,
                    values=(
                        BOX_UNCHECKED,
                        "",
                        str(file_info.path),
                        scanner.format_size(file_info.size),
                    ),
                )
                self._row_paths[row_id] = file_info.path
                member_rows.append(row_id)

            self._group_rows[group_row] = member_rows

    # ---------------------------------------------------------------
    # 小工具
    # ---------------------------------------------------------------
    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.choose_button.configure(state=state)
        self.scan_button.configure(state=state)

    def _clear_table(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)
        for row in self.duplicate_table.get_children():
            self.duplicate_table.delete(row)

        # 換資料夾重新掃描時，之前的勾選也要清掉
        self._row_paths = {}
        self._group_rows = {}
        self._size_by_path = {}
        self._selected = {}
        self._update_selected_stats()


def main() -> None:
    """啟動程式。"""
    root = tk.Tk()
    CleanerApp(root)
    root.mainloop()