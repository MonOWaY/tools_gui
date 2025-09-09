# gui/tabs/main_tabs.py
"""
Основные вкладки: TXT→Table, Find Duplicates, Remove Duplicates, Email Scanner
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

from config import DEFAULT_ENCODINGS, PREVIEW_LIMIT
from gui.widgets.common import MetricsPanel, FileSelector, SettingsFrame
from gui.utils import run_in_thread, show_error
from core import (
    scan_txt_stats, scan_csv_lines, iter_rows_from_input, write_csv_stream, 
    write_excel_single_or_split, preview_duplicates_csv, preview_duplicates_txt,
    find_duplicates_csv, find_duplicates_txt, dedupe_keep_one, dedupe_txt_keep_one,
    find_email_duplicates_live, parse_delims
)


class MainTabs:
    """Класс для управления основными вкладками приложения."""
    
    def __init__(self, parent, log_widget: ScrolledText):
        self.parent = parent
        self.log = log_widget
        self.init_variables()
        self.create_tabs()
    
    def init_variables(self):
        """(metrics создаём прямо в соответствующих вкладках)"""
        pass

        
        # Find Duplicates
        self.dup_metrics = MetricsPanel(None, {
            "files": "Files: —", 
            "lines": "Lines: —",
            "found": "Duplicates found: —"
        })
        
        # Remove Duplicates
        self.dd_metrics = MetricsPanel(None, {
            "files": "Files: —",
            "before": "Lines Before: —",
            "after": "Lines After: —",
            "removed": "Removed: —"
        })
        
        # Email Scanner
        self.ed_metrics = MetricsPanel(None, {
            "files": "Files: —",
            "lines": "Lines: —", 
            "found": "Problem emails: —"
        })
    
    def create_tabs(self):
        """Создание основных вкладок."""
        self.create_txt2table_tab()
        self.create_find_duplicates_tab()
        self.create_remove_duplicates_tab()
        self.create_email_scanner_tab()
    
    def create_txt2table_tab(self):
        """Вкладка TXT → Table."""
        self.txt_tab = ttk.Frame(self.parent)
        self.parent.add(self.txt_tab, text="TXT → Table")
        
        pad = {'padx': 8, 'pady': 4}
        
        # Input selector with File/Folder buttons
        input_frame = ttk.Frame(self.txt_tab)
        input_frame.grid(row=0, column=0, columnspan=3, sticky='ew', **pad)
        
        ttk.Label(input_frame, text="Input (file or folder):").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.txt_input = ttk.Entry(input_frame, width=70)
        self.txt_input.grid(row=0, column=1, sticky='ew', padx=(0, 6))
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=0, column=2)
        ttk.Button(btn_frame, text="File…", command=self.browse_txt_input_file).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(btn_frame, text="Folder…", command=self.browse_txt_input_folder).grid(row=0, column=1)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Output selector
        self.txt_output_sel = FileSelector(
            self.txt_tab, "Output (.csv or .xlsx):", 
            browse_callback=self.browse_txt_output,
            file_types=[("CSV", "*.csv"), ("Excel", "*.xlsx")]
        )
        self.txt_output_sel.grid(row=1, column=0, columnspan=3, sticky='ew', **pad)
        
        # Settings
        self.txt_settings = SettingsFrame(self.txt_tab)
        self.txt_settings.add_entry("Delimiters:", "delims", "; : \\t |", width=30)
        self.txt_settings.add_combobox("Encoding:", "encoding", DEFAULT_ENCODINGS, "utf-8-sig")
        self.txt_settings.grid(row=2, column=0, columnspan=3, sticky='w', **pad)
        
        # Checkboxes
        self.txt_settings.new_row()
        self.txt_settings.add_checkbox("Recursive", "recursive")
        self.txt_settings.add_checkbox("Include source file", "include_source")
        self.txt_settings.add_checkbox("Keep empty lines", "keep_empty")
        
        # Format preferences
        self.txt_settings.new_row()
        format_frame = ttk.Frame(self.txt_tab)
        format_frame.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        
        ttk.Label(format_frame, text="Prefer:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.txt_format = tk.StringVar(value="auto")
        for i, opt in enumerate(["auto", "csv", "xlsx"]):
            ttk.Radiobutton(format_frame, text=opt, value=opt, variable=self.txt_format).grid(row=0, column=1+i, padx=(0, 6))
        
        self.txt_split_excel = tk.BooleanVar()
        ttk.Checkbutton(format_frame, text="Split Excel parts", variable=self.txt_split_excel).grid(row=0, column=4, padx=(12, 0))
        
        # Headers
        headers_frame = ttk.Frame(self.txt_tab)
        headers_frame.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        
        ttk.Label(headers_frame, text="Column 1 header:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.txt_header1 = ttk.Entry(headers_frame, width=15)
        self.txt_header1.insert(0, "До разделителя")
        self.txt_header1.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(headers_frame, text="Column 2 header:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.txt_header2 = ttk.Entry(headers_frame, width=15)
        self.txt_header2.insert(0, "После разделителя")
        self.txt_header2.grid(row=0, column=3)
        
        # Buttons
        btn_frame = ttk.Frame(self.txt_tab)
        btn_frame.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btn_frame, text="Scan", command=self.scan_txt).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn_frame, text="Run", command=self.run_txt2table).grid(row=0, column=1)
        
        # Metrics
        from gui.widgets.common import MetricsPanel
        self.txt_metrics = MetricsPanel(self.txt_tab, {
            "files": "Files: —",
            "lines": "Lines: —"
        })
        self.txt_metrics.grid(row=7, column=0, columnspan=3, sticky='w', **pad)


        
        self.txt_tab.columnconfigure(0, weight=1)
    
    def create_find_duplicates_tab(self):
        """Вкладка Find Duplicates с preview."""
        container = ttk.Frame(self.parent)
        self.parent.add(container, text="Find Duplicates")
        
        # Левая панель настроек
        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky='nsew', padx=(8, 4))
        
        # Правая панель preview
        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky='nsew', padx=(4, 8))
        
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        
        pad = {'padx': 6, 'pady': 4}
        
        # Input/Output
        self.dup_input_sel = FileSelector(
            left, "Input CSV/TXT:", 
            browse_callback=self.browse_dup_in,
            file_types=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")]
        )
        self.dup_input_sel.grid(row=0, column=0, columnspan=3, sticky='ew', **pad)
        
        self.dup_output_sel = FileSelector(
            left, "Output Duplicates (optional):", 
            browse_callback=self.browse_dup_out,
            file_types=[("CSV/TXT", "*.csv;*.txt")]
        )
        self.dup_output_sel.grid(row=1, column=0, columnspan=3, sticky='ew', **pad)
        
        # Settings
        self.dup_settings = SettingsFrame(left)
        self.dup_settings.add_entry("Separator (CSV):", "separator", ",", width=10)
        self.dup_settings.add_combobox("Encoding:", "encoding", DEFAULT_ENCODINGS, "utf-8-sig")
        self.dup_settings.add_checkbox("Header present (CSV)", "header", True)
        self.dup_settings.add_entry("Batch:", "batch", "20000", width=8)
        self.dup_settings.grid(row=2, column=0, columnspan=3, sticky='w', **pad)
        
        # Preview settings
        prev_frame = ttk.Frame(left)
        prev_frame.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        
        ttk.Label(prev_frame, text="Preview limit:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.dup_preview_limit = ttk.Entry(prev_frame, width=8)
        self.dup_preview_limit.insert(0, str(PREVIEW_LIMIT))
        self.dup_preview_limit.grid(row=0, column=1, padx=(0, 16))
        
        self.dup_unique_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(prev_frame, text="Unique duplicate rows only", variable=self.dup_unique_only).grid(row=0, column=2)
        
        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btn_frame, text="Scan", command=self.scan_dup).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn_frame, text="Preview", command=self.preview_dups).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btn_frame, text="Run (save to file)", command=self.run_find_dups).grid(row=0, column=2)
        
        # Metrics
        from gui.widgets.common import MetricsPanel
        self.dup_metrics = MetricsPanel(left, {
            "files": "Files: —", 
            "lines": "Lines: —",
            "found": "Duplicates found: —"
        })
        self.dup_metrics.grid(row=5, column=0, columnspan=3, sticky='w', **pad)

        
        left.columnconfigure(0, weight=1)
        
        # Preview area
        ttk.Label(right, text="Duplicates preview:").pack(anchor='w', padx=8, pady=(8, 0))
        self.dup_preview = ScrolledText(right, height=20, state='disabled')
        self.dup_preview.pack(fill='both', expand=True, padx=8, pady=8)
    
    def create_remove_duplicates_tab(self):
        """Вкладка Remove Duplicates."""
        self.dd_tab = ttk.Frame(self.parent)
        self.parent.add(self.dd_tab, text="Remove Duplicates")
        
        pad = {'padx': 8, 'pady': 4}
        
        # Input/Output files
        self.dd_input_sel = FileSelector(
            self.dd_tab, "Input CSV/TXT:",
            browse_callback=self.browse_dd_in,
            file_types=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")]
        )
        self.dd_input_sel.grid(row=0, column=0, columnspan=3, sticky='ew', **pad)
        
        self.dd_output_sel = FileSelector(
            self.dd_tab, "Output (deduped):",
            browse_callback=self.browse_dd_out
        )
        self.dd_output_sel.grid(row=1, column=0, columnspan=3, sticky='ew', **pad)
        
        self.dd_dups_sel = FileSelector(
            self.dd_tab, "Duplicates file (optional):",
            browse_callback=self.browse_dd_dups,
            file_types=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")]
        )
        self.dd_dups_sel.grid(row=2, column=0, columnspan=3, sticky='ew', **pad)
        
        # Settings
        self.dd_settings = SettingsFrame(self.dd_tab)
        self.dd_settings.add_entry("Separator (CSV):", "separator", ",", width=10)
        self.dd_settings.add_combobox("Encoding:", "encoding", DEFAULT_ENCODINGS, "utf-8-sig")
        self.dd_settings.add_checkbox("Header present (input)", "header", True)
        self.dd_settings.add_checkbox("Header present (dups)", "dups_header", True)
        self.dd_settings.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        
        # Buttons
        btn_frame = ttk.Frame(self.dd_tab)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btn_frame, text="Scan", command=self.scan_dedup).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn_frame, text="Run", command=self.run_dedup).grid(row=0, column=1)
        
        # Metrics
        from gui.widgets.common import MetricsPanel
        self.dd_metrics = MetricsPanel(self.dd_tab, {
            "files": "Files: —",
            "before": "Lines Before: —",
            "after": "Lines After: —",
            "removed": "Removed: —"
        })
        self.dd_metrics.grid(row=5, column=0, columnspan=3, sticky='w', **pad)

        
        self.dd_tab.columnconfigure(0, weight=1)
    
    def create_email_scanner_tab(self):
        """Вкладка Email Duplicates Scanner."""
        self.ed_tab = ttk.Frame(self.parent)
        self.parent.add(self.ed_tab, text="Email Duplicates Scanner")
        
        pad = {'padx': 6, 'pady': 4}
        
        # Input
        self.ed_input_sel = FileSelector(
            self.ed_tab, "Source CSV:",
            browse_callback=self.browse_ed_in,
            file_types=[("CSV", "*.csv"), ("All", "*.*")]
        )
        self.ed_input_sel.grid(row=0, column=0, columnspan=3, sticky='ew', **pad)
        
        # Column settings
        col_frame = ttk.Frame(self.ed_tab)
        col_frame.grid(row=1, column=0, columnspan=3, sticky='w', **pad)
        
        ttk.Label(col_frame, text="Email column:").grid(row=0, column=0, sticky='e', padx=(0, 6))
        self.ed_col_email = ttk.Entry(col_frame, width=20)
        self.ed_col_email.insert(0, "email")
        self.ed_col_email.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(col_frame, text="Password column:").grid(row=0, column=2, sticky='e', padx=(0, 6))
        self.ed_col_pass = ttk.Entry(col_frame, width=20)
        self.ed_col_pass.insert(0, "pass")
        self.ed_col_pass.grid(row=0, column=3)
        
        # Encoding
        self.ed_settings = SettingsFrame(self.ed_tab)
        self.ed_settings.add_combobox("Encoding:", "encoding", DEFAULT_ENCODINGS, "utf-8")
        self.ed_settings.grid(row=2, column=0, columnspan=3, sticky='w', **pad)
        
        # Output (optional)
        self.ed_output_sel = FileSelector(
            self.ed_tab, "Save found to file (optional):",
            browse_callback=self.browse_ed_out,
            file_types=[("CSV", "*.csv")]
        )
        self.ed_output_sel.grid(row=3, column=0, columnspan=3, sticky='ew', **pad)
        
        # Buttons
        btn_frame = ttk.Frame(self.ed_tab)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btn_frame, text="Scan", command=self.scan_email_dups).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn_frame, text="Find Email Duplicates (Live)", command=self.run_email_dupes).grid(row=0, column=1)
        
        # Metrics
        from gui.widgets.common import MetricsPanel
        self.ed_metrics = MetricsPanel(self.ed_tab, {
            "files": "Files: —",
            "lines": "Lines: —", 
            "found": "Problem emails: —"
        })
        self.ed_metrics.grid(row=5, column=0, columnspan=3, sticky='w', **pad)

        
        # Results area
        ttk.Label(self.ed_tab, text="Found duplicate emails:").grid(row=6, column=0, sticky="nw", **pad)
        self.ed_results = ScrolledText(self.ed_tab, height=12, state='disabled')
        self.ed_results.grid(row=6, column=1, columnspan=2, sticky="nsew", padx=6, pady=6)
        
        self.ed_tab.columnconfigure(1, weight=1)
        self.ed_tab.rowconfigure(6, weight=1)
    
    # ====== Browse Methods ======
    
    def browse_txt_input_file(self):
        path = filedialog.askopenfilename(title="Выбрать TXT файл", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path: self.txt_input.delete(0, 'end'); self.txt_input.insert(0, path)

    def browse_txt_input_folder(self):
        path = filedialog.askdirectory(title="Выбрать папку с TXT")
        if path: self.txt_input.delete(0, 'end'); self.txt_input.insert(0, path)

    def browse_txt_output(self):
        path = filedialog.asksaveasfilename(title="Сохранить как", defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if path: self.txt_output_sel.set_value(path)

    def browse_dup_in(self):
        path = filedialog.askopenfilename(title="Входной файл", filetypes=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")])
        if path: self.dup_input_sel.set_value(path)

    def browse_dup_out(self):
        path = filedialog.asksaveasfilename(title="CSV для дублей", defaultextension=".csv", filetypes=[("CSV/TXT", "*.csv;*.txt")])
        if path: self.dup_output_sel.set_value(path)

    def browse_dd_in(self):
        path = filedialog.askopenfilename(title="Входной файл", filetypes=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")])
        if path: self.dd_input_sel.set_value(path)

    def browse_dd_out(self):
        path = filedialog.asksaveasfilename(title="Файл без дублей", defaultextension=".csv")
        if path: self.dd_output_sel.set_value(path)

    def browse_dd_dups(self):
        path = filedialog.askopenfilename(title="Файл с дублями", filetypes=[("CSV/TXT", "*.csv;*.txt"), ("All", "*.*")])
        if path: self.dd_dups_sel.set_value(path)

    def browse_ed_in(self):
        path = filedialog.askopenfilename(title="Выберите CSV файл", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.ed_input_sel.set_value(path)

    def browse_ed_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить найденные дубли", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path: self.ed_output_sel.set_value(path)
    
    # ====== Scan Methods ======
    
    def scan_txt(self):
        """Сканирование TXT файлов."""
        input_path = Path(self.txt_input.get().strip())
        if not input_path.exists():
            show_error("Ошибка", "Указан неверный входной путь.")
            return
        
        recursive = self.txt_settings.get_value("recursive")
        encoding = self.txt_settings.get_value("encoding")

        def job():
            try:
                self.txt_metrics.update_metric("files", "Files: …")
                self.txt_metrics.update_metric("lines", "Lines: …")
                
                files, lines = scan_txt_stats(input_path, recursive, encoding)
                
                self.txt_metrics.update_metric("files", f"Files: {files:,}")
                self.txt_metrics.update_metric("lines", f"Lines: {lines:,}")
                
                from gui.utils import log_safe
                log_safe(self.log, f"[TXT Scan] Найдено {files} файл(ов), {lines:,} строк")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[TXT Scan] Ошибка: {e}")
                show_error("Ошибка", str(e))
        
        run_in_thread(job)

    def scan_dup(self):
        """Сканирование для Find Duplicates."""
        inp = Path(self.dup_input_sel.get_value())
        if not inp.exists():
            show_error("Ошибка", "Входной файл не найден.")
            return
        
        file_ext = inp.suffix.lower()
        enc = self.dup_settings.get_value("encoding")
        
        def job():
            try:
                self.dup_metrics.update_metric("files", "Files: 1")
                self.dup_metrics.update_metric("lines", "Lines: …")
                
                if file_ext == '.csv':
                    sep = self.dup_settings.get_value("separator") or ","
                    header = self.dup_settings.get_value("header")
                    lines = scan_csv_lines(inp, enc, sep, header)
                else:
                    # TXT файл
                    lines = sum(1 for _ in open(inp, 'r', encoding=enc, errors='replace'))
                
                self.dup_metrics.update_metric("lines", f"Lines: {lines:,}")
                
                from gui.utils import log_safe
                log_safe(self.log, f"[Dup Scan] Файл содержит {lines:,} строк")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Dup Scan] Ошибка: {e}")
                show_error("Ошибка", str(e))
        
        run_in_thread(job)

    def scan_dedup(self):
        """Сканирование для Remove Duplicates."""
        inp = Path(self.dd_input_sel.get_value())
        if not inp.exists():
            show_error("Ошибка", "Входной файл не найден.")
            return
        
        file_ext = inp.suffix.lower()
        enc = self.dd_settings.get_value("encoding")
        dups_path = self.dd_dups_sel.get_value()
        
        def job():
            try:
                files = 1 + (1 if dups_path else 0)
                self.dd_metrics.update_metric("files", f"Files: {files}")
                self.dd_metrics.update_metric("before", "Lines Before: …")
                
                if file_ext == '.csv':
                    sep = self.dd_settings.get_value("separator") or ","
                    header = self.dd_settings.get_value("header")
                    lines_in = scan_csv_lines(inp, enc, sep, header)
                else:
                    # TXT файл
                    lines_in = sum(1 for _ in open(inp, 'r', encoding=enc, errors='replace'))
                
                self.dd_metrics.update_metric("before", f"Lines Before: {lines_in:,}")
                
                from gui.utils import log_safe
                log_safe(self.log, f"[Dedup Scan] Входной файл содержит {lines_in:,} строк")
                
                if dups_path:
                    dups_p = Path(dups_path)
                    if dups_p.exists():
                        if dups_p.suffix.lower() == '.csv':
                            dups_header = self.dd_settings.get_value("dups_header")
                            lines_dups = scan_csv_lines(dups_p, enc, sep, dups_header)
                        else:
                            lines_dups = sum(1 for _ in open(dups_p, 'r', encoding=enc, errors='replace'))
                        log_safe(self.log, f"[Dedup Scan] Файл дублей содержит {lines_dups:,} строк")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Dedup Scan] Ошибка: {e}")
                show_error("Ошибка", str(e))
        
        run_in_thread(job)

    def scan_email_dups(self):
        """Сканирование для Email Scanner."""
        inp = Path(self.ed_input_sel.get_value())
        if not inp.exists():
            show_error("Ошибка", "CSV файл не найден.")
            return
        
        enc = self.ed_settings.get_value("encoding")
        
        def job():
            try:
                self.ed_metrics.update_metric("files", "Files: 1")
                self.ed_metrics.update_metric("lines", "Lines: …")
                
                lines = scan_csv_lines(inp, enc, ",", True)  # Предполагаем заголовок
                self.ed_metrics.update_metric("lines", f"Lines: {lines:,}")
                
                from gui.utils import log_safe
                log_safe(self.log, f"[Email Dup Scan] CSV содержит {lines:,} строк данных")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Email Dup Scan] Ошибка: {e}")
                show_error("Ошибка", str(e))
        
        run_in_thread(job)

    # ====== Run Methods ======
    
    def run_txt2table(self):
        """Запуск TXT → Table."""
        input_path = Path(self.txt_input.get().strip())
        output_path = Path(self.txt_output_sel.get_value())
        
        if not input_path.exists():
            show_error("Ошибка", "Указан неверный входной путь.")
            return
        if not output_path:
            show_error("Ошибка", "Укажи выходной файл (.csv или .xlsx).")
            return

        # Получаем настройки
        delims = parse_delims(self.txt_settings.get_value("delims"))
        encoding = self.txt_settings.get_value("encoding")
        recursive = self.txt_settings.get_value("recursive")
        include_source = self.txt_settings.get_value("include_source")
        keep_empty = self.txt_settings.get_value("keep_empty")
        prefer = self.txt_format.get()
        split_excel = self.txt_split_excel.get()
        
        header1 = self.txt_header1.get().strip() or "До разделителя"
        header2 = self.txt_header2.get().strip() or "После разделителя"

        def job():
            try:
                import time
                from gui.utils import log_safe
                
                start_time = time.time()
                log_safe(self.log, f"[TXT→Table] Старт: {input_path} → {output_path}")
                
                rows_iter = iter_rows_from_input(
                    input_path, delims, keep_empty=keep_empty,
                    recursive=recursive, include_source=include_source, encoding=encoding
                )
                
                ext = output_path.suffix.lower()
                target = {"auto": ("csv" if ext == ".csv" else ("xlsx" if ext == ".xlsx" else "csv")),
                          "csv": "csv", "xlsx": "xlsx"}[prefer]
                
                if target == "csv":
                    csv_path = output_path if ext == ".csv" else output_path.with_suffix(".csv")
                    count = write_csv_stream(rows_iter, csv_path, include_source, header1, header2)
                    self.txt_metrics.update_metric("lines", f"Lines: {count:,}")
                    total_time = time.time() - start_time
                    log_safe(self.log, f"[TXT→Table] Готово за {total_time:.1f}с. Строк: {count:,}. Файл: {csv_path}")
                else:
                    try:
                        xlsx_path = output_path if ext == ".xlsx" else output_path.with_suffix(".xlsx")
                        count = write_excel_single_or_split(rows_iter, xlsx_path, split=split_excel, 
                                                           include_source=include_source, header1=header1, header2=header2)
                        self.txt_metrics.update_metric("lines", f"Lines: {count:,}")
                        total_time = time.time() - start_time
                        log_safe(self.log, f"[TXT→Table] Готово за {total_time:.1f}с. Excel строк: {count:,}.")
                    except OverflowError:
                        csv_path = output_path.with_suffix(".csv")
                        log_safe(self.log, "[TXT→Table] Excel переполнен, переключаюсь на CSV…")
                        rows_iter2 = iter_rows_from_input(
                            input_path, delims, keep_empty=keep_empty,
                            recursive=recursive, include_source=include_source, encoding=encoding
                        )
                        count = write_csv_stream(rows_iter2, csv_path, include_source, header1, header2)
                        self.txt_metrics.update_metric("lines", f"Lines: {count:,}")
                        total_time = time.time() - start_time
                        log_safe(self.log, f"[TXT→Table] Готово за {total_time:.1f}с. Строк: {count:,}. Файл: {csv_path}")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[TXT→Table] Ошибка: {e}")
                show_error("Ошибка", str(e))

        run_in_thread(job)

    def preview_dups(self):
        """Preview дубликатов."""
        inp = Path(self.dup_input_sel.get_value())
        if not inp.exists():
            show_error("Ошибка", "Входной файл не найден.")
            return
        
        file_ext = inp.suffix.lower()
        enc = self.dup_settings.get_value("encoding")
        unique_only = self.dup_unique_only.get()
        
        try:
            limit = int(self.dup_preview_limit.get())
        except:
            limit = PREVIEW_LIMIT

        def job():
            try:
                self.dup_metrics.update_metric("files", "Files: 1")
                self.dup_metrics.update_metric("lines", "Lines: …")
                self.dup_metrics.update_metric("found", "Duplicates found: …")

                if file_ext == '.csv':
                    sep = self.dup_settings.get_value("separator") or ","
                    header = self.dup_settings.get_value("header")
                    lines_total, rows, dups_total = preview_duplicates_csv(
                        inp, encoding=enc, sep=sep, has_header=header,
                        unique_only=unique_only, limit=limit, log=self.log
                    )
                    preview_text = []
                    if header:
                        preview_text.append("[header skipped]\n")
                    for row in rows:
                        preview_text.append(sep.join(row) + '\n')
                else:
                    # TXT файл
                    lines_total, rows, dups_total = preview_duplicates_txt(
                        inp, encoding=enc, unique_only=unique_only, limit=limit, log=self.log
                    )
                    preview_text = [line + '\n' for line in rows]
                
                self.dup_metrics.update_metric("lines", f"Lines: {lines_total:,}")
                self.dup_metrics.update_metric("found", f"Duplicates found: {dups_total:,}")

                def print_preview():
                    self.dup_preview.configure(state='normal')
                    self.dup_preview.delete('1.0', 'end')
                    self.dup_preview.insert('end', ''.join(preview_text))
                    self.dup_preview.configure(state='disabled')
                
                self.parent.after(0, print_preview)

                from gui.utils import log_safe
                log_safe(self.log, f"[Find Dups] Preview готов. Показано {len(rows)} строк (из {dups_total:,}).")

            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Find Dups Preview] Ошибка: {e}")
                show_error("Ошибка", str(e))

        run_in_thread(job)

    def run_find_dups(self):
        """Запуск поиска дубликатов с сохранением в файл."""
        inp = Path(self.dup_input_sel.get_value())
        outp_str = self.dup_output_sel.get_value()
        
        if not inp.exists():
            show_error("Ошибка", "Входной файл не найден.")
            return
        if not outp_str:
            show_error("Ошибка", "Укажи файл для сохранения дублей или используй Preview.")
            return

        outp = Path(outp_str)
        file_ext = inp.suffix.lower()
        enc = self.dup_settings.get_value("encoding")

        def job():
            try:
                from gui.utils import log_safe
                
                self.dup_metrics.update_metric("files", "Files: 1")
                self.dup_metrics.update_metric("lines", "Lines: …")
                self.dup_metrics.update_metric("found", "Duplicates found: …")

                log_safe(self.log, f"[Find Dups] Старт: {inp} → {outp}")
                
                if file_ext == '.csv':
                    sep = self.dup_settings.get_value("separator") or ","
                    header = self.dup_settings.get_value("header")
                    try:
                        batch = int(self.dup_settings.get_value("batch"))
                    except:
                        batch = 20000
                    
                    lines_total, dups_written = find_duplicates_csv(
                        inp, outp, encoding=enc, sep=sep, quotechar='"',
                        has_header=header, batch=batch, log=self.log
                    )
                else:
                    # TXT файл
                    lines_total, dups_written = find_duplicates_txt(inp, outp, encoding=enc, log=self.log)
                
                self.dup_metrics.update_metric("lines", f"Lines: {lines_total:,}")
                self.dup_metrics.update_metric("found", f"Duplicates found: {dups_written:,}")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Find Dups] Ошибка: {e}")
                show_error("Ошибка", str(e))

        run_in_thread(job)

    def run_dedup(self):
        """Запуск Remove Duplicates."""
        inp = Path(self.dd_input_sel.get_value())
        outp_str = self.dd_output_sel.get_value()
        dups_str = self.dd_dups_sel.get_value()
        
        if not inp.exists():
            show_error("Ошибка", "Входной файл не найден.")
            return
        if not outp_str:
            show_error("Ошибка", "Укажи выходной файл.")
            return
        
        outp = Path(outp_str)
        dups = Path(dups_str) if dups_str else None
        file_ext = inp.suffix.lower()
        enc = self.dd_settings.get_value("encoding")

        def job():
            try:
                from gui.utils import log_safe
                
                files = 1 + (1 if dups else 0)
                self.dd_metrics.update_metric("files", f"Files: {files}")
                self.dd_metrics.update_metric("before", "Lines Before: …")
                self.dd_metrics.update_metric("after", "Lines After: …")
                self.dd_metrics.update_metric("removed", "Removed: …")

                log_safe(self.log, f"[Remove Duplicates] Старт: {inp} → {outp}")
                
                if file_ext == '.csv':
                    sep = self.dd_settings.get_value("separator") or ","
                    no_header = not self.dd_settings.get_value("header")
                    dups_header = self.dd_settings.get_value("dups_header")
                    total_in, total_out, dups_lines = dedupe_keep_one(
                        inp, outp, dups, encoding=enc, sep=sep, quotechar='"',
                        no_header=no_header, dups_no_header=not dups_header, log=self.log
                    )
                else:
                    # TXT файл
                    total_in, total_out, dups_lines = dedupe_txt_keep_one(inp, outp, dups, encoding=enc, log=self.log)
                
                self.dd_metrics.update_metric("before", f"Lines Before: {total_in:,}")
                self.dd_metrics.update_metric("after", f"Lines After: {total_out:,}")
                self.dd_metrics.update_metric("removed", f"Removed: {max(0, total_in - total_out):,}")
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Remove Duplicates] Ошибка: {e}")
                show_error("Ошибка", str(e))

        run_in_thread(job)

    def run_email_dupes(self):
        """Запуск Email Duplicates Scanner с live выводом."""
        in_path_str = self.ed_input_sel.get_value()
        col_email = self.ed_col_email.get().strip() or "email"
        col_pass = self.ed_col_pass.get().strip() or "pass"
        enc_in = self.ed_settings.get_value("encoding")
        out_path_str = self.ed_output_sel.get_value()

        if not in_path_str:
            show_error("Ошибка", "Укажи входной CSV.")
            return

        def job():
            try:
                input_csv = Path(in_path_str)
                output_csv = Path(out_path_str) if out_path_str else None
                
                total, count_emails = find_email_duplicates_live(
                    input_csv, col_email, col_pass, enc_in, output_csv, self.log, self.ed_results
                )
                
                self.ed_metrics.update_metric("files", "Files: 1")
                self.ed_metrics.update_metric("lines", f"Lines: {total:,}")
                self.ed_metrics.update_metric("found", f"Problem emails: {count_emails:,}")
                
            except Exception as e:
                from gui.utils import log_safe
                log_safe(self.log, f"[Email Dups] Ошибка: {e}")
                show_error("Ошибка", str(e))

        run_in_thread(job)