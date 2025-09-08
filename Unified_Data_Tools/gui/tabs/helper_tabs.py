# gui/tabs/helper_tabs.py
from __future__ import annotations

from pathlib import Path
from types import MethodType
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# Этот модуль отвечает ТОЛЬКО за построение "вспомогательных" вкладок (tabs 5–11).
# Он ожидает, что у "app" уже есть:
#   - app.notebook: ttk.Notebook
#   - методы-обработчики: browse_* / scan_* / run_* (реализованы в других файлах)
#   - StringVar-метрики: sep_* / copy_* / del_* (инициализированы в main_window.py)

def add_helper_tabs(app) -> None:
    """Создать и добавить все вспомогательные вкладки в notebook приложения."""
    _build_replace_tab(app)
    _build_split_tab(app)
    _build_join_tab(app)
    _build_csv2txt_tab(app)
    _build_delete_by_list_tab(app)
    _build_separator_tab(app)
    _build_copy_files_tab(app)


# ----------------------------- Replace Delimiter ------------------------------

def _build_replace_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="Replace Delimiter")
    app.tab_replace = f  # совместимость по имени

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Input file (.txt):").grid(row=0, column=0, sticky="e", **pad)
    app.rep_in = ttk.Entry(f, width=60)
    app.rep_in.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_rep_in).grid(row=0, column=2)

    ttk.Label(f, text="Output file (.txt):").grid(row=1, column=0, sticky="e", **pad)
    app.rep_out = ttk.Entry(f, width=60)
    app.rep_out.grid(row=1, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_rep_out).grid(row=1, column=2)

    ttk.Label(f, text="Replace:").grid(row=2, column=0, sticky="e", **pad)
    app.rep_old = ttk.Entry(f, width=10)
    app.rep_old.grid(row=2, column=1, sticky="w", **pad)
    app.rep_old.insert(0, ";")

    ttk.Label(f, text="with:").grid(row=2, column=1, sticky="e")
    app.rep_new = ttk.Entry(f, width=10)
    app.rep_new.grid(row=2, column=1, padx=(140, 0), pady=4, sticky="")
    app.rep_new.insert(0, ":")

    frm = ttk.Frame(f)
    frm.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.rep_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.rep_enc_in.set("auto")
    app.rep_enc_in.grid(row=0, column=1, padx=(0, 16))

    ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
    app.rep_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.rep_enc_out.set("utf-8")
    app.rep_enc_out.grid(row=0, column=3)

    ttk.Button(f, text="Run Replace", command=app.run_replace).grid(row=4, column=1, sticky="w", pady=6)
    f.columnconfigure(1, weight=1)


# ------------------------------ Split Email/Pass ------------------------------

def _build_split_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="Split Email/Pass")
    app.tab_split = f

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Source (.txt):").grid(row=0, column=0, sticky="e", **pad)
    app.sp_in = ttk.Entry(f, width=60)
    app.sp_in.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_sp_in).grid(row=0, column=2)

    ttk.Label(f, text="Delimiter:").grid(row=1, column=0, sticky="e", **pad)
    app.sp_delim = ttk.Entry(f, width=10)
    app.sp_delim.grid(row=1, column=1, sticky="w", **pad)
    app.sp_delim.insert(0, ":")

    ttk.Label(f, text="Email → file (.txt):").grid(row=2, column=0, sticky="e", **pad)
    app.sp_out_email = ttk.Entry(f, width=60)
    app.sp_out_email.grid(row=2, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_sp_out_email).grid(row=2, column=2)

    ttk.Label(f, text="Pass → file (.txt):").grid(row=3, column=0, sticky="e", **pad)
    app.sp_out_pass = ttk.Entry(f, width=60)
    app.sp_out_pass.grid(row=3, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_sp_out_pass).grid(row=3, column=2)

    frm = ttk.Frame(f)
    frm.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.sp_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.sp_enc_in.set("auto")
    app.sp_enc_in.grid(row=0, column=1, padx=(0, 16))

    ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
    app.sp_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.sp_enc_out.set("utf-8")
    app.sp_enc_out.grid(row=0, column=3)

    ttk.Button(f, text="Split", command=app.run_split).grid(row=5, column=1, sticky="w", pady=6)
    f.columnconfigure(1, weight=1)


# ----------------------------------- Join -------------------------------------

def _build_join_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="Join Files")
    app.tab_join = f

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Email file (.txt):").grid(row=0, column=0, sticky="e", **pad)
    app.jn_email = ttk.Entry(f, width=60)
    app.jn_email.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_jn_email).grid(row=0, column=2)

    ttk.Label(f, text="Password file (.txt):").grid(row=1, column=0, sticky="e", **pad)
    app.jn_pass = ttk.Entry(f, width=60)
    app.jn_pass.grid(row=1, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_jn_pass).grid(row=1, column=2)

    ttk.Label(f, text="Output (.txt):").grid(row=2, column=0, sticky="e", **pad)
    app.jn_out = ttk.Entry(f, width=60)
    app.jn_out.grid(row=2, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_jn_out).grid(row=2, column=2)

    ttk.Label(f, text="Delimiter:").grid(row=3, column=0, sticky="e", **pad)
    app.jn_delim = ttk.Entry(f, width=10)
    app.jn_delim.grid(row=3, column=1, sticky="w", **pad)
    app.jn_delim.insert(0, ":")

    frm = ttk.Frame(f)
    frm.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.jn_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.jn_enc_in.set("auto")
    app.jn_enc_in.grid(row=0, column=1, padx=(0, 16))

    ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
    app.jn_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.jn_enc_out.set("utf-8")
    app.jn_enc_out.grid(row=0, column=3)

    ttk.Button(f, text="Join", command=app.run_join).grid(row=5, column=1, sticky="w", pady=6)
    f.columnconfigure(1, weight=1)


# -------------------------------- CSV → TXT -----------------------------------

def _build_csv2txt_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="CSV → TXT")
    app.tab_csv2txt = f

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Source (.csv):").grid(row=0, column=0, sticky="e", **pad)
    app.ct_in = ttk.Entry(f, width=60)
    app.ct_in.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_ct_in).grid(row=0, column=2)

    ttk.Label(f, text="Email column name:").grid(row=1, column=0, sticky="e", **pad)
    app.ct_col_email = ttk.Entry(f, width=20)
    app.ct_col_email.grid(row=1, column=1, sticky="w", **pad)
    app.ct_col_email.insert(0, "email")

    ttk.Label(f, text="Password column name:").grid(row=2, column=0, sticky="e", **pad)
    app.ct_col_pass = ttk.Entry(f, width=20)
    app.ct_col_pass.grid(row=2, column=1, sticky="w", **pad)
    app.ct_col_pass.insert(0, "pass")

    ttk.Label(f, text="Delimiter in .txt:").grid(row=3, column=0, sticky="e", **pad)
    app.ct_delim = ttk.Entry(f, width=10)
    app.ct_delim.grid(row=3, column=1, sticky="w", **pad)
    app.ct_delim.insert(0, ":")

    ttk.Label(f, text="Output .txt:").grid(row=4, column=0, sticky="e", **pad)
    app.ct_out = ttk.Entry(f, width=60)
    app.ct_out.grid(row=4, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_ct_out).grid(row=4, column=2)

    frm = ttk.Frame(f)
    frm.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.ct_enc_in = ttk.Combobox(frm, values=["utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.ct_enc_in.set("utf-8")
    app.ct_enc_in.grid(row=0, column=1, padx=(0, 16))

    ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
    app.ct_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.ct_enc_out.set("utf-8")
    app.ct_enc_out.grid(row=0, column=3)

    ttk.Button(f, text="Convert CSV → TXT", command=app.run_csv2txt).grid(row=6, column=1, sticky="w", pady=6)
    f.columnconfigure(1, weight=1)


# ------------------------------ Delete by List --------------------------------

def _build_delete_by_list_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="Delete by List")
    app.tab_delete_list = f

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Source (CSV/TXT):").grid(row=0, column=0, sticky="e", **pad)
    app.del_src = ttk.Entry(f, width=60)
    app.del_src.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_del_src).grid(row=0, column=2)

    ttk.Label(f, text="Delete list (.txt):").grid(row=1, column=0, sticky="e", **pad)
    app.del_list = ttk.Entry(f, width=60)
    app.del_list.grid(row=1, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_del_list).grid(row=1, column=2)

    ttk.Label(f, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
    app.del_out = ttk.Entry(f, width=60)
    app.del_out.grid(row=2, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_del_out).grid(row=2, column=2)

    ttk.Label(f, text="(CSV) Column for matching (optional):").grid(row=3, column=0, sticky="e", **pad)
    app.del_csv_col = ttk.Entry(f, width=20)
    app.del_csv_col.grid(row=3, column=1, sticky="w", **pad)
    app.del_csv_col.insert(0, "")

    app.del_case_ins = tk.BooleanVar(value=True)
    ttk.Checkbutton(f, text="Ignore case and spaces", variable=app.del_case_ins).grid(row=4, column=1, sticky="w")

    frm = ttk.Frame(f)
    frm.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.del_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.del_enc_in.set("auto")
    app.del_enc_in.grid(row=0, column=1, padx=(0, 16))

    ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
    app.del_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
    app.del_enc_out.set("utf-8")
    app.del_enc_out.grid(row=0, column=3)

    ttk.Button(f, text="Delete Rows", command=app.run_delete_by_list).grid(row=6, column=1, sticky="w", pady=6)
    f.columnconfigure(1, weight=1)


# ------------------------------ File Separator --------------------------------

def _build_separator_tab(app):
    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="File Separator")
    app.tab_separator = f

    pad = {"padx": 6, "pady": 4}

    ttk.Label(f, text="Input file (.txt/.csv):").grid(row=0, column=0, sticky="e", **pad)
    app.sep_in = ttk.Entry(f, width=60)
    app.sep_in.grid(row=0, column=1, sticky="we", **pad)
    ttk.Button(f, text="Browse…", command=app.browse_sep_in).grid(row=0, column=2)

    ttk.Label(f, text="Output folder:").grid(row=1, column=0, sticky="e", **pad)
    app.sep_out = ttk.Entry(f, width=60)
    app.sep_out.grid(row=1, column=1, sticky="we", **pad)
    ttk.Button(f, text="Select…", command=app.browse_sep_out).grid(row=1, column=2)

    ttk.Label(f, text="Lines per file:").grid(row=2, column=0, sticky="e", **pad)
    app.sep_lines = ttk.Entry(f, width=10)
    app.sep_lines.grid(row=2, column=1, sticky="w", **pad)
    app.sep_lines.insert(0, "500000")

    frm_fmt = ttk.Frame(f)
    frm_fmt.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm_fmt, text="Output format:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.sep_format = tk.StringVar(value="txt")
    ttk.Radiobutton(frm_fmt, text="txt", value="txt", variable=app.sep_format).grid(row=0, column=1, padx=(0, 12))
    ttk.Radiobutton(frm_fmt, text="csv", value="csv", variable=app.sep_format).grid(row=0, column=2)

    frm_enc = ttk.Frame(f)
    frm_enc.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm_enc, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.sep_enc_in = ttk.Combobox(frm_enc, values=["utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=15, state="readonly")
    app.sep_enc_in.set("utf-8")
    app.sep_enc_in.grid(row=0, column=1)

    btns = ttk.Frame(f)
    btns.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
    ttk.Button(btns, text="Scan", command=app.scan_separator).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="Run Separation", command=app.run_separator).grid(row=0, column=1)

    met = ttk.Frame(f)
    met.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(met, textvariable=app.sep_files_var).grid(row=0, column=0, padx=(0, 20))
    ttk.Label(met, textvariable=app.sep_lines_var).grid(row=0, column=1, padx=(0, 20))
    ttk.Label(met, textvariable=app.sep_parts_var).grid(row=0, column=2)

    f.columnconfigure(1, weight=1)


# ------------------------------ Copy Text Files -------------------------------

def _ensure_on_copy_method_change(app):
    """Локально добавляем обработчик переключения 'Select files'/'Select folder', если его нет."""
    if hasattr(app, "on_copy_method_change"):
        return

    def _on_copy_method_change(self):
        # Перестраиваем правую кнопку в зависимости от выбранного режима
        for w in self.copy_in_frame.winfo_children():
            w.destroy()
        if self.copy_method.get() == "files":
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Files…", command=self.browse_copy_files)
        else:
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Folder…", command=self.browse_copy_folder)
        self.copy_browse_btn.grid(row=0, column=0)

    app.on_copy_method_change = MethodType(_on_copy_method_change, app)


def _build_copy_files_tab(app):
    _ensure_on_copy_method_change(app)

    f = ttk.Frame(app.notebook)
    app.notebook.add(f, text="Copy Text Files")
    app.tab_copy_files = f

    pad = {"padx": 6, "pady": 4}

    frm_method = ttk.Frame(f)
    frm_method.grid(row=0, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm_method, text="Input method:").grid(row=0, column=0, sticky='w', padx=(0, 16))
    app.copy_method = tk.StringVar(value="files")
    ttk.Radiobutton(frm_method, text="Select files", value="files", variable=app.copy_method,
                    command=app.on_copy_method_change).grid(row=0, column=1, padx=(0, 16))
    ttk.Radiobutton(frm_method, text="Select folder", value="folder", variable=app.copy_method,
                    command=app.on_copy_method_change).grid(row=0, column=2)

    ttk.Label(f, text="Input files/folder:").grid(row=1, column=0, sticky="e", **pad)
    app.copy_in = ttk.Entry(f, width=60)
    app.copy_in.grid(row=1, column=1, sticky="we", **pad)

    app.copy_in_frame = ttk.Frame(f)
    app.copy_in_frame.grid(row=1, column=2, **pad)
    app.copy_browse_btn = ttk.Button(app.copy_in_frame, text="Browse Files…", command=app.browse_copy_files)
    app.copy_browse_btn.grid(row=0, column=0)

    ttk.Label(f, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
    app.copy_out = ttk.Entry(f, width=60)
    app.copy_out.grid(row=2, column=1, sticky="we", **pad)
    ttk.Button(f, text="Save As…", command=app.browse_copy_out).grid(row=2, column=2)

    frm_settings = ttk.Frame(f)
    frm_settings.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
    app.copy_recursive = tk.BooleanVar(value=True)
    ttk.Checkbutton(frm_settings, text="Recursive (for folder)", variable=app.copy_recursive).grid(row=0, column=0, padx=(0, 16))

    ttk.Label(frm_settings, text="File pattern:").grid(row=0, column=1, sticky='w', padx=(0, 6))
    app.copy_pattern = ttk.Entry(frm_settings, width=15)
    app.copy_pattern.insert(0, "*.txt")
    app.copy_pattern.grid(row=0, column=2)

    frm_enc = ttk.Frame(f)
    frm_enc.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(frm_enc, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
    app.copy_enc_in = ttk.Combobox(frm_enc, values=["auto", "utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=15, state="readonly")
    app.copy_enc_in.set("auto")
    app.copy_enc_in.grid(row=0, column=1)

    btns = ttk.Frame(f)
    btns.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
    ttk.Button(btns, text="Scan", command=app.scan_copy_files).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="Start Copy Files", command=app.run_copy_files).grid(row=0, column=1)

    met = ttk.Frame(f)
    met.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
    ttk.Label(met, textvariable=app.copy_files_var).grid(row=0, column=0, padx=(0, 20))
    ttk.Label(met, textvariable=app.copy_lines_var).grid(row=0, column=1, padx=(0, 20))
    ttk.Label(met, textvariable=app.copy_total_var).grid(row=0, column=2)

    f.columnconfigure(1, weight=1)
