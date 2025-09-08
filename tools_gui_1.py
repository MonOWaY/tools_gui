#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Data Tools - Объединенное приложение для работы с TXT и CSV файлами

Основные функции:
- TXT → Table (CSV/XLSX) с поддержкой больших файлов
- Find Duplicates с preview и live-режимом
- Remove Duplicates с опциональным файлом дублей
- Email Duplicates Scanner (live-режим для поиска повторных email с разными паролями)

Вспомогательные функции:
- Замена разделителя в TXT файлах
- Разделение файлов email:pass
- Объединение файлов email + pass
- CSV → TXT конвертация
- Удаление строк по списку

Требования: pip install pandas openpyxl chardet
"""

import csv
import sqlite3
import threading
import time
from pathlib import Path
from typing import Iterable, Tuple, List, Optional, Iterator, Set, Dict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# Для авто-детекта кодировки
try:
    import chardet
except ImportError:
    chardet = None

# ====== Общие утилиты =========================================================

DEFAULT_DELIMS = [';', ':']
EXCEL_MAX_ROWS = 1_048_576
EXCEL_DATA_ROWS_LIMIT = EXCEL_MAX_ROWS - 1
US = "\x1f"  # технический разделитель для ключей

def detect_encoding(file_path: str, default="utf-8") -> str:
    """Пытается угадать кодировку (использует chardet при наличии)."""
    if not chardet:
        return default
    try:
        with open(file_path, "rb") as f:
            raw = f.read(200_000)
        res = chardet.detect(raw) or {}
        enc = (res.get("encoding") or "").lower()
        return enc or default
    except Exception:
        return default

def decode_escapes(s: str) -> str:
    """Декодирует escape-последовательности типа \\t, \\n."""
    try:
        return bytes(s, 'utf-8').decode('unicode_escape')
    except Exception:
        return s

def parse_delims_input(delims_text: str) -> List[str]:
    """Строка вида ': ; |' или ':\n;\n|' -> список возможных разделителей."""
    delims = []
    for part in delims_text.replace(",", "\n").splitlines():
        s = part.strip()
        if s:
            delims.append(s)
    return delims or [":"]

def parse_delims(text: str) -> List[str]:
    """Парсинг разделителей для TXT→Table."""
    if not text.strip():
        return DEFAULT_DELIMS[:]
    raw = [p.strip().strip('"').strip("'") for p in text.replace(',', ' ').split()]
    return [decode_escapes(p) for p in raw if p] or DEFAULT_DELIMS[:]

def row_to_key(row: List[str]) -> str:
    """Преобразует строку CSV в уникальный ключ."""
    return US.join("" if x is None else x for x in row)

def key_to_row(key: str) -> List[str]:
    """Обратное преобразование ключа в строку."""
    return key.split(US)

def log_safe(widget: ScrolledText, text: str):
    """Потокобезопасное добавление текста в лог."""
    def _do():
        widget.configure(state='normal')
        widget.insert('end', text + '\n')
        widget.see('end')
        widget.configure(state='disabled')
        widget.update_idletasks()
    
    try:
        widget.after(0, _do)
    except:
        # Если виджет недоступен, просто печатаем
        print(text)

def safe_mkdirs(filepath: str):
    """Создает директории для файла."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

def split_once_multi(line: str, delims: List[str]) -> Optional[Tuple[str, str]]:
    """Разделяет строку по первому встретившемуся разделителю из списка."""
    for d in delims:
        if d in line:
            left, right = line.split(d, 1)
            return left.strip(), right.strip()
    return None

def find_split(line: str, delims: List[str]) -> Tuple[str, str]:
    """Находит первый разделитель и разбивает строку."""
    first_pos: Optional[int] = None
    first_len: int = 0
    for d in delims:
        if not d:
            continue
        pos = line.find(d)
        if pos != -1 and (first_pos is None or pos < first_pos):
            first_pos = pos
            first_len = len(d)
    if first_pos is None:
        return line.strip(), ''
    return line[:first_pos].strip(), line[first_pos + first_len:].strip()

# ====== TXT → Table функции ===================================================

def iter_rows_from_file(txt_path: Path, delims: List[str], keep_empty: bool,
                        source_name: Optional[str], encoding: str) -> Iterator[Tuple[str, str, Optional[str]]]:
    """Итератор строк из файла."""
    with open(txt_path, 'r', encoding=encoding, errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n\r')
            if not line.strip():
                if keep_empty:
                    yield ('', '', source_name)
                else:
                    continue
            before, after = find_split(line, delims)
            yield (before, after, source_name)

def iter_rows_from_input(input_path: Path, delims: List[str], keep_empty: bool,
                         recursive: bool, include_source: bool, encoding: str) -> Iterable[Tuple[str, str, str]]:
    """Итератор строк из файла или папки."""
    if input_path.is_file():
        src = input_path.name if include_source else ''
        for before, after, _ in iter_rows_from_file(input_path, delims, keep_empty, src, encoding):
            yield before, after, src
    elif input_path.is_dir():
        pattern = "**/*.txt" if recursive else "*.txt"
        files = sorted(input_path.glob(pattern))
        for f in files:
            src = f.name if include_source else ''
            for before, after, _ in iter_rows_from_file(f, delims, keep_empty, src, encoding):
                yield before, after, src
    else:
        raise FileNotFoundError(f"Путь не найден: {input_path}")

def write_csv_stream(rows: Iterable[Tuple[str, str, str]], csv_path: Path, include_source: bool, 
                     header1: str = "Before separator", header2: str = "After separator") -> int:
    """Записывает данные в CSV файл."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if include_source:
            w.writerow(['source_file', header1, header2])
        else:
            w.writerow([header1, header2])
        for before, after, source in rows:
            if include_source:
                w.writerow([source, before, after])
            else:
                w.writerow([before, after])
            count += 1
    return count

def write_excel_single_or_split(rows: Iterable[Tuple[str, str, str]],
                                base_xlsx_path: Path,
                                split: bool,
                                include_source: bool,
                                header1: str = "Before separator", 
                                header2: str = "After separator") -> int:
    """Записывает данные в Excel файл(ы)."""
    import pandas as pd
    base_xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    def new_writer(path: Path):
        return pd.ExcelWriter(path, engine='openpyxl', mode='w')

    def open_new_part(idx: int):
        path = base_xlsx_path if not split else _suffix_path(base_xlsx_path, idx)
        w = new_writer(path)
        cols = (['source_file'] if include_source else []) + [header1, header2]
        pd.DataFrame(columns=cols).to_excel(w, sheet_name='Sheet1', index=False, startrow=0)
        return w

    part_idx = 1
    writer = open_new_part(part_idx)
    rows_written_total = 0
    rows_in_current_file = 0
    startrow = 1

    buf_source: List[str] = []
    buf_before: List[str] = []
    buf_after: List[str] = []
    BUF_SIZE = 50_000

    def flush_buffer():
        nonlocal startrow, rows_in_current_file, rows_written_total, writer, part_idx
        if not buf_before:
            return
        n = len(buf_before)
        if not split and rows_in_current_file + n > EXCEL_DATA_ROWS_LIMIT:
            raise OverflowError("Excel лист переполнен")
        if split and rows_in_current_file + n > EXCEL_DATA_ROWS_LIMIT:
            writer.close()
            part_idx += 1
            writer = open_new_part(part_idx)
            startrow = 1
            rows_in_current_file = 0
        data = {}
        if include_source:
            data['source_file'] = buf_source
        data[header1] = buf_before
        data[header2] = buf_after
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Sheet1', index=False, header=False, startrow=startrow)
        startrow += n
        rows_in_current_file += n
        rows_written_total += n
        buf_source.clear(); buf_before.clear(); buf_after.clear()

    try:
        for before, after, source in rows:
            if include_source:
                buf_source.append(source)
            buf_before.append(before)
            buf_after.append(after)
            if len(buf_before) >= BUF_SIZE:
                flush_buffer()
        flush_buffer()
        writer.close()
        return rows_written_total
    finally:
        try:
            if writer:
                writer.close()
        except Exception:
            pass

def _suffix_path(path: Path, idx: int) -> Path:
    """Добавляет суффикс к имени файла."""
    return path.with_name(f"{path.stem}_part{idx:03d}{path.suffix}")

# ====== Сканеры файлов ========================================================

def scan_txt_stats(input_path: Path, recursive: bool, encoding: str) -> Tuple[int, int]:
    """Возвращает (files_count, lines_total) для TXT входа."""
    if input_path.is_file():
        files = 1
        lines = sum(1 for _ in open(input_path, 'r', encoding=encoding, errors='replace'))
        return files, lines
    elif input_path.is_dir():
        pattern = "**/*.txt" if recursive else "*.txt"
        files_list = list(input_path.glob(pattern))
        total = 0
        for p in files_list:
            total += sum(1 for _ in open(p, 'r', encoding=encoding, errors='replace'))
        return len(files_list), total
    else:
        raise FileNotFoundError(str(input_path))

def scan_csv_lines(csv_path: Path, encoding: str, sep: str, has_header: bool) -> int:
    """Считает количество строк-данных (без заголовка)."""
    sep = decode_escapes(sep)
    with open(csv_path, 'r', encoding=encoding, newline='') as f:
        r = csv.reader(f, delimiter=sep, quotechar='"')
        first = next(r, None)
        if first is None:
            return 0
        count = 0
        if not has_header:
            count += 1
        for _ in r:
            count += 1
        return count

# ====== Find Duplicates =======================================================

# ====== Find/Remove Duplicates for TXT files ================================

def find_duplicates_txt(input_txt: Path, output_txt: Path, encoding: str,
                        log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Находит дубликаты в TXT файле."""
    start_time = time.time()
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    
    line_counts = {}
    lines_total = 0
    
    with open(input_txt, 'r', encoding=encoding, errors='replace') as f:
        for line in f:
            clean_line = line.rstrip('\n\r')
            lines_total += 1
            line_counts[clean_line] = line_counts.get(clean_line, 0) + 1
            
            if lines_total % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Find Dups TXT] Прочитано строк: {lines_total:,} за {elapsed:.1f}с…")
    
    dups_written = 0
    with open(output_txt, 'w', encoding='utf-8', newline='') as f:
        for line, count in line_counts.items():
            if count > 1:
                for _ in range(count):
                    f.write(line + '\n')
                    dups_written += 1
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Find Dups TXT] Готово за {total_time:.1f}с. Дубликаты сохранены: {output_txt}")
    return lines_total, dups_written

def preview_duplicates_txt(input_txt: Path, encoding: str, unique_only: bool, limit: int,
                           log: Optional[ScrolledText] = None) -> Tuple[int, List[str], int]:
    """Preview дубликатов в TXT файле."""
    start_time = time.time()
    line_counts = {}
    lines_total = 0
    
    with open(input_txt, 'r', encoding=encoding, errors='replace') as f:
        for line in f:
            clean_line = line.rstrip('\n\r')
            lines_total += 1
            line_counts[clean_line] = line_counts.get(clean_line, 0) + 1
            
            if lines_total % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Find Dups TXT] Прочитано строк: {lines_total:,} за {elapsed:.1f}с…")
    
    preview: List[str] = []
    total_dup_lines = 0
    dup_unique = 0
    
    for line, count in line_counts.items():
        if count > 1:
            dup_unique += 1
            total_dup_lines += count
            if unique_only:
                if len(preview) < limit:
                    preview.append(line)
            else:
                for _ in range(count):
                    if len(preview) < limit:
                        preview.append(line)
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Find Dups TXT] Найдено уникальных дублей: {dup_unique:,}; всего строк-дубликатов: {total_dup_lines:,} за {total_time:.1f}с.")
    return lines_total, preview, total_dup_lines

def dedupe_txt_keep_one(input_txt: Path, output_txt: Path, dups_txt: Optional[Path],
                        encoding: str, log: Optional[ScrolledText] = None) -> Tuple[int, int, Optional[int]]:
    """Удаление дубликатов из TXT файла."""
    start_time = time.time()
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    
    dup_lines = set()
    dups_lines_count: Optional[int] = None
    
    if dups_txt:
        dups_lines_count = 0
        with open(dups_txt, 'r', encoding=encoding, errors='replace') as f:
            for line in f:
                clean_line = line.rstrip('\n\r')
                dup_lines.add(clean_line)
                dups_lines_count += 1
        if log: log_safe(log, f"Загружено строк дублей: {len(dup_lines):,}")
    
    seen_lines = set()
    kept_from_dups = set()
    total_in = 0
    total_out = 0
    
    with open(input_txt, 'r', encoding=encoding, errors='replace') as fin, \
         open(output_txt, 'w', encoding='utf-8', newline='') as fout:
        
        for line in fin:
            clean_line = line.rstrip('\n\r')
            total_in += 1
            
            if dup_lines:
                if clean_line in dup_lines:
                    if clean_line in kept_from_dups:
                        continue
                    kept_from_dups.add(clean_line)
                    fout.write(clean_line + '\n')
                    total_out += 1
                else:
                    fout.write(clean_line + '\n')
                    total_out += 1
            else:
                if clean_line in seen_lines:
                    continue
                seen_lines.add(clean_line)
                fout.write(clean_line + '\n')
                total_out += 1
            
            if total_in % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Remove Duplicates TXT] Обработано строк: {total_in:,} за {elapsed:.1f}с")
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Remove Duplicates TXT] Готово за {total_time:.1f}с. Итог сохранён: {output_txt}")
    return total_in, total_out, dups_lines_count

# ====== Find/Remove Duplicates for CSV files ================================

def preview_duplicates_csv(input_csv: Path, encoding: str, sep: str, has_header: bool,
                           unique_only: bool, limit: int, log: Optional[ScrolledText] = None) -> Tuple[int, List[List[str]], int]:
    """Preview дубликатов в CSV файле."""
    start_time = time.time()
    rows_by_key: Dict[str, List[List[str]]] = {}
    rows_total = 0
    
    with open(input_csv, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.reader(f, delimiter=sep)
        
        if has_header:
            headers = next(reader, None)
            if headers:
                rows_total += 1
        
        for row in reader:
            rows_total += 1
            if not row:  # Skip empty rows
                continue
                
            # Create key from all columns for duplicate detection
            key = sep.join(str(cell).strip() for cell in row)
            if key not in rows_by_key:
                rows_by_key[key] = []
            rows_by_key[key].append(row)
            
            if rows_total % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Find Dups CSV] Прочитано строк: {rows_total:,} за {elapsed:.1f}с…")
    
    preview: List[List[str]] = []
    total_dup_rows = 0
    dup_unique = 0
    
    for key, rows in rows_by_key.items():
        if len(rows) > 1:
            dup_unique += 1
            total_dup_rows += len(rows)
            if unique_only:
                if len(preview) < limit:
                    preview.append(rows[0])  # Show only one instance
            else:
                for row in rows:
                    if len(preview) < limit:
                        preview.append(row)
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Find Dups CSV] Найдено уникальных дублей: {dup_unique:,}; всего строк-дубликатов: {total_dup_rows:,} за {total_time:.1f}с.")
    return rows_total, preview, total_dup_rows

def find_duplicates_csv(input_csv: Path, output_csv: Path, encoding: str, sep: str, quotechar: str,
                        has_header: bool, batch: int, log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Находит дубликаты в CSV файле."""
    start_time = time.time()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    rows_by_key: Dict[str, List[List[str]]] = {}
    rows_total = 0
    
    with open(input_csv, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.reader(f, delimiter=sep, quotechar=quotechar)
        
        if has_header:
            headers = next(reader, None)
            if headers:
                rows_total += 1
        
        for row in reader:
            rows_total += 1
            if not row:  # Skip empty rows
                continue
                
            # Create key from all columns for duplicate detection
            key = sep.join(str(cell).strip() for cell in row)
            if key not in rows_by_key:
                rows_by_key[key] = []
            rows_by_key[key].append(row)
            
            if rows_total % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Find Dups CSV] Прочитано строк: {rows_total:,} за {elapsed:.1f}с…")
    
    dups_written = 0
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=sep, quotechar=quotechar)
        
        if has_header:
            # Write header to output
            with open(input_csv, 'r', encoding=encoding, errors='replace', newline='') as infile:
                header_reader = csv.reader(infile, delimiter=sep, quotechar=quotechar)
                headers = next(header_reader, None)
                if headers:
                    writer.writerow(headers)
        
        for key, rows in rows_by_key.items():
            if len(rows) > 1:  # Only write duplicates
                for row in rows:
                    writer.writerow(row)
                    dups_written += 1
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Find Dups CSV] Готово за {total_time:.1f}с. Дубликаты сохранены: {output_csv}")
    return rows_total, dups_written

def dedupe_keep_one(input_csv: Path, output_csv: Path, dups_csv: Optional[Path], encoding: str, sep: str, quotechar: str,
                    no_header: bool, dups_no_header: bool, log: Optional[ScrolledText] = None) -> Tuple[int, int, Optional[int]]:
    """Удаление дубликатов из CSV файла."""
    start_time = time.time()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    dup_keys = set()
    dups_lines_count: Optional[int] = None
    
    if dups_csv:
        dups_lines_count = 0
        with open(dups_csv, 'r', encoding=encoding, errors='replace', newline='') as f:
            reader = csv.reader(f, delimiter=sep, quotechar=quotechar)
            
            if not dups_no_header:
                next(reader, None)  # Skip header
            
            for row in reader:
                if not row:  # Skip empty rows
                    continue
                key = sep.join(str(cell).strip() for cell in row)
                dup_keys.add(key)
                dups_lines_count += 1
        if log: log_safe(log, f"Загружено строк дублей: {len(dup_keys):,}")
    
    seen_keys = set()
    kept_from_dups = set()
    total_in = 0
    total_out = 0
    
    with open(input_csv, 'r', encoding=encoding, errors='replace', newline='') as fin, \
         open(output_csv, 'w', encoding='utf-8', newline='') as fout:
        
        reader = csv.reader(fin, delimiter=sep, quotechar=quotechar)
        writer = csv.writer(fout, delimiter=sep, quotechar=quotechar)
        
        if not no_header:
            headers = next(reader, None)
            if headers:
                writer.writerow(headers)
                total_in += 1
        
        for row in reader:
            if not row:  # Skip empty rows
                continue
                
            total_in += 1
            key = sep.join(str(cell).strip() for cell in row)
            
            if dup_keys:
                if key in dup_keys:
                    if key in kept_from_dups:
                        continue
                    kept_from_dups.add(key)
                    writer.writerow(row)
                    total_out += 1
                else:
                    writer.writerow(row)
                    total_out += 1
            else:
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                writer.writerow(row)
                total_out += 1
            
            if total_in % 100000 == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Remove Duplicates CSV] Обработано строк: {total_in:,} за {elapsed:.1f}с")
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Remove Duplicates CSV] Готово за {total_time:.1f}с. Итог сохранён: {output_csv}")
    return total_in, total_out, dups_lines_count

# ====== Email Duplicates Scanner ==============================================

def find_email_duplicates_live(input_csv: Path, col_email: str, col_pass: str, encoding: str,
                               output_csv: Optional[Path], log: Optional[ScrolledText],
                               results_widget: Optional[ScrolledText]) -> Tuple[int, int]:
    """Live поиск повторных email с разными паролями."""
    start_time = time.time()
    if log: log_safe(log, f"→ Поиск повторных email с разными паролями (LIVE): {input_csv}")
    enc_read = "utf-8" if encoding == "auto" else encoding

    report_every = 50_000
    next_report = report_every

    passes_by_email: Dict[str, Set[str]] = {}
    rows_by_email: Dict[str, List[Dict[str, str]]] = {}
    emitted_email: Set[str] = set()
    batch_lines: List[str] = []
    batch_size = 100

    total = 0
    headers = None

    # Очистка результатов
    if results_widget:
        def clear_results():
            results_widget.configure(state='normal')
            results_widget.delete("1.0", "end")
            results_widget.configure(state='disabled')
        try:
            results_widget.after(0, clear_results)
        except:
            pass

    def append_result_lines(lines: List[str]):
        """Потокобезопасно добавить строки в поле результатов."""
        if not lines or not results_widget:
            return
        text = "".join(lines)
        def _do():
            try:
                results_widget.configure(state='normal')
                results_widget.insert("end", text)
                results_widget.see("end")
                results_widget.configure(state='disabled')
            except:
                pass
        try:
            results_widget.after(0, _do)
        except:
            pass

    with open(input_csv, "r", newline="", encoding=enc_read, errors="replace") as f_in:
        reader = csv.DictReader(f_in)
        headers = reader.fieldnames
        if not headers:
            if log: log_safe(log, "❌ Не удалось прочитать заголовки CSV.")
            return 0, 0
        if col_email not in headers or col_pass not in headers:
            if log: log_safe(log, f"❌ Нет колонок '{col_email}' и/или '{col_pass}' в CSV.")
            return 0, 0

        for row in reader:
            total += 1
            if total >= next_report:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"… Обработано {total:,} строк за {elapsed:.1f}с")
                next_report += report_every

            e = (row.get(col_email) or "").strip()
            p = (row.get(col_pass) or "").strip()
            if not e:
                continue

            rows_by_email.setdefault(e, []).append(row)

            if p:
                prev = passes_by_email.setdefault(e, set())
                before = len(prev)
                prev.add(p)
                after = len(prev)

                if after > 1 and e not in emitted_email:
                    emitted_email.add(e)
                    for r in rows_by_email[e]:
                        batch_lines.append(f"{r.get(col_email,'')},{r.get(col_pass,'')}\n")
                        if len(batch_lines) >= batch_size:
                            append_result_lines(batch_lines)
                            batch_lines.clear()
                elif e in emitted_email:
                    batch_lines.append(f"{row.get(col_email,'')},{row.get(col_pass,'')}\n")
                    if len(batch_lines) >= batch_size:
                        append_result_lines(batch_lines)
                        batch_lines.clear()

    if batch_lines:
        append_result_lines(batch_lines)
        batch_lines.clear()

    count_emails = sum(1 for s in passes_by_email.values() if len([x for x in s if x != ""]) > 1)
    total_time = time.time() - start_time
    if log: log_safe(log, f"✓ Готово за {total_time:.1f}с. Сканировано строк: {total:,}")
    if log: log_safe(log, f"   Проблемных email: {count_emails}")

    if output_csv and headers:
        try:
            safe_mkdirs(str(output_csv))
            with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
                writer = csv.DictWriter(f_out, fieldnames=headers)
                writer.writeheader()
                saved_rows = 0
                for e in emitted_email:
                    for r in rows_by_email.get(e, []):
                        writer.writerow(r)
                        saved_rows += 1
            if log: log_safe(log, f"✓ Сохранено {saved_rows} строк в: {output_csv}")
        except Exception as e:
            if log: log_safe(log, f"⚠️ Не удалось сохранить CSV: {e}")

    return total, count_emails

    # ====== File Separator function =============================================

def separate_file(input_path: Path, output_dir: Path, lines_per_file: int, output_format: str,
                  input_encoding: str, log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Разделяет большой файл на множество маленьких."""
    start_time = time.time()
    
    timestamp = time.strftime("%m%d_%H%M")
    result_dir = output_dir / f"Result_{timestamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    
    current_part = 1
    current_lines = 0
    total_lines = 0
    
    input_ext = input_path.suffix.lower()
    file_timestamp = time.strftime("%H%M")
    
    if input_ext == '.csv' and output_format == 'csv':
        with open(input_path, 'r', encoding=input_encoding, errors='replace', newline='') as infile:
            reader = csv.reader(infile)
            headers = next(reader, None)
            
            if headers:
                current_file_path = result_dir / f"result_{file_timestamp}_{current_part}.csv"
                current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                writer = csv.writer(current_file)
                writer.writerow(headers)
                
                for row in reader:
                    if current_lines >= lines_per_file:
                        current_file.close()
                        current_part += 1
                        current_lines = 0
                        current_file_path = result_dir / f"result_{file_timestamp}_{current_part}.csv"
                        current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                        writer = csv.writer(current_file)
                        writer.writerow(headers)
                    
                    writer.writerow(row)
                    current_lines += 1
                    total_lines += 1
                    
                    if total_lines % 100000 == 0:
                        elapsed = time.time() - start_time
                        if log: log_safe(log, f"[File Separator] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
                
                current_file.close()
    else:
        current_file_path = result_dir / f"result_{file_timestamp}_{current_part}.{output_format}"
        current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
        
        with open(input_path, 'r', encoding=input_encoding, errors='replace') as infile:
            for line in infile:
                if current_lines >= lines_per_file:
                    current_file.close()
                    current_part += 1
                    current_lines = 0
                    current_file_path = result_dir / f"result_{file_timestamp}_{current_part}.{output_format}"
                    current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                
                current_file.write(line)
                current_lines += 1
                total_lines += 1
                
                if total_lines % 100000 == 0:
                    elapsed = time.time() - start_time
                    if log: log_safe(log, f"[File Separator] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
        
        current_file.close()
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[File Separator] Готово за {total_time:.1f}с. Создано {current_part} файлов в: {result_dir}")
    return total_lines, current_part

# ====== Copy Text Files function ==========================================

def copy_text_files(file_paths: List[Path], output_path: Path, input_encoding: str,
                    log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Объединяет несколько текстовых файлов в один."""
    start_time = time.time()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    total_files = len(file_paths)
    total_lines = 0
    
    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        for i, file_path in enumerate(file_paths, 1):
            if log: log_safe(log, f"[Copy Files] Обработка файла {i}/{total_files}: {file_path.name}")
            
            try:
                with open(file_path, 'r', encoding=input_encoding, errors='replace') as infile:
                    file_lines = 0
                    for line in infile:
                        outfile.write(line)
                        file_lines += 1
                        total_lines += 1
                        
                        if total_lines % 100000 == 0:
                            elapsed = time.time() - start_time
                            if log: log_safe(log, f"[Copy Files] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
                    
                    if log: log_safe(log, f"[Copy Files] Файл {file_path.name}: {file_lines:,} строк")
            except Exception as e:
                if log: log_safe(log, f"[Copy Files] Ошибка при обработке {file_path}: {e}")
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Copy Files] Готово за {total_time:.1f}с. Объединено {total_files} файлов, {total_lines:,} строк в: {output_path}")
    return total_files, total_lines
# ====== GUI Application =======================================================

class UnifiedDataTools(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Unified Data Tools - Полный набор инструментов для работы с данными")
        self.geometry("1200x900")
        
        # Переменные для метрик - должны быть созданы первыми!
        self.init_metrics()
        
        # Создание основных вкладок
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        
        # Основные вкладки
        self.create_main_tabs()
        
        # Вспомогательные вкладки
        self.create_helper_tabs()
        
        # Общий лог внизу
        self.create_log_section()
        
        # Стили
        try:
            style = ttk.Style()
            style.theme_use("clam")
        except Exception:
            pass
    
    def init_metrics(self):
        """Инициализация переменных метрик."""
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

    def create_main_tabs(self):
        """Создание основных вкладок."""
        # 1. TXT → Table (приоритет от data_tools_gui.py)
        self.tab_txt2table = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_txt2table, text="TXT → Table")
        self.build_txt2table_tab()
        
        # 2. Find Duplicates (с preview, приоритет от data_tools_gui.py)
        self.tab_find_dups = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_find_dups, text="Find Duplicates")
        self.build_find_duplicates_tab()
        
        # 3. Remove Duplicates (приоритет от data_tools_gui.py)
        self.tab_remove_dups = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_remove_dups, text="Remove Duplicates")
        self.build_remove_duplicates_tab()
        
        # 4. Email Duplicates Scanner (приоритет от text_tools_gui.py)
        self.tab_email_dups = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_email_dups, text="Email Duplicates Scanner")
        self.build_email_duplicates_tab()

    def create_helper_tabs(self):
        """Создание вспомогательных вкладок."""
        # 5. Replace Delimiter
        self.tab_replace = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_replace, text="Replace Delimiter")
        self.build_replace_tab()
        
        # 6. Split Email/Pass
        self.tab_split = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_split, text="Split Email/Pass")
        self.build_split_tab()
        
        # 7. Join Files
        self.tab_join = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_join, text="Join Files")
        self.build_join_tab()
        
        # 8. CSV → TXT
        self.tab_csv2txt = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_csv2txt, text="CSV → TXT")
        self.build_csv2txt_tab()
        
        # 9. Delete by List
        self.tab_delete_list = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_delete_list, text="Delete by List")
        self.build_delete_by_list_tab()

        # 10. File Separator
        self.tab_separator = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_separator, text="File Separator")
        self.build_separator_tab()
        
        # 11. Copy Text Files
        self.tab_copy_files = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_copy_files, text="Copy Text Files")
        self.build_copy_files_tab()

    def create_log_section(self):
        """Создание секции логов внизу."""
        log_frame = ttk.LabelFrame(self, text="Журнал операций")
        log_frame.pack(fill='both', expand=False, padx=8, pady=(0, 8))
        
        self.log = ScrolledText(log_frame, height=12, state='disabled')
        self.log.pack(fill='both', expand=True, padx=4, pady=4)

    # ====== Основные вкладки ======

    def build_txt2table_tab(self):
        """Вкладка TXT → Table (приоритет от data_tools_gui.py)."""
        f = self.tab_txt2table
        pad = {'padx': 8, 'pady': 4}

        # Input path with File/Folder buttons
        ttk.Label(f, text="Input (file or folder):").grid(row=0, column=0, sticky='w', **pad)
        self.txt_input = ttk.Entry(f, width=70)
        self.txt_input.grid(row=0, column=1, **pad)
        
        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=0, column=2, **pad)
        ttk.Button(btns, text="File…", command=self.browse_txt_input_file).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(btns, text="Folder…", command=self.browse_txt_input_folder).grid(row=0, column=1)

        # Output path
        ttk.Label(f, text="Output (.csv or .xlsx):").grid(row=1, column=0, sticky='w', **pad)
        self.txt_output = ttk.Entry(f, width=70)
        self.txt_output.grid(row=1, column=1, **pad)
        ttk.Button(f, text="Save As…", command=self.browse_txt_output).grid(row=1, column=2, **pad)

        # Headers settings
        frm4 = ttk.Frame(f)
        frm4.grid(row=2, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm4, text="Column 1 header:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.txt_header1 = ttk.Entry(frm4, width=15)
        self.txt_header1.insert(0, "Before separator")
        self.txt_header1.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm4, text="Column 2 header:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.txt_header2 = ttk.Entry(frm4, width=15)
        self.txt_header2.insert(0, "After separator")
        self.txt_header2.grid(row=0, column=3)

        # Settings row 1
        frm1 = ttk.Frame(f)
        frm1.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm1, text="Delimiters:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.txt_delims = ttk.Entry(frm1, width=30)
        self.txt_delims.insert(0, "; : \\t |")
        self.txt_delims.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm1, text="Encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.txt_enc = ttk.Combobox(frm1, width=15, values=["utf-8-sig", "utf-8", "cp1251", "utf-16"], state="readonly")
        self.txt_enc.set("utf-8-sig")
        self.txt_enc.grid(row=0, column=3, padx=(0, 16))

        # Settings row 2 - checkboxes
        frm2 = ttk.Frame(f)
        frm2.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        
        self.chk_recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm2, text="Recursive", variable=self.chk_recursive).grid(row=0, column=0, padx=(0, 16))
        
        self.chk_with_source = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm2, text="Include source file", variable=self.chk_with_source).grid(row=0, column=1, padx=(0, 16))
        
        self.keep_empty = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm2, text="Keep empty lines", variable=self.keep_empty).grid(row=0, column=2, padx=(0, 16))

        # Format preferences
        frm3 = ttk.Frame(f)
        frm3.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm3, text="Prefer:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.prefer = tk.StringVar(value="auto")
        for i, opt in enumerate(["auto", "csv", "xlsx"]):
            ttk.Radiobutton(frm3, text=opt, value=opt, variable=self.prefer).grid(row=0, column=1+i, padx=(0, 6))
        
        self.split_excel = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm3, text="Split Excel parts", variable=self.split_excel).grid(row=0, column=4, padx=(12, 0))

        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_txt).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Run", command=self.run_txt2table).grid(row=0, column=1)

        # Metrics
        met = ttk.Frame(f)
        met.grid(row=7, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met, textvariable=self.txt_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met, textvariable=self.txt_lines_var).grid(row=0, column=1)

        for col in range(3):
            f.grid_columnconfigure(col, weight=1)

    def build_find_duplicates_tab(self):
        """Вкладка Find Duplicates с preview."""
        container = ttk.Frame(self.tab_find_dups)
        container.pack(fill='both', expand=True)

        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky='nsew')
        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky='nsew')
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        pad = {'padx': 8, 'pady': 4}

        # Input
        ttk.Label(left, text="Input CSV/TXT:").grid(row=0, column=0, sticky='w', **pad)
        self.dup_in = ttk.Entry(left, width=60)
        self.dup_in.grid(row=0, column=1, **pad)
        ttk.Button(left, text="Browse…", command=self.browse_dup_in).grid(row=0, column=2, **pad)

        # Output (optional)
        ttk.Label(left, text="Output Duplicates (optional):").grid(row=1, column=0, sticky='w', **pad)
        self.dup_out = ttk.Entry(left, width=60)
        self.dup_out.grid(row=1, column=1, **pad)
        ttk.Button(left, text="Save As…", command=self.browse_dup_out).grid(row=1, column=2, **pad)

        # Settings
        frm = ttk.Frame(left)
        frm.grid(row=2, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Separator:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.dup_sep = ttk.Entry(frm, width=10)
        self.dup_sep.insert(0, ",")
        self.dup_sep.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.dup_enc = ttk.Combobox(frm, width=15, values=["utf-8-sig", "utf-8", "cp1251", "utf-16"], state="readonly")
        self.dup_enc.set("utf-8-sig")
        self.dup_enc.grid(row=0, column=3, padx=(0, 16))
        
        self.dup_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Header present", variable=self.dup_header).grid(row=0, column=4, padx=(0, 16))
        
        ttk.Label(frm, text="Batch:").grid(row=0, column=5, sticky='w', padx=(0, 6))
        self.dup_batch = ttk.Entry(frm, width=8)
        self.dup_batch.insert(0, "20000")
        self.dup_batch.grid(row=0, column=6)

        # Preview settings
        frm_prev = ttk.Frame(left)
        frm_prev.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm_prev, text="Preview limit:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.prev_limit = ttk.Entry(frm_prev, width=8)
        self.prev_limit.insert(0, "5000")
        self.prev_limit.grid(row=0, column=1, padx=(0, 16))
        
        self.prev_unique = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_prev, text="Unique duplicate rows only", variable=self.prev_unique).grid(row=0, column=2)

        # Buttons
        btns = ttk.Frame(left)
        btns.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_dup).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Preview", command=self.preview_dups).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Run (save to file)", command=self.run_find_dups).grid(row=0, column=2)

        # Metrics
        met = ttk.Frame(left)
        met.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met, textvariable=self.dup_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met, textvariable=self.dup_lines_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(met, textvariable=self.dup_found_var).grid(row=0, column=2)

        for c in range(3):
            left.grid_columnconfigure(c, weight=1)

        # Preview area
        ttk.Label(right, text="Duplicates preview:").pack(anchor='w', padx=8, pady=(8, 0))
        self.dup_preview = ScrolledText(right, height=20, state='disabled')
        self.dup_preview.pack(fill='both', expand=True, padx=8, pady=8)

    def build_remove_duplicates_tab(self):
        """Вкладка Remove Duplicates."""
        f = self.tab_remove_dups
        pad = {'padx': 8, 'pady': 4}

        # Input
        ttk.Label(f, text="Input CSV/TXT:").grid(row=0, column=0, sticky='w', **pad)
        self.dd_in = ttk.Entry(f, width=70)
        self.dd_in.grid(row=0, column=1, **pad)
        ttk.Button(f, text="Browse…", command=self.browse_dd_in).grid(row=0, column=2, **pad)

        # Output
        ttk.Label(f, text="Output (deduped):").grid(row=1, column=0, sticky='w', **pad)
        self.dd_out = ttk.Entry(f, width=70)
        self.dd_out.grid(row=1, column=1, **pad)
        ttk.Button(f, text="Save As…", command=self.browse_dd_out).grid(row=1, column=2, **pad)

        # Duplicates file (optional)
        ttk.Label(f, text="Duplicates file (optional):").grid(row=2, column=0, sticky='w', **pad)
        self.dd_dups = ttk.Entry(f, width=70)
        self.dd_dups.grid(row=2, column=1, **pad)
        ttk.Button(f, text="Browse…", command=self.browse_dd_dups).grid(row=2, column=2, **pad)

        # Settings
        frm = ttk.Frame(f)
        frm.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Separator:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.dd_sep = ttk.Entry(frm, width=10)
        self.dd_sep.insert(0, ",")
        self.dd_sep.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.dd_enc = ttk.Combobox(frm, width=15, values=["utf-8-sig", "utf-8", "cp1251", "utf-16"], state="readonly")
        self.dd_enc.set("utf-8-sig")
        self.dd_enc.grid(row=0, column=3, padx=(0, 16))
        
        self.dd_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Header present (input)", variable=self.dd_header).grid(row=0, column=4, padx=(0, 16))
        
        self.dd_dups_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Header present (dups)", variable=self.dd_dups_header).grid(row=0, column=5)

        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_dedup).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Run", command=self.run_dedup).grid(row=0, column=1)

        # Metrics
        met1 = ttk.Frame(f)
        met1.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met1, textvariable=self.dd_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met1, textvariable=self.dd_lines_var).grid(row=0, column=1)

        met2 = ttk.Frame(f)
        met2.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met2, textvariable=self.dd_before_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met2, textvariable=self.dd_after_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(met2, textvariable=self.dd_dups_lines_var).grid(row=0, column=2, padx=(0, 20))
        ttk.Label(met2, textvariable=self.dd_removed_var).grid(row=0, column=3)

        for col in range(3):
            f.grid_columnconfigure(col, weight=1)

    def build_email_duplicates_tab(self):
        """Вкладка Email Duplicates Scanner с live выводом."""
        f = self.tab_email_dups
        pad = {'padx': 6, 'pady': 4}

        # Input
        ttk.Label(f, text="Source CSV:").grid(row=0, column=0, sticky="e", **pad)
        self.ed_in = ttk.Entry(f, width=60)
        self.ed_in.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_ed_in).grid(row=0, column=2)

        # Column settings
        ttk.Label(f, text="Email column:").grid(row=1, column=0, sticky="e", **pad)
        self.ed_col_email = ttk.Entry(f, width=20)
        self.ed_col_email.grid(row=1, column=1, sticky="w", **pad)
        self.ed_col_email.insert(0, "email")

        ttk.Label(f, text="Password column:").grid(row=2, column=0, sticky="e", **pad)
        self.ed_col_pass = ttk.Entry(f, width=20)
        self.ed_col_pass.grid(row=2, column=1, sticky="w", **pad)
        self.ed_col_pass.insert(0, "pass")

        # Encoding
        ttk.Label(f, text="Encoding:").grid(row=3, column=0, sticky="e", **pad)
        self.ed_enc_in = ttk.Combobox(f, width=15, values=["utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], state="readonly")
        self.ed_enc_in.set("utf-8")
        self.ed_enc_in.grid(row=3, column=1, sticky="w")

        # Output (optional)
        ttk.Label(f, text="Save found to file (optional):").grid(row=4, column=0, sticky="e", **pad)
        self.ed_out = ttk.Entry(f, width=60)
        self.ed_out.grid(row=4, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_ed_out).grid(row=4, column=2)

        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_email_dups).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Find Email Duplicates (Live)", command=self.run_email_dupes).grid(row=0, column=1)

        # Metrics
        met = ttk.Frame(f)
        met.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met, textvariable=self.ed_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met, textvariable=self.ed_lines_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(met, textvariable=self.ed_found_var).grid(row=0, column=2)

        # Results area
        ttk.Label(f, text="Found duplicate emails:").grid(row=7, column=0, sticky="ne", **pad)
        self.ed_results = ScrolledText(f, height=12, state='disabled')
        self.ed_results.grid(row=7, column=1, sticky="nsew", padx=6, pady=6)

        f.columnconfigure(1, weight=1)
        f.rowconfigure(7, weight=1)

    # ====== Вспомогательные вкладки ======

    def build_replace_tab(self):
        """Вкладка замены разделителя."""
        f = self.tab_replace
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Input file (.txt):").grid(row=0, column=0, sticky="e", **pad)
        self.rep_in = ttk.Entry(f, width=60)
        self.rep_in.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_rep_in).grid(row=0, column=2)

        ttk.Label(f, text="Output file (.txt):").grid(row=1, column=0, sticky="e", **pad)
        self.rep_out = ttk.Entry(f, width=60)
        self.rep_out.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_rep_out).grid(row=1, column=2)

        ttk.Label(f, text="Replace:").grid(row=2, column=0, sticky="e", **pad)
        self.rep_old = ttk.Entry(f, width=10)
        self.rep_old.grid(row=2, column=1, sticky="w", **pad)
        self.rep_old.insert(0, ";")

        ttk.Label(f, text="with:").grid(row=2, column=1, sticky="e")
        self.rep_new = ttk.Entry(f, width=10)
        self.rep_new.grid(row=2, column=1, padx=(140, 0), pady=4, sticky="")
        self.rep_new.insert(0, ":")

        # Encoding
        frm = ttk.Frame(f)
        frm.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.rep_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.rep_enc_in.set("auto")
        self.rep_enc_in.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.rep_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.rep_enc_out.set("utf-8")
        self.rep_enc_out.grid(row=0, column=3)

        ttk.Button(f, text="Run Replace", command=self.run_replace).grid(row=4, column=1, sticky="w", pady=6)
        f.columnconfigure(1, weight=1)

    def build_split_tab(self):
        """Вкладка разделения email:pass."""
        f = self.tab_split
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Source (.txt):").grid(row=0, column=0, sticky="e", **pad)
        self.sp_in = ttk.Entry(f, width=60)
        self.sp_in.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_sp_in).grid(row=0, column=2)

        ttk.Label(f, text="Delimiter:").grid(row=1, column=0, sticky="e", **pad)
        self.sp_delim = ttk.Entry(f, width=10)
        self.sp_delim.grid(row=1, column=1, sticky="w", **pad)
        self.sp_delim.insert(0, ":")

        ttk.Label(f, text="Email → file (.txt):").grid(row=2, column=0, sticky="e", **pad)
        self.sp_out_email = ttk.Entry(f, width=60)
        self.sp_out_email.grid(row=2, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_sp_out_email).grid(row=2, column=2)

        ttk.Label(f, text="Pass → file (.txt):").grid(row=3, column=0, sticky="e", **pad)
        self.sp_out_pass = ttk.Entry(f, width=60)
        self.sp_out_pass.grid(row=3, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_sp_out_pass).grid(row=3, column=2)

        # Encoding
        frm = ttk.Frame(f)
        frm.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.sp_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.sp_enc_in.set("auto")
        self.sp_enc_in.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.sp_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.sp_enc_out.set("utf-8")
        self.sp_enc_out.grid(row=0, column=3)

        ttk.Button(f, text="Split", command=self.run_split).grid(row=5, column=1, sticky="w", pady=6)
        f.columnconfigure(1, weight=1)

    def build_join_tab(self):
        """Вкладка объединения файлов."""
        f = self.tab_join
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Email file (.txt):").grid(row=0, column=0, sticky="e", **pad)
        self.jn_email = ttk.Entry(f, width=60)
        self.jn_email.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_jn_email).grid(row=0, column=2)

        ttk.Label(f, text="Password file (.txt):").grid(row=1, column=0, sticky="e", **pad)
        self.jn_pass = ttk.Entry(f, width=60)
        self.jn_pass.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_jn_pass).grid(row=1, column=2)

        ttk.Label(f, text="Output (.txt):").grid(row=2, column=0, sticky="e", **pad)
        self.jn_out = ttk.Entry(f, width=60)
        self.jn_out.grid(row=2, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_jn_out).grid(row=2, column=2)

        ttk.Label(f, text="Delimiter:").grid(row=3, column=0, sticky="e", **pad)
        self.jn_delim = ttk.Entry(f, width=10)
        self.jn_delim.grid(row=3, column=1, sticky="w", **pad)
        self.jn_delim.insert(0, ":")

        # Encoding
        frm = ttk.Frame(f)
        frm.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.jn_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.jn_enc_in.set("auto")
        self.jn_enc_in.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.jn_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.jn_enc_out.set("utf-8")
        self.jn_enc_out.grid(row=0, column=3)

        ttk.Button(f, text="Join", command=self.run_join).grid(row=5, column=1, sticky="w", pady=6)
        f.columnconfigure(1, weight=1)

    def build_csv2txt_tab(self):
        """Вкладка CSV → TXT."""
        f = self.tab_csv2txt
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Source (.csv):").grid(row=0, column=0, sticky="e", **pad)
        self.ct_in = ttk.Entry(f, width=60)
        self.ct_in.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_ct_in).grid(row=0, column=2)

        ttk.Label(f, text="Email column name:").grid(row=1, column=0, sticky="e", **pad)
        self.ct_col_email = ttk.Entry(f, width=20)
        self.ct_col_email.grid(row=1, column=1, sticky="w", **pad)
        self.ct_col_email.insert(0, "email")

        ttk.Label(f, text="Password column name:").grid(row=2, column=0, sticky="e", **pad)
        self.ct_col_pass = ttk.Entry(f, width=20)
        self.ct_col_pass.grid(row=2, column=1, sticky="w", **pad)
        self.ct_col_pass.insert(0, "pass")

        ttk.Label(f, text="Delimiter in .txt:").grid(row=3, column=0, sticky="e", **pad)
        self.ct_delim = ttk.Entry(f, width=10)
        self.ct_delim.grid(row=3, column=1, sticky="w", **pad)
        self.ct_delim.insert(0, ":")

        ttk.Label(f, text="Output .txt:").grid(row=4, column=0, sticky="e", **pad)
        self.ct_out = ttk.Entry(f, width=60)
        self.ct_out.grid(row=4, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_ct_out).grid(row=4, column=2)

        # Encoding
        frm = ttk.Frame(f)
        frm.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.ct_enc_in = ttk.Combobox(frm, values=["utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.ct_enc_in.set("utf-8")
        self.ct_enc_in.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.ct_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.ct_enc_out.set("utf-8")
        self.ct_enc_out.grid(row=0, column=3)

        ttk.Button(f, text="Convert CSV → TXT", command=self.run_csv2txt).grid(row=6, column=1, sticky="w", pady=6)
        f.columnconfigure(1, weight=1)

    def build_delete_by_list_tab(self):
        """Вкладка удаления строк по списку."""
        f = self.tab_delete_list
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Source (CSV/TXT):").grid(row=0, column=0, sticky="e", **pad)
        self.del_src = ttk.Entry(f, width=60)
        self.del_src.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_del_src).grid(row=0, column=2)

        ttk.Label(f, text="Delete list (.txt):").grid(row=1, column=0, sticky="e", **pad)
        self.del_list = ttk.Entry(f, width=60)
        self.del_list.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_del_list).grid(row=1, column=2)

        ttk.Label(f, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
        self.del_out = ttk.Entry(f, width=60)
        self.del_out.grid(row=2, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_del_out).grid(row=2, column=2)

        ttk.Label(f, text="(CSV) Column for matching (optional):").grid(row=3, column=0, sticky="e", **pad)
        self.del_csv_col = ttk.Entry(f, width=20)
        self.del_csv_col.grid(row=3, column=1, sticky="w", **pad)
        self.del_csv_col.insert(0, "")

        self.del_case_ins = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Ignore case and spaces", variable=self.del_case_ins).grid(row=4, column=1, sticky="w")

        # Encoding
        frm = ttk.Frame(f)
        frm.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.del_enc_in = ttk.Combobox(frm, values=["auto", "utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.del_enc_in.set("auto")
        self.del_enc_in.grid(row=0, column=1, padx=(0, 16))
        
        ttk.Label(frm, text="Output encoding:").grid(row=0, column=2, sticky='w', padx=(0, 6))
        self.del_enc_out = ttk.Combobox(frm, values=["utf-8", "cp1251", "iso-8859-1"], width=10, state="readonly")
        self.del_enc_out.set("utf-8")
        self.del_enc_out.grid(row=0, column=3)

        ttk.Button(f, text="Delete Rows", command=self.run_delete_by_list).grid(row=6, column=1, sticky="w", pady=6)
        f.columnconfigure(1, weight=1)

    def build_separator_tab(self):
        """Вкладка File Separator - разделение больших файлов."""
        f = self.tab_separator
        pad = {"padx": 6, "pady": 4}
        
        ttk.Label(f, text="Input file (.txt/.csv):").grid(row=0, column=0, sticky="e", **pad)
        self.sep_in = ttk.Entry(f, width=60)
        self.sep_in.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_sep_in).grid(row=0, column=2)

        ttk.Label(f, text="Output directory:").grid(row=1, column=0, sticky="e", **pad)
        self.sep_out_dir = ttk.Entry(f, width=60)
        self.sep_out_dir.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(f, text="Browse…", command=self.browse_sep_out_dir).grid(row=1, column=2)

        ttk.Label(f, text="Lines per file:").grid(row=2, column=0, sticky="e", **pad)
        self.sep_lines = ttk.Entry(f, width=15)
        self.sep_lines.grid(row=2, column=1, sticky="w", **pad)
        self.sep_lines.insert(0, "1000000")

        # Format selection
        frm_format = ttk.Frame(f)
        frm_format.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm_format, text="Output format:").grid(row=0, column=0, sticky='w', padx=(0, 16))
        self.sep_format = tk.StringVar(value="txt")
        ttk.Radiobutton(frm_format, text="TXT", value="txt", variable=self.sep_format).grid(row=0, column=1, padx=(0, 16))
        ttk.Radiobutton(frm_format, text="CSV", value="csv", variable=self.sep_format).grid(row=0, column=2)

        # Encoding
        frm_enc = ttk.Frame(f)
        frm_enc.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm_enc, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.sep_enc_in = ttk.Combobox(frm_enc, values=["utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=15, state="readonly")
        self.sep_enc_in.set("utf-8")
        self.sep_enc_in.grid(row=0, column=1)

        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_separator).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Run Separation", command=self.run_separator).grid(row=0, column=1)

        # Metrics
        met = ttk.Frame(f)
        met.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met, textvariable=self.sep_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met, textvariable=self.sep_lines_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(met, textvariable=self.sep_parts_var).grid(row=0, column=2)

        f.columnconfigure(1, weight=1)

    def build_copy_files_tab(self):
        """Вкладка Copy Text Files - объединение файлов."""
        f = self.tab_copy_files
        pad = {"padx": 6, "pady": 4}
        
        # Input selection method
        frm_method = ttk.Frame(f)
        frm_method.grid(row=0, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm_method, text="Input method:").grid(row=0, column=0, sticky='w', padx=(0, 16))
        self.copy_method = tk.StringVar(value="files")
        ttk.Radiobutton(frm_method, text="Select files", value="files", variable=self.copy_method, command=self.on_copy_method_change).grid(row=0, column=1, padx=(0, 16))
        ttk.Radiobutton(frm_method, text="Select folder", value="folder", variable=self.copy_method, command=self.on_copy_method_change).grid(row=0, column=2)

        # Input files/folder
        ttk.Label(f, text="Input files/folder:").grid(row=1, column=0, sticky="e", **pad)
        self.copy_in = ttk.Entry(f, width=60)
        self.copy_in.grid(row=1, column=1, sticky="we", **pad)
        
        # Buttons for input (will change based on method)
        self.copy_in_frame = ttk.Frame(f)
        self.copy_in_frame.grid(row=1, column=2, **pad)
        self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Files…", command=self.browse_copy_files)
        self.copy_browse_btn.grid(row=0, column=0)

        # Output file
        ttk.Label(f, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
        self.copy_out = ttk.Entry(f, width=60)
        self.copy_out.grid(row=2, column=1, sticky="we", **pad)
        ttk.Button(f, text="Save As…", command=self.browse_copy_out).grid(row=2, column=2)

        # Settings
        frm_settings = ttk.Frame(f)
        frm_settings.grid(row=3, column=0, columnspan=3, sticky='w', **pad)
        self.copy_recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_settings, text="Recursive (for folder)", variable=self.copy_recursive).grid(row=0, column=0, padx=(0, 16))
        
        ttk.Label(frm_settings, text="File pattern:").grid(row=0, column=1, sticky='w', padx=(0, 6))
        self.copy_pattern = ttk.Entry(frm_settings, width=15)
        self.copy_pattern.insert(0, "*.txt")
        self.copy_pattern.grid(row=0, column=2)

        # Encoding
        frm_enc = ttk.Frame(f)
        frm_enc.grid(row=4, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(frm_enc, text="Input encoding:").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.copy_enc_in = ttk.Combobox(frm_enc, values=["auto", "utf-8", "utf-8-sig", "cp1251", "iso-8859-1"], width=15, state="readonly")
        self.copy_enc_in.set("auto")
        self.copy_enc_in.grid(row=0, column=1)

        # Buttons
        btns = ttk.Frame(f)
        btns.grid(row=5, column=0, columnspan=3, sticky='w', **pad)
        ttk.Button(btns, text="Scan", command=self.scan_copy_files).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Start Copy Files", command=self.run_copy_files).grid(row=0, column=1)

        # Metrics
        met = ttk.Frame(f)
        met.grid(row=6, column=0, columnspan=3, sticky='w', **pad)
        ttk.Label(met, textvariable=self.copy_files_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(met, textvariable=self.copy_lines_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(met, textvariable=self.copy_total_var).grid(row=0, column=2)

        f.columnconfigure(1, weight=1)

    # ====== Utility Methods ======

    def _set_var(self, var: tk.StringVar, value: str):
        """Потокобезопасно обновляет переменную."""
        try:
            self.after(0, var.set, value)
        except:
            pass

    def _run_in_thread(self, func, *args, **kwargs):
        """Запускает функцию в отдельном потоке."""
        t = threading.Thread(target=self._safe_run, args=(func, *args), kwargs=kwargs, daemon=True)
        t.start()

    def _safe_run(self, func, *args, **kwargs):
        """Безопасно выполняет функцию с обработкой ошибок."""
        try:
            func(*args, **kwargs)
        except Exception as e:
            log_safe(self.log, f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))

    def open_text_lines(self, file_path: str, encoding_choice: str = "auto"):
        """Итератор по строкам текстового файла с учетом выбранной/автоматической кодировки."""
        enc = detect_encoding(file_path) if encoding_choice == "auto" else encoding_choice
        return open(file_path, "r", encoding=enc, errors="replace")

    def write_text_lines(self, file_path: str, lines, encoding_choice: str = "utf-8"):
        """Запись строк в текстовый файл."""
        enc = "utf-8" if encoding_choice == "auto" else encoding_choice
        with open(file_path, "w", encoding=enc, newline="") as f:
            for line in lines:
                if not line.endswith("\n"):
                    line = line + "\n"
                f.write(line)

    # ====== File Browser Methods ======

    def browse_txt_input_file(self):
        path = filedialog.askopenfilename(title="Выбрать TXT файл", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path: self.txt_input.delete(0, 'end'); self.txt_input.insert(0, path)

    def browse_txt_input_folder(self):
        path = filedialog.askdirectory(title="Выбрать папку с TXT")
        if path: self.txt_input.delete(0, 'end'); self.txt_input.insert(0, path)

    def browse_txt_output(self):
        path = filedialog.asksaveasfilename(title="Сохранить как", defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if path: self.txt_output.delete(0, 'end'); self.txt_output.insert(0, path)

    def browse_dup_in(self):
        path = filedialog.askopenfilename(title="CSV с данными", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.dup_in.delete(0, 'end'); self.dup_in.insert(0, path)

    def browse_dup_out(self):
        path = filedialog.asksaveasfilename(title="CSV для дублей (опционально)", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path: self.dup_out.delete(0, 'end'); self.dup_out.insert(0, path)

    def browse_dd_in(self):
        path = filedialog.askopenfilename(title="Входной CSV", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.dd_in.delete(0, 'end'); self.dd_in.insert(0, path)

    def browse_dd_out(self):
        path = filedialog.asksaveasfilename(title="Файл без дублей", defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("TXT", "*.txt"), ("All", "*.*")])
        if path: self.dd_out.delete(0, 'end'); self.dd_out.insert(0, path)

    def browse_dd_dups(self):
        path = filedialog.askopenfilename(title="CSV с дублями (опционально)", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.dd_dups.delete(0, 'end'); self.dd_dups.insert(0, path)

    def browse_ed_in(self):
        path = filedialog.askopenfilename(title="Выберите CSV файл", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.ed_in.delete(0, 'end'); self.ed_in.insert(0, path)

    def browse_ed_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить найденные дубли", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path: self.ed_out.delete(0, 'end'); self.ed_out.insert(0, path)

    # Helper tabs browsers
    def browse_rep_in(self):
        path = filedialog.askopenfilename(title="Выбрать TXT файл", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path: self.rep_in.delete(0, 'end'); self.rep_in.insert(0, path)

    def browse_rep_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить как", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: self.rep_out.delete(0, 'end'); self.rep_out.insert(0, path)

    def browse_sp_in(self):
        path = filedialog.askopenfilename(title="Выбрать файл для разделения", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path: self.sp_in.delete(0, 'end'); self.sp_in.insert(0, path)

    def browse_sp_out_email(self):
        path = filedialog.asksaveasfilename(title="Сохранить email файл", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: self.sp_out_email.delete(0, 'end'); self.sp_out_email.insert(0, path)

    def browse_sp_out_pass(self):
        path = filedialog.asksaveasfilename(title="Сохранить password файл", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: self.sp_out_pass.delete(0, 'end'); self.sp_out_pass.insert(0, path)

    def browse_jn_email(self):
        path = filedialog.askopenfilename(title="Выбрать файл с email", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path: self.jn_email.delete(0, 'end'); self.jn_email.insert(0, path)

    def browse_jn_pass(self):
        path = filedialog.askopenfilename(title="Выбрать файл с паролями", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path: self.jn_pass.delete(0, 'end'); self.jn_pass.insert(0, path)

    def browse_jn_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить объединенный файл", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: self.jn_out.delete(0, 'end'); self.jn_out.insert(0, path)

    def browse_ct_in(self):
        path = filedialog.askopenfilename(title="Выбрать CSV файл", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path: self.ct_in.delete(0, 'end'); self.ct_in.insert(0, path)

    def browse_ct_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить TXT файл", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: self.ct_out.delete(0, 'end'); self.ct_out.insert(0, path)

    def browse_del_src(self):
        path = filedialog.askopenfilename(title="Выбрать исходный файл", filetypes=[("All", "*.*")])
        if path: self.del_src.delete(0, 'end'); self.del_src.insert(0, path)

    def browse_del_list(self):
        path = filedialog.askopenfilename(title="Выбрать список для удаления", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path: self.del_list.delete(0, 'end'); self.del_list.insert(0, path)

    def browse_del_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить результат", defaultextension=".txt")
        if path: self.del_out.delete(0, 'end'); self.del_out.insert(0, path)

    # New browsers for separator and copy files
    def browse_sep_in(self):
        path = filedialog.askopenfilename(title="Выбрать файл для разделения", filetypes=[("Text/CSV", "*.txt;*.csv"), ("All", "*.*")])
        if path: self.sep_in.delete(0, 'end'); self.sep_in.insert(0, path)

    def browse_sep_out_dir(self):
        path = filedialog.askdirectory(title="Выбрать папку для результатов")
        if path: self.sep_out_dir.delete(0, 'end'); self.sep_out_dir.insert(0, path)

    def browse_copy_files(self):
        paths = filedialog.askopenfilenames(title="Выбрать файлы для объединения", filetypes=[("Text/CSV", "*.txt;*.csv"), ("All", "*.*")])
        if paths: 
            self.copy_in.delete(0, 'end')
            self.copy_in.insert(0, "; ".join(paths))

    def browse_copy_folder(self):
        path = filedialog.askdirectory(title="Выбрать папку с файлами")
        if path: self.copy_in.delete(0, 'end'); self.copy_in.insert(0, path)

    def browse_copy_out(self):
        path = filedialog.asksaveasfilename(title="Сохранить объединенный файл", defaultextension=".txt", filetypes=[("Text", "*.txt"), ("CSV", "*.csv")])
        if path: self.copy_out.delete(0, 'end'); self.copy_out.insert(0, path)

    def on_copy_method_change(self):
        """Обновляет кнопки в зависимости от выбранного метода."""
        method = self.copy_method.get()
        for widget in self.copy_in_frame.winfo_children():
            widget.destroy()
        
        if method == "files":
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Files…", command=self.browse_copy_files)
        else:
            self.copy_browse_btn = ttk.Button(self.copy_in_frame, text="Browse Folder…", command=self.browse_copy_folder)
        
        self.copy_browse_btn.grid(row=0, column=0)

    # ====== Scan Methods ======

    def scan_txt(self):
        """Сканирование TXT файлов."""
        input_path = Path(self.txt_input.get().strip())
        if not input_path.exists():
            messagebox.showerror("Ошибка", "Указан неверный входной путь.")
            return
        recursive = bool(self.chk_recursive.get())
        encoding = self.txt_enc.get()

        def job():
            try:
                self._set_var(self.txt_files_var, "Files: …")
                self._set_var(self.txt_lines_var, "Lines: …")
                files, lines = scan_txt_stats(input_path, recursive, encoding)
                self._set_var(self.txt_files_var, f"Files: {files:,}")
                self._set_var(self.txt_lines_var, f"Lines: {lines:,}")
                log_safe(self.log, f"[TXT Scan] Найдено {files} файл(ов), {lines:,} строк")
            except Exception as e:
                log_safe(self.log, f"[TXT Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        self._run_in_thread(job)

    def scan_dup(self):
        """Сканирование CSV для поиска дублей."""
        inp = Path(self.dup_in.get().strip())
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        enc = self.dup_enc.get()
        sep = self.dup_sep.get().strip() or ","
        header = bool(self.dup_header.get())

        def job():
            try:
                self._set_var(self.dup_files_var, "Files: 1")
                self._set_var(self.dup_lines_var, "Lines: …")
                lines = scan_csv_lines(inp, enc, sep, header)
                self._set_var(self.dup_lines_var, f"Lines: {lines:,}")
                log_safe(self.log, f"[Dup Scan] CSV содержит {lines:,} строк данных")
            except Exception as e:
                log_safe(self.log, f"[Dup Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        self._run_in_thread(job)

    def scan_dedup(self):
        """Сканирование для Remove Duplicates."""
        inp = Path(self.dd_in.get().strip())
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        enc = self.dd_enc.get()
        sep = self.dd_sep.get().strip() or ","
        header = bool(self.dd_header.get())
        dups = Path(self.dd_dups.get().strip()) if self.dd_dups.get().strip() else None
        dups_header = bool(self.dd_dups_header.get())

        def job():
            try:
                files = 1 + (1 if dups else 0)
                self._set_var(self.dd_files_var, f"Files: {files}")
                self._set_var(self.dd_lines_var, "Lines: …")
                self._set_var(self.dd_before_var, "Lines Before: …")
                self._set_var(self.dd_dups_lines_var, "Duplicates Lines: —" if not dups else "Duplicates Lines: …")

                lines_in = scan_csv_lines(inp, enc, sep, header)
                self._set_var(self.dd_lines_var, f"Lines: {lines_in:,}")
                self._set_var(self.dd_before_var, f"Lines Before: {lines_in:,}")
                log_safe(self.log, f"[Dedup Scan] Входной файл содержит {lines_in:,} строк")

                if dups:
                    lines_dups = scan_csv_lines(dups, enc, sep, dups_header)
                    self._set_var(self.dd_dups_lines_var, f"Duplicates Lines: {lines_dups:,}")
                    log_safe(self.log, f"[Dedup Scan] Файл дублей содержит {lines_dups:,} строк")
                else:
                    self._set_var(self.dd_dups_lines_var, "Duplicates Lines: —")
            except Exception as e:
                log_safe(self.log, f"[Dedup Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        self._run_in_thread(job)

    def scan_email_dups(self):
        """Сканирование для Email Duplicates."""
        inp = Path(self.ed_in.get().strip())
        if not inp.exists():
            messagebox.showerror("Ошибка", "CSV файл не найден.")
            return
        enc = self.ed_enc_in.get()

        def job():
            try:
                self._set_var(self.ed_files_var, "Files: 1")
                self._set_var(self.ed_lines_var, "Lines: …")
                lines = scan_csv_lines(inp, enc, ",", True)  # Предполагаем заголовок
                self._set_var(self.ed_lines_var, f"Lines: {lines:,}")
                log_safe(self.log, f"[Email Dup Scan] CSV содержит {lines:,} строк данных")
            except Exception as e:
                log_safe(self.log, f"[Email Dup Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        self._run_in_thread(job)

    def scan_separator(self):
        """Сканирование для File Separator."""
        inp = Path(self.sep_in.get().strip())
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        
        enc = self.sep_enc_in.get()
        try:
            lines_per_file = int(self.sep_lines.get())
        except:
            lines_per_file = 1000000

        def job():
            try:
                self._set_var(self.sep_files_var, "Files: 1")
                self._set_var(self.sep_lines_var, "Lines: …")
                
                # Подсчет строк
                total_lines = 0
                with open(inp, 'r', encoding=enc, errors='replace') as f:
                    for _ in f:
                        total_lines += 1
                        if total_lines % 100000 == 0:
                            self._set_var(self.sep_lines_var, f"Lines: {total_lines:,}…")
                
                estimated_parts = (total_lines + lines_per_file - 1) // lines_per_file
                self._set_var(self.sep_lines_var, f"Lines: {total_lines:,}")
                self._set_var(self.sep_parts_var, f"Estimated parts: {estimated_parts:,}")
                log_safe(self.log, f"[File Separator Scan] Файл содержит {total_lines:,} строк, будет создано ~{estimated_parts:,} частей")
            except Exception as e:
                log_safe(self.log, f"[File Separator Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        
        self._run_in_thread(job)

    def scan_copy_files(self):
        """Сканирование для Copy Files."""
        method = self.copy_method.get()
        input_str = self.copy_in.get().strip()
        if not input_str:
            messagebox.showerror("Ошибка", "Укажи входные файлы или папку.")
            return
        
        enc = self.copy_enc_in.get()
        
        def job():
            try:
                self._set_var(self.copy_files_var, "Files: …")
                self._set_var(self.copy_lines_var, "Lines: …")
                
                file_paths = []
                if method == "files":
                    # Разделяем пути файлов
                    paths = [p.strip() for p in input_str.split(";")]
                    file_paths = [Path(p) for p in paths if p and Path(p).exists()]
                else:
                    # Папка
                    folder_path = Path(input_str)
                    if folder_path.exists() and folder_path.is_dir():
                        pattern = self.copy_pattern.get().strip() or "*.txt"
                        recursive = bool(self.copy_recursive.get())
                        if recursive:
                            file_paths = list(folder_path.rglob(pattern))
                        else:
                            file_paths = list(folder_path.glob(pattern))
                
                if not file_paths:
                    self._set_var(self.copy_files_var, "Files: 0")
                    self._set_var(self.copy_lines_var, "Lines: 0")
                    log_safe(self.log, "[Copy Files Scan] Файлы не найдены")
                    return
                
                # Подсчет строк
                total_lines = 0
                encoding = detect_encoding(str(file_paths[0])) if enc == "auto" else enc
                
                for i, file_path in enumerate(file_paths):
                    try:
                        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                            file_lines = sum(1 for _ in f)
                            total_lines += file_lines
                        
                        if (i + 1) % 10 == 0:
                            self._set_var(self.copy_files_var, f"Files: {i + 1:,}/{len(file_paths):,}")
                            self._set_var(self.copy_lines_var, f"Lines: {total_lines:,}…")
                    except Exception as e:
                        log_safe(self.log, f"[Copy Files Scan] Ошибка при чтении {file_path}: {e}")
                
                self._set_var(self.copy_files_var, f"Files: {len(file_paths):,}")
                self._set_var(self.copy_lines_var, f"Lines: {total_lines:,}")
                log_safe(self.log, f"[Copy Files Scan] Найдено {len(file_paths):,} файлов, {total_lines:,} строк")
            except Exception as e:
                log_safe(self.log, f"[Copy Files Scan] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))
        
        self._run_in_thread(job)

    # ====== Run Methods - Main Tabs ======

    def run_txt2table(self):
        """Запуск TXT → Table."""
        input_path = Path(self.txt_input.get().strip())
        output_path = Path(self.txt_output.get().strip())
        if not input_path.exists():
            messagebox.showerror("Ошибка", "Указан неверный входной путь.")
            return
        if not output_path:
            messagebox.showerror("Ошибка", "Укажи выходной файл (.csv или .xlsx).")
            return

        delims = parse_delims(self.txt_delims.get())
        encoding = self.txt_enc.get()
        recursive = bool(self.chk_recursive.get())
        include_source = bool(self.chk_with_source.get())
        keep_empty = bool(self.keep_empty.get())
        prefer = self.prefer.get()
        split_excel = bool(self.split_excel.get())
        # Custom Headers
        header1 = self.txt_header1.get().strip() or "Before delimiter"
        header2 = self.txt_header2.get().strip() or "After delimiter"

        def job():
            try:
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
                    self._set_var(self.txt_lines_var, f"Lines: {count:,}")
                    total_time = time.time() - start_time
                    log_safe(self.log, f"[TXT→Table] Готово за {total_time:.1f}с. Строк: {count:,}. Файл: {csv_path}")
                else:
                    try:
                        xlsx_path = output_path if ext == ".xlsx" else output_path.with_suffix(".xlsx")
                        count = write_excel_single_or_split(rows_iter, xlsx_path, split=split_excel, include_source=include_source, header1=header1, header2=header2)
                        self._set_var(self.txt_lines_var, f"Lines: {count:,}")
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
                        self._set_var(self.txt_lines_var, f"Lines: {count:,}")
                        total_time = time.time() - start_time
                        log_safe(self.log, f"[TXT→Table] Готово за {total_time:.1f}с. Строк: {count:,}. Файл: {csv_path}")
            except Exception as e:
                log_safe(self.log, f"[TXT→Table] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    def preview_dups(self):
        """Preview дубликатов - поддержка CSV и TXT."""
        inp = Path(self.dup_in.get().strip())
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        
        file_ext = inp.suffix.lower()
        enc = self.dup_enc.get()
        unique_only = bool(self.prev_unique.get())
        try:
            limit = int(self.prev_limit.get())
        except:
            limit = 5000

        def job():
            try:
                self._set_var(self.dup_files_var, "Files: 1")
                self._set_var(self.dup_lines_var, "Lines: …")
                self._set_var(self.dup_found_var, "Duplicates found: …")

                if file_ext == '.csv':
                    sep = self.dup_sep.get().strip() or ","
                    header = bool(self.dup_header.get())
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
                
                self._set_var(self.dup_lines_var, f"Lines: {lines_total:,}")
                self._set_var(self.dup_found_var, f"Duplicates found: {dups_total:,}")

                def print_preview():
                    self.dup_preview.configure(state='normal')
                    self.dup_preview.delete('1.0', 'end')
                    self.dup_preview.insert('end', ''.join(preview_text))
                    self.dup_preview.configure(state='disabled')
                self.after(0, print_preview)

                log_safe(self.log, f"[Find Dups] Preview готов. Показано {len(rows)} строк (из {dups_total:,}).")

            except Exception as e:
                log_safe(self.log, f"[Find Dups Preview] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    def run_find_dups(self):
        """Запуск поиска дубликатов с сохранением в файл - поддержка CSV и TXT."""
        inp = Path(self.dup_in.get().strip())
        outp = Path(self.dup_out.get().strip()) if self.dup_out.get().strip() else None
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        if outp is None:
            messagebox.showerror("Ошибка", "Укажи файл для сохранения дублей или используй Preview.")
            return

        file_ext = inp.suffix.lower()
        enc = self.dup_enc.get()

        def job():
            try:
                self._set_var(self.dup_files_var, "Files: 1")
                self._set_var(self.dup_lines_var, "Lines: …")
                self._set_var(self.dup_found_var, "Duplicates found: …")

                log_safe(self.log, f"[Find Dups] Старт: {inp} → {outp}")
                
                if file_ext == '.csv':
                    sep = self.dup_sep.get().strip() or ","
                    header = bool(self.dup_header.get())
                    try:
                        batch = int(self.dup_batch.get())
                    except:
                        batch = 20000
                    
                    lines_total, dups_written = find_duplicates_csv(inp, outp, encoding=enc, sep=sep, quotechar='"',
                                                                    has_header=header, batch=batch, log=self.log)
                else:
                    # TXT файл
                    lines_total, dups_written = find_duplicates_txt(inp, outp, encoding=enc, log=self.log)
                
                self._set_var(self.dup_lines_var, f"Lines: {lines_total:,}")
                self._set_var(self.dup_found_var, f"Duplicates found: {dups_written:,}")
            except Exception as e:
                log_safe(self.log, f"[Find Dups] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    def run_dedup(self):
        """Запуск Remove Duplicates - поддержка CSV и TXT."""
        inp = Path(self.dd_in.get().strip())
        outp = Path(self.dd_out.get().strip())
        dups = Path(self.dd_dups.get().strip()) if self.dd_dups.get().strip() else None
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        if not outp:
            messagebox.showerror("Ошибка", "Укажи выходной файл.")
            return
        
        file_ext = inp.suffix.lower()
        enc = self.dd_enc.get()

        def job():
            try:
                files = 1 + (1 if dups else 0)
                self._set_var(self.dd_files_var, f"Files: {files}")
                self._set_var(self.dd_lines_var, "Lines: …")
                self._set_var(self.dd_before_var, "Lines Before: …")
                self._set_var(self.dd_after_var, "Lines After: …")
                self._set_var(self.dd_dups_lines_var, "Duplicates Lines: —" if not dups else "Duplicates Lines: …")
                self._set_var(self.dd_removed_var, "Duplicates removed: …")

                log_safe(self.log, f"[Remove Duplicates] Старт: {inp} → {outp}")
                
                if file_ext == '.csv':
                    sep = self.dd_sep.get().strip() or ","
                    no_header = not bool(self.dd_header.get())
                    dups_header = bool(self.dd_dups_header.get())
                    total_in, total_out, dups_lines = dedupe_keep_one(inp, outp, dups, encoding=enc, sep=sep, quotechar='"',
                                                                      no_header=no_header, dups_no_header=not dups_header, log=self.log)
                else:
                    # TXT файл
                    total_in, total_out, dups_lines = dedupe_txt_keep_one(inp, outp, dups, encoding=enc, log=self.log)
                
                self._set_var(self.dd_lines_var, f"Lines: {total_in:,}")
                self._set_var(self.dd_before_var, f"Lines Before: {total_in:,}")
                self._set_var(self.dd_after_var, f"Lines After: {total_out:,}")
                self._set_var(self.dd_dups_lines_var, f"Duplicates Lines: {dups_lines:,}" if dups_lines is not None else "Duplicates Lines: —")
                self._set_var(self.dd_removed_var, f"Duplicates removed: {max(0, total_in - total_out):,}")
            except Exception as e:
                log_safe(self.log, f"[Remove Duplicates] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    def run_email_dupes(self):
        """Запуск Email Duplicates Scanner с live выводом."""
        in_path = self.ed_in.get().strip()
        col_email = (self.ed_col_email.get().strip() or "email")
        col_pass = (self.ed_col_pass.get().strip() or "pass")
        enc_in = self.ed_enc_in.get()
        out_path = self.ed_out.get().strip()

        if not in_path:
            messagebox.showerror("Ошибка", "Укажи входной CSV.")
            return

        def job():
            try:
                input_csv = Path(in_path)
                output_csv = Path(out_path) if out_path else None
                
                total, count_emails = find_email_duplicates_live(
                    input_csv, col_email, col_pass, enc_in, output_csv, self.log, self.ed_results
                )
                
                self._set_var(self.ed_files_var, "Files: 1")
                self._set_var(self.ed_lines_var, f"Lines: {total:,}")
                self._set_var(self.ed_found_var, f"Duplicates emails: {count_emails:,}")
                
            except Exception as e:
                log_safe(self.log, f"[Email Dups] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    # ====== Run Methods - Helper Tabs ======

    def run_replace(self):
        """Замена разделителя."""
        in_path = self.rep_in.get().strip()
        out_path = self.rep_out.get().strip()
        old = self.rep_old.get()
        new = self.rep_new.get()
        enc_in = self.rep_enc_in.get()
        enc_out = self.rep_enc_out.get()
        
        if not (in_path and out_path and old is not None and new is not None):
            messagebox.showerror("Ошибка", "Заполни путь к файлам и символы замены.")
            return

        def job():
            try:
                start_time = time.time()
                log_safe(self.log, f"[Replace] Замена '{old}' → '{new}' в: {in_path}")
                safe_mkdirs(out_path)
                cnt = 0
                with self.open_text_lines(in_path, enc_in) as f_in:
                    self.write_text_lines(out_path, (line.replace(old, new) for line in f_in), enc_out)
                    cnt = sum(1 for _ in self.open_text_lines(in_path, enc_in))
                total_time = time.time() - start_time
                log_safe(self.log, f"[Replace] Готово за {total_time:.1f}с. Строк обработано: {cnt:,}. Результат: {out_path}")
            except Exception as e:
                log_safe(self.log, f"[Replace] Ошибка: {e}")

        self._run_in_thread(job)

    def run_split(self):
        """Разделение email:pass."""
        in_path = self.sp_in.get().strip()
        delim = self.sp_delim.get()
        out_email = self.sp_out_email.get().strip()
        out_pass = self.sp_out_pass.get().strip()
        enc_in = self.sp_enc_in.get()
        enc_out = self.sp_enc_out.get()
        
        if not (in_path and out_email and out_pass and delim):
            messagebox.showerror("Ошибка", "Укажи входной файл, разделитель и выходные файлы.")
            return

        def job():
            try:
                start_time = time.time()
                log_safe(self.log, f"[Split] Разделение {in_path} по '{delim}'")
                safe_mkdirs(out_email)
                safe_mkdirs(out_pass)
                
                c_ok = c_bad = 0
                email_lines = []
                pass_lines = []
                
                with self.open_text_lines(in_path, enc_in) as f_in:
                    for line in f_in:
                        line = line.rstrip("\n\r")
                        if delim in line:
                            left, right = line.split(delim, 1)
                            email_lines.append(left.strip())
                            pass_lines.append(right.strip())
                            c_ok += 1
                        else:
                            c_bad += 1
                
                self.write_text_lines(out_email, email_lines, enc_out)
                self.write_text_lines(out_pass, pass_lines, enc_out)
                
                total_time = time.time() - start_time
                log_safe(self.log, f"[Split] Готово за {total_time:.1f}с. Успешно: {c_ok:,}, пропущено без разделителя: {c_bad:,}.")
                log_safe(self.log, f"   Email → {out_email}")
                log_safe(self.log, f"   Pass  → {out_pass}")
            except Exception as e:
                log_safe(self.log, f"[Split] Ошибка: {e}")

        self._run_in_thread(job)

    def run_join(self):
        """Объединение email + pass."""
        email_path = self.jn_email.get().strip()
        pass_path = self.jn_pass.get().strip()
        out_path = self.jn_out.get().strip()
        delim = self.jn_delim.get()
        enc_in = self.jn_enc_in.get()
        enc_out = self.jn_enc_out.get()
        
        if not (email_path and pass_path and out_path and delim):
            messagebox.showerror("Ошибка", "Укажи оба входных и выходной файл, плюс разделитель.")
            return

        def job():
            try:
                start_time = time.time()
                log_safe(self.log, f"[Join] Объединение {email_path} + {pass_path} через '{delim}'")
                safe_mkdirs(out_path)
                
                cnt = 0
                result_lines = []
                
                with self.open_text_lines(email_path, enc_in) as f_em, \
                     self.open_text_lines(pass_path, enc_in) as f_pw:
                    for e, p in zip(f_em, f_pw):
                        e = e.strip()
                        p = p.strip()
                        if e or p:
                            result_lines.append(f"{e}{delim}{p}")
                            cnt += 1
                
                self.write_text_lines(out_path, result_lines, enc_out)
                
                # проверим длины
                len_em = sum(1 for _ in self.open_text_lines(email_path, enc_in))
                len_pw = sum(1 for _ in self.open_text_lines(pass_path, enc_in))
                if len_em != len_pw:
                    log_safe(self.log, f"⚠️ Внимание: файлы разной длины (email={len_em:,}, pass={len_pw:,}). Лишние строки проигнорированы.")
                
                total_time = time.time() - start_time
                log_safe(self.log, f"[Join] Готово за {total_time:.1f}с. Сконкатенировано пар: {cnt:,}. Результат: {out_path}")
            except Exception as e:
                log_safe(self.log, f"[Join] Ошибка: {e}")

        self._run_in_thread(job)

    def run_csv2txt(self):
        """CSV → TXT конвертация."""
        in_path = self.ct_in.get().strip()
        out_path = self.ct_out.get().strip()
        col_email = self.ct_col_email.get().strip() or "email"
        col_pass = self.ct_col_pass.get().strip() or "pass"
        delim = self.ct_delim.get() or ":"
        enc_in = self.ct_enc_in.get()
        enc_out = self.ct_enc_out.get()

        if not (in_path and out_path):
            messagebox.showerror("Ошибка", "Укажи входной CSV и выходной TXT.")
            return

        def job():
            try:
                start_time = time.time()
                log_safe(self.log, f"[CSV→TXT] CSV → TXT: {in_path} → {out_path} | колонки: {col_email}/{col_pass}, разделитель '{delim}'")
                safe_mkdirs(out_path)
                
                c_ok = c_missing = 0
                result_lines = []
                
                with open(in_path, "r", newline="", encoding=enc_in, errors="replace") as f_in:
                    reader = csv.DictReader(f_in)
                    if not reader.fieldnames:
                        log_safe(self.log, "[CSV→TXT] Не удалось прочитать заголовки CSV.")
                        return
                    
                    missing_cols = [c for c in [col_email, col_pass] if c not in reader.fieldnames]
                    if missing_cols:
                        log_safe(self.log, f"[CSV→TXT] В CSV нет колонок: {missing_cols}")
                        return
                    
                    for row in reader:
                        e = (row.get(col_email) or "").strip()
                        p = (row.get(col_pass) or "").strip()
                        if e or p:
                            result_lines.append(f"{e}{delim}{p}")
                            c_ok += 1
                        else:
                            c_missing += 1
                
                self.write_text_lines(out_path, result_lines, enc_out)
                
                total_time = time.time() - start_time
                log_safe(self.log, f"[CSV→TXT] Готово за {total_time:.1f}с. Строк записано: {c_ok:,}, пустых пропущено: {c_missing:,}. Результат: {out_path}")
            except Exception as e:
                log_safe(self.log, f"[CSV→TXT] Ошибка: {e}")

        self._run_in_thread(job)

    def run_delete_by_list(self):
        """Удаление строк по списку."""
        src_path = self.del_src.get().strip()
        list_path = self.del_list.get().strip()
        out_path = self.del_out.get().strip()
        csv_col = self.del_csv_col.get().strip()
        enc_in = self.del_enc_in.get()
        enc_out = self.del_enc_out.get()
        ignore_case = self.del_case_ins.get()

        if not (src_path and list_path and out_path):
            messagebox.showerror("Ошибка", "Укажи источник, список для удаления и выходной файл.")
            return

        def canon(s: str) -> str:
            s2 = s.strip()
            return s2.lower() if ignore_case else s2

        def job():
            try:
                start_time = time.time()
                log_safe(self.log, f"[Delete by List] Удаление строк по списку: {src_path} - список {list_path} → {out_path}")
                safe_mkdirs(out_path)

                # Загружаем множество для удаления
                del_set: Set[str] = set()
                with self.open_text_lines(list_path, enc_in) as f_list:
                    for line in f_list:
                        s = canon(line.rstrip("\r\n"))
                        if s:
                            del_set.add(s)
                log_safe(self.log, f"[Delete by List] Загружено значений для удаления: {len(del_set):,}")

                suffix = Path(src_path).suffix.lower()
                removed = kept = 0

                if suffix == ".csv":
                    enc_read = detect_encoding(src_path) if enc_in == "auto" else enc_in
                    enc_write = "utf-8" if enc_out == "auto" else enc_out
                    with open(src_path, "r", newline="", encoding=enc_read, errors="replace") as f_in, \
                         open(out_path, "w", newline="", encoding=enc_write) as f_out:
                        reader = csv.DictReader(f_in)
                        if not reader.fieldnames:
                            log_safe(self.log, "[Delete by List] Не удалось прочитать заголовки CSV.")
                            return
                        headers = reader.fieldnames
                        writer = csv.DictWriter(f_out, fieldnames=headers)
                        writer.writeheader()

                        if csv_col and csv_col not in headers:
                            log_safe(self.log, f"[Delete by List] Колонка '{csv_col}' не найдена. Сравниваю по целой строке CSV.")

                        for row in reader:
                            if csv_col and csv_col in headers:
                                key = canon((row.get(csv_col) or ""))
                            else:
                                key = canon(",".join((row.get(h) or "").strip() for h in headers))
                            if key in del_set:
                                removed += 1
                                continue
                            writer.writerow(row)
                            kept += 1
                            
                            if kept % 100000 == 0:
                                elapsed = time.time() - start_time
                                log_safe(self.log, f"[Delete by List] Обработано: {kept:,} за {elapsed:.1f}с")

                else:
                    # TXT
                    result_lines = []
                    with self.open_text_lines(src_path, enc_in) as f_in:
                        for line in f_in:
                            raw = line.rstrip("\r\n")
                            key = canon(raw)
                            if key in del_set:
                                removed += 1
                                continue
                            result_lines.append(raw)
                            kept += 1
                            
                            if kept % 100000 == 0:
                                elapsed = time.time() - start_time
                                log_safe(self.log, f"[Delete by List] Обработано: {kept:,} за {elapsed:.1f}с")
                    
                    self.write_text_lines(out_path, result_lines, enc_out)

                total_time = time.time() - start_time
                log_safe(self.log, f"[Delete by List] Готово за {total_time:.1f}с. Оставлено: {kept:,}, удалено: {removed:,}. Результат: {out_path}")
            except Exception as e:
                log_safe(self.log, f"[Delete by List] Ошибка: {e}")

        self._run_in_thread(job)

    def run_separator(self):
        """Запуск File Separator."""
        inp = Path(self.sep_in.get().strip())
        out_dir = Path(self.sep_out_dir.get().strip()) if self.sep_out_dir.get().strip() else None
        if not inp.exists():
            messagebox.showerror("Ошибка", "Входной файл не найден.")
            return
        if not out_dir:
            messagebox.showerror("Ошибка", "Укажи папку для результатов.")
            return
        
        try:
            lines_per_file = int(self.sep_lines.get())
        except:
            messagebox.showerror("Ошибка", "Некорректное количество строк на файл.")
            return
        
        output_format = self.sep_format.get()
        enc = self.sep_enc_in.get()

        def job():
            try:
                self._set_var(self.sep_files_var, "Files: 1")
                self._set_var(self.sep_lines_var, "Lines: …")
                self._set_var(self.sep_parts_var, "Parts created: …")

                log_safe(self.log, f"[File Separator] Старт: {inp} → {out_dir}")
                total_lines, parts_created = separate_file(inp, out_dir, lines_per_file, output_format, enc, self.log)
                
                self._set_var(self.sep_lines_var, f"Lines: {total_lines:,}")
                self._set_var(self.sep_parts_var, f"Parts created: {parts_created:,}")
            except Exception as e:
                log_safe(self.log, f"[File Separator] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)

    def run_copy_files(self):
        """Запуск Copy Files."""
        method = self.copy_method.get()
        input_str = self.copy_in.get().strip()
        output_path = Path(self.copy_out.get().strip()) if self.copy_out.get().strip() else None
        
        if not input_str:
            messagebox.showerror("Ошибка", "Укажи входные файлы или папку.")
            return
        if not output_path:
            messagebox.showerror("Ошибка", "Укажи выходной файл.")
            return
        
        enc = self.copy_enc_in.get()

        def job():
            try:
                self._set_var(self.copy_files_var, "Files: …")
                self._set_var(self.copy_lines_var, "Lines: …")
                self._set_var(self.copy_total_var, "Total lines: …")

                # Получаем список файлов
                file_paths = []
                if method == "files":
                    paths = [p.strip() for p in input_str.split(";")]
                    file_paths = [Path(p) for p in paths if p and Path(p).exists()]
                else:
                    folder_path = Path(input_str)
                    if folder_path.exists() and folder_path.is_dir():
                        pattern = self.copy_pattern.get().strip() or "*.txt"
                        recursive = bool(self.copy_recursive.get())
                        if recursive:
                            file_paths = list(folder_path.rglob(pattern))
                        else:
                            file_paths = list(folder_path.glob(pattern))

                if not file_paths:
                    messagebox.showerror("Ошибка", "Файлы не найдены.")
                    return

                encoding = detect_encoding(str(file_paths[0])) if enc == "auto" else enc
                log_safe(self.log, f"[Copy Files] Старт: объединение {len(file_paths):,} файлов → {output_path}")
                
                total_files, total_lines = copy_text_files(file_paths, output_path, encoding, self.log)
                
                self._set_var(self.copy_files_var, f"Files: {total_files:,}")
                self._set_var(self.copy_total_var, f"Total lines: {total_lines:,}")
            except Exception as e:
                log_safe(self.log, f"[Copy Files] Ошибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        self._run_in_thread(job)


# ====== Main Function =========================================================

def main():
    """Запуск приложения."""
    app = UnifiedDataTools()
    app.mainloop()


if __name__ == "__main__":
    main()