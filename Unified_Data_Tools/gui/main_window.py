# Unified_Data_Tools/gui/main_window.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog  # + у тебя уже есть messagebox, ttk и т.д.
from pathlib import Path
import csv, math

from gui.utils import log_safe, run_in_thread, show_error, show_info
from core.file_ops import separate_file, copy_text_files
from core.file_utils import detect_encoding



# Импортируем КЛАСС основных вкладок
from gui.tabs.main_tabs import MainTabs  # ← исправили
# Helper-вкладки подключим (UI уже есть), но мы дадим заглушки-обработчики ниже
from gui.tabs.helper_tabs import add_helper_tabs

from gui.utils import show_info  # для заглушек

class MainWindow(tk.Tk):
    """Главное окно приложения Unified Data Tools (модульная версия)."""

    def __init__(self, *, title: str = "Unified Data Tools", geometry: str = "1200x900"):
        super().__init__()
        self.title(title)
        self.geometry(geometry)

        # Строковые метрики, чтобы вкладки могли их обновлять
        self._init_metrics()

        # Общий Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        # Общий лог внизу (создаём РАНЬШЕ вкладок, чтобы прокинуть его в MainTabs)
        self._create_log_section()

        # Основные вкладки (TXT→Table, Find/Remove Duplicates, Email Scanner)
        self.main_tabs = MainTabs(self.notebook, self.log)

        # Вспомогательные вкладки (Replace, Split, Join, CSV→TXT, Delete by List, Separator, Copy Files)
        # Добавляем сразу — ниже есть минимальные обработчики-заглушки
        add_helper_tabs(self)

        # Немного аккуратной темы, если доступна
        try:
            style = ttk.Style()
            style.theme_use("clam")
        except Exception:
            pass

    # ------------------------------ Метрики -----------------------------------

    def _init_metrics(self):
        # TXT → Table
        self.txt_files_var = tk.StringVar(value="Files: —")
        self.txt_lines_var = tk.StringVar(value="Lines: —")

        # Find Duplicates
        self.dup_files_var = tk.StringVar(value="Files: —")
        self.dup_lines_var = tk.StringVar(value="Lines: —")
        self.dup_found_var = tk.StringVar(value="Duplicates found: —")

        # Remove Duplicates
        self.dd_files_var = tk.StringVar(value="Files: —")
        self.dd_lines_var = tk.StringVar(value="Lines: —")
        self.dd_before_var = tk.StringVar(value="Lines Before: —")
        self.dd_after_var = tk.StringVar(value="Lines After: —")
        self.dd_dups_lines_var = tk.StringVar(value="Duplicates Lines: —")
        self.dd_removed_var = tk.StringVar(value="Duplicates removed: —")

        # Email Duplicates
        self.ed_files_var = tk.StringVar(value="Files: —")
        self.ed_lines_var = tk.StringVar(value="Lines: —")
        self.ed_found_var = tk.StringVar(value="Duplicate emails: —")

        # File Separator
        self.sep_files_var = tk.StringVar(value="Files: —")
        self.sep_lines_var = tk.StringVar(value="Lines: —")
        self.sep_parts_var = tk.StringVar(value="Parts created: —")

        # Copy Files
        self.copy_files_var = tk.StringVar(value="Files: —")
        self.copy_lines_var = tk.StringVar(value="Lines: —")
        self.copy_total_var = tk.StringVar(value="Total lines: —")

    # -------------------------- Секция общего лога -----------------------------

    def _create_log_section(self):
        log_frame = ttk.LabelFrame(self, text="Журнал операций")
        log_frame.pack(fill='both', expand=False, padx=8, pady=(0, 8))

        # Делай public — вкладки будут писать сюда
        self.log = ScrolledText(log_frame, height=12, state='disabled')
        self.log.pack(fill='both', expand=True, padx=4, pady=4)

    # -------------------------- Заглушки для helper-вкладок --------------------
    # Эти методы нужны, чтобы кнопки на helper-вкладках не падали.
    # Позже можно заменить содержимым (вызовами core.* + gui.utils.run_in_thread).

        # ====== Helper tabs browsers ======

       # ====== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ======
    def _enc_in(self, enc: str, path: str) -> str:
        return detect_encoding(path) if enc == "auto" else enc

    # ====== Replace Delimiter ======
    def browse_rep_in(self):
        p = filedialog.askopenfilename(title="Выбрать TXT", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.rep_in.delete(0, 'end'); self.rep_in.insert(0, p)

    def browse_rep_out(self):
        p = filedialog.asksaveasfilename(title="Сохранить как", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p: self.rep_out.delete(0, 'end'); self.rep_out.insert(0, p)

    def run_replace(self):
        inp, outp = self.rep_in.get().strip(), self.rep_out.get().strip()
        old, new = self.rep_old.get(), self.rep_new.get()
        enc_in = self.rep_enc_in.get(); enc_out = self.rep_enc_out.get()
        if not inp or not outp: return show_error("Replace", "Укажи входной и выходной файл.")
        def _job():
            ii = self._enc_in(enc_in, inp)
            total = 0
            Path(outp).parent.mkdir(parents=True, exist_ok=True)
            log_safe(self.log, f"[Replace] Старт: {inp} → {outp}  [{old!r} → {new!r}]")
            with open(inp, 'r', encoding=ii, errors='replace') as f, \
                 open(outp, 'w', encoding=enc_out, newline='') as g:
                for total, line in enumerate(f, 1):
                    g.write(line.replace(old, new))
                    if total % 100000 == 0:
                        log_safe(self.log, f"[Replace] {total:,} строк…")
            log_safe(self.log, f"[Replace] Готово: {total:,} строк.")
        run_in_thread(_job)

    # ====== Split Email/Pass ======
    def browse_sp_in(self):
        p = filedialog.askopenfilename(title="Файл для разделения", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.sp_in.delete(0, 'end'); self.sp_in.insert(0, p)

    def browse_sp_out_email(self):
        p = filedialog.asksaveasfilename(title="Сохранить email", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p: self.sp_out_email.delete(0, 'end'); self.sp_out_email.insert(0, p)

    def browse_sp_out_pass(self):
        p = filedialog.asksaveasfilename(title="Сохранить pass", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p: self.sp_out_pass.delete(0, 'end'); self.sp_out_pass.insert(0, p)

    def run_split(self):
        src = self.sp_in.get().strip()
        out_e = self.sp_out_email.get().strip()
        out_p = self.sp_out_pass.get().strip()
        delim = self.sp_delim.get() or ":"
        enc_in = self.sp_enc_in.get(); enc_out = self.sp_enc_out.get()
        if not src or not out_e or not out_p:
            return show_error("Split", "Укажи входной и 2 выходных файла.")
        def _job():
            ii = self._enc_in(enc_in, src)
            total = 0
            Path(out_e).parent.mkdir(parents=True, exist_ok=True)
            Path(out_p).parent.mkdir(parents=True, exist_ok=True)
            log_safe(self.log, f"[Split] Старт: {src} → ({out_e}, {out_p})  delim={delim!r}")
            with open(src, 'r', encoding=ii, errors='replace') as f, \
                 open(out_e, 'w', encoding=enc_out, newline='') as fe, \
                 open(out_p, 'w', encoding=enc_out, newline='') as fp:
                for total, line in enumerate(f, 1):
                    s = line.rstrip("\n\r")
                    a, b = (s.split(delim, 1) + [""])[:2]
                    fe.write(a + "\n")
                    fp.write(b + "\n")
                    if total % 100000 == 0:
                        log_safe(self.log, f"[Split] {total:,} строк…")
            log_safe(self.log, f"[Split] Готово: {total:,} строк.")
        run_in_thread(_job)

    # ====== Join Files ======
    def browse_jn_email(self):
        p = filedialog.askopenfilename(title="Файл email", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.jn_email.delete(0, 'end'); self.jn_email.insert(0, p)

    def browse_jn_pass(self):
        p = filedialog.askopenfilename(title="Файл паролей", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.jn_pass.delete(0, 'end'); self.jn_pass.insert(0, p)

    def browse_jn_out(self):
        p = filedialog.asksaveasfilename(title="Сохранить объединённый", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p: self.jn_out.delete(0, 'end'); self.jn_out.insert(0, p)

    def run_join(self):
        fe, fp = self.jn_email.get().strip(), self.jn_pass.get().strip()
        outp = self.jn_out.get().strip()
        delim = self.jn_delim.get() or ":"
        enc_in = self.jn_enc_in.get(); enc_out = self.jn_enc_out.get()
        if not fe or not fp or not outp: 
            return show_error("Join", "Укажи файл email, файл pass и выходной файл.")
        def _job():
            ii = self._enc_in(enc_in, fe)
            jj = self._enc_in(enc_in, fp)
            total = 0
            Path(outp).parent.mkdir(parents=True, exist_ok=True)
            log_safe(self.log, f"[Join] Старт: {fe} + {fp} → {outp}  delim={delim!r}")
            with open(fe, 'r', encoding=ii, errors='replace') as e, \
                 open(fp, 'r', encoding=jj, errors='replace') as p, \
                 open(outp, 'w', encoding=enc_out, newline='') as g:
                for total, (le, lp) in enumerate(zip(e, p), 1):
                    g.write(le.rstrip("\n\r") + delim + lp.lstrip("\n\r"))
                    if total % 100000 == 0:
                        log_safe(self.log, f"[Join] {total:,} строк…")
            log_safe(self.log, f"[Join] Готово: {total:,} строк.")
        run_in_thread(_job)

    # ====== CSV → TXT ======
    def browse_ct_in(self):
        p = filedialog.askopenfilename(title="CSV", filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if p: self.ct_in.delete(0, 'end'); self.ct_in.insert(0, p)

    def browse_ct_out(self):
        p = filedialog.asksaveasfilename(title="TXT", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p: self.ct_out.delete(0, 'end'); self.ct_out.insert(0, p)

    def run_csv2txt(self):
        src = self.ct_in.get().strip()
        outp = self.ct_out.get().strip()
        col_e = (self.ct_col_email.get() or "email").strip()
        col_p = (self.ct_col_pass.get() or "pass").strip()
        delim = self.ct_delim.get() or ":"
        enc_in = self.ct_enc_in.get(); enc_out = self.ct_enc_out.get()
        if not src or not outp:
            return show_error("CSV→TXT", "Укажи входной CSV и выходной TXT.")
        def _job():
            ii = enc_in  # для CSV авто-детект редко нужен; можно добавить при желании
            total = 0
            Path(outp).parent.mkdir(parents=True, exist_ok=True)
            log_safe(self.log, f"[CSV→TXT] Старт: {src} → {outp}  [{col_e!r},{col_p!r}] delim={delim!r}")
            with open(src, 'r', encoding=ii, newline='') as f, \
                 open(outp, 'w', encoding=enc_out, newline='') as g:
                r = csv.DictReader(f)
                if not r.fieldnames or col_e not in r.fieldnames or col_p not in r.fieldnames:
                    return show_error("CSV→TXT", f"Колонки не найдены. Есть: {r.fieldnames}")
                for total, row in enumerate(r, 1):
                    g.write(f"{row.get(col_e,'')}{delim}{row.get(col_p,'')}\n")
                    if total % 100000 == 0:
                        log_safe(self.log, f"[CSV→TXT] {total:,} строк…")
            log_safe(self.log, f"[CSV→TXT] Готово: {total:,} строк.")
        run_in_thread(_job)

    # ====== Delete by List ======
    def browse_del_src(self):
        p = filedialog.askopenfilename(title="Источник (CSV/TXT)",
                                       filetypes=[("CSV/TXT", "*.csv;*.txt"), ("CSV", "*.csv"), ("Text", "*.txt"), ("All files", "*.*")])
        if p: self.del_src.delete(0, 'end'); self.del_src.insert(0, p)

    def browse_del_list(self):
        p = filedialog.askopenfilename(title="Список для удаления", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.del_list.delete(0, 'end'); self.del_list.insert(0, p)

    def browse_del_out(self):
        p = filedialog.asksaveasfilename(title="Сохранить результат", defaultextension=".txt", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.del_out.delete(0, 'end'); self.del_out.insert(0, p)

    def run_delete_by_list(self):
        src = self.del_src.get().strip()
        lst = self.del_list.get().strip()
        outp = self.del_out.get().strip()
        col = (self.del_csv_col.get() or "").strip()
        enc_in = self.del_enc_in.get(); enc_out = self.del_enc_out.get()
        ignore = self.del_case_ins.get()
        if not src or not lst or not outp:
            return show_error("Delete by List", "Укажи исходный файл, список и выходной файл.")
        def norm(s: str) -> str:
            s = s.strip()
            return s.lower().replace(" ", "") if ignore else s
        def _job():
            ii = self._enc_in(enc_in, src)
            with open(lst, 'r', encoding=self._enc_in(enc_in, lst), errors='replace') as f:
                killers = {norm(x) for x in f if x.strip()}
            total, kept = 0, 0
            Path(outp).parent.mkdir(parents=True, exist_ok=True)
            log_safe(self.log, f"[Delete] Старт: {src} – список {len(killers):,} шт → {outp}")
            if src.lower().endswith(".csv"):
                with open(src, 'r', encoding=ii, newline='', errors='replace') as f, \
                     open(outp, 'w', encoding=enc_out, newline='') as g:
                    r = csv.DictReader(f)
                    if col:
                        if not r.fieldnames or col not in r.fieldnames:
                            return show_error("Delete by List", f"Колонка {col!r} не найдена. Есть: {r.fieldnames}")
                        w = csv.DictWriter(g, fieldnames=r.fieldnames); w.writeheader()
                        for row in r:
                            total += 1
                            if norm(str(row.get(col,""))) in killers: continue
                            w.writerow(row); kept += 1
                    else:
                        # без колонки — считаем первой колонкой
                        f.seek(0); rr = csv.reader(f)
                        headers = next(rr, None)
                        if headers:
                            ww = csv.writer(g); ww.writerow(headers)
                        for row in rr:
                            total += 1
                            key = norm(row[0] if row else "")
                            if key in killers: continue
                            ww.writerow(row); kept += 1
            else:  # TXT
                with open(src, 'r', encoding=ii, errors='replace') as f, \
                     open(outp, 'w', encoding=enc_out, newline='') as g:
                    for line in f:
                        total += 1
                        if norm(line) in killers: continue
                        g.write(line); kept += 1
            log_safe(self.log, f"[Delete] Готово: всего {total:,}, осталось {kept:,}.")
        run_in_thread(_job)

    # ====== File Separator ======
    def browse_sep_in(self):
        p = filedialog.askopenfilename(title="Файл для разделения", filetypes=[("Text/CSV", "*.txt;*.csv"), ("All files", "*.*")])
        if p: self.sep_in.delete(0, 'end'); self.sep_in.insert(0, p)

    def browse_sep_out(self):
        p = filedialog.askdirectory(title="Папка для результатов")
        if p: self.sep_out.delete(0, 'end'); self.sep_out.insert(0, p)

    def scan_separator(self):
        src = self.sep_in.get().strip()
        if not src: return show_error("File Separator", "Укажи входной файл.")
        enc = self.sep_enc_in.get()
        ii = self._enc_in(enc, src)
        lines = 0
        with open(src, 'r', encoding=ii, errors='replace') as f:
            for lines, _ in enumerate(f, 1): pass
        parts = 0
        try:
            n = int(self.sep_lines.get().strip() or "0")
            parts = math.ceil(lines / n) if n > 0 else 0
        except Exception:
            parts = 0
        self.sep_files_var.set("Files: 1")
        self.sep_lines_var.set(f"Lines: {lines:,}")
        self.sep_parts_var.set(f"Parts created: {parts:,}")

    def run_separator(self):
        src = self.sep_in.get().strip()
        outdir = self.sep_out.get().strip()
        fmt = self.sep_format.get() or "txt"
        enc = self.sep_enc_in.get()
        try:
            lines_per = int(self.sep_lines.get().strip())
        except Exception:
            return show_error("File Separator", "Неверное значение Lines per file.")
        if not src or not outdir: return show_error("File Separator", "Укажи входной файл и папку вывода.")
        def _job():
            ii = self._enc_in(enc, src)
            total_lines, parts = separate_file(Path(src), Path(outdir), lines_per, fmt, ii, log=self.log)
            self.sep_files_var.set("Files: 1")
            self.sep_lines_var.set(f"Lines: {total_lines:,}")
            self.sep_parts_var.set(f"Parts created: {parts:,}")
        run_in_thread(_job)

    # ====== Copy Text Files ======
    def browse_copy_files(self):
        ps = filedialog.askopenfilenames(title="Выбрать файлы", filetypes=[("Text/CSV", "*.txt;*.csv"), ("All files", "*.*")])
        if ps: self.copy_in.delete(0,'end'); self.copy_in.insert(0, "; ".join(ps))

    def browse_copy_folder(self):
        p = filedialog.askdirectory(title="Папка с файлами")
        if p: self.copy_in.delete(0,'end'); self.copy_in.insert(0, p)

    def browse_copy_out(self):
        p = filedialog.asksaveasfilename(title="Сохранить объединённый", defaultextension=".txt",
                                         filetypes=[("Text", "*.txt"), ("CSV", "*.csv")])
        if p: self.copy_out.delete(0, 'end'); self.copy_out.insert(0, p)

    def scan_copy_files(self):
        method = self.copy_method.get()
        enc = self.copy_enc_in.get()
        paths = []
        if method == "files":
            raw = self.copy_in.get().strip()
            if raw:
                paths = [Path(s.strip()) for s in raw.split(";") if s.strip()]
        else:
            folder = Path(self.copy_in.get().strip())
            if folder.is_dir():
                pat = self.copy_pattern.get().strip() or "*.txt"
                pattern = f"**/{pat}" if self.copy_recursive.get() else pat
                paths = list(folder.glob(pattern))
        total_lines = 0
        for p in paths:
            ii = self._enc_in(enc, str(p))
            try:
                with open(p, 'r', encoding=ii, errors='replace') as f:
                    for total_lines, _ in enumerate(f, 1): pass
            except Exception:
                pass
        self.copy_files_var.set(f"Files: {len(paths)}")
        self.copy_lines_var.set(f"Lines: {total_lines:,}")
        self.copy_total_var.set(f"Total lines: {total_lines:,}")

    def run_copy_files(self):
        outp = self.copy_out.get().strip()
        if not outp: return show_error("Copy Text Files", "Укажи выходной файл.")
        method = self.copy_method.get()
        enc = self.copy_enc_in.get()
        if method == "files":
            raw = self.copy_in.get().strip()
            files = [Path(s.strip()) for s in raw.split(";") if s.strip()]
        else:
            folder = Path(self.copy_in.get().strip())
            pat = self.copy_pattern.get().strip() or "*.txt"
            pattern = f"**/{pat}" if self.copy_recursive.get() else pat
            files = list(folder.glob(pattern)) if folder.is_dir() else []
        if not files:
            return show_error("Copy Text Files", "Не выбраны входные файлы.")
        def _job():
            ii = enc  # для копирования допускаем единую кодировку чтения
            total_files, total_lines = copy_text_files(files, Path(outp), ii, log=self.log)
            self.copy_files_var.set(f"Files: {total_files}")
            self.copy_lines_var.set(f"Lines: {total_lines:,}")
            self.copy_total_var.set(f"Total lines: {total_lines:,}")
        run_in_thread(_job)

    # переключатель режима (files/folder) — если его нет, helper_tabs добавляет локально,
    # но мы оставим реализацию здесь, чтобы точно работать.
    def on_copy_method_change(self):
        for w in self.copy_in_frame.winfo_children():
            w.destroy()
        if self.copy_method.get() == "files":
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Files…", command=self.browse_copy_files)
        else:
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Folder…", command=self.browse_copy_folder)
        self.copy_browse_btn.grid(row=0, column=0)


    # Для переключателя режима в Copy Text Files (files/folder).
    # Если уже реализован — оставь свой.
    def on_copy_method_change(self):
        for w in self.copy_in_frame.winfo_children():
            w.destroy()
        if self.copy_method.get() == "files":
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Files…", command=self.browse_copy_files)
        else:
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Folder…", command=self.browse_copy_folder)
        self.copy_browse_btn.grid(row=0, column=0)



def run():
    app = MainWindow(title="Unified Data Tools - Полный набор инструментов для работы с данными")
    app.mainloop()


if __name__ == "__main__":
    run()
