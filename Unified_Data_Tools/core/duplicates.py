# core/duplicates.py
"""
Функции для поиска и удаления дубликатов в CSV и TXT файлах
"""

import csv
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple
from tkinter.scrolledtext import ScrolledText

from config import TECHNICAL_SEPARATOR, TEMP_DB_SUFFIX, PROGRESS_REPORT_INTERVAL
from .file_utils import decode_escapes


def row_to_key(row: List[str]) -> str:
    """Преобразует строку CSV в уникальный ключ."""
    return TECHNICAL_SEPARATOR.join("" if x is None else x for x in row)


def key_to_row(key: str) -> List[str]:
    """Обратное преобразование ключа в строку."""
    return key.split(TECHNICAL_SEPARATOR)


def log_safe(widget: Optional[ScrolledText], text: str):
    """Потокобезопасное добавление текста в лог."""
    if not widget:
        print(text)
        return
        
    def _do():
        widget.configure(state='normal')
        widget.insert('end', text + '\n')
        widget.see('end')
        widget.configure(state='disabled')
        widget.update_idletasks()
    
    try:
        widget.after(0, _do)
    except:
        print(text)


# ====== TXT Duplicates Functions ======

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
            
            if lines_total % PROGRESS_REPORT_INTERVAL == 0:
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
            
            if lines_total % PROGRESS_REPORT_INTERVAL == 0:
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
            
            if total_in % PROGRESS_REPORT_INTERVAL == 0:
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Remove Duplicates TXT] Обработано строк: {total_in:,} за {elapsed:.1f}с")
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Remove Duplicates TXT] Готово за {total_time:.1f}с. Итог сохранён: {output_txt}")
    return total_in, total_out, dups_lines_count


# ====== CSV Duplicates Functions ======

def find_duplicates_csv(input_csv: Path, output_csv: Path, encoding: str, sep: str,
                        quotechar: str, has_header: bool, batch: int,
                        log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Сохраняет дубликаты в файл. Возвращает (lines_total, duplicates_rows_written)."""
    start_time = time.time()
    out_dir = output_csv.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    sep = decode_escapes(sep)

    db_path = output_csv.with_suffix(output_csv.suffix + TEMP_DB_SUFFIX)
    if db_path.exists():
        db_path.unlink(missing_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("CREATE TABLE IF NOT EXISTS t (key TEXT PRIMARY KEY, cnt INTEGER NOT NULL);")

    lines_total = 0

    with open(input_csv, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=sep, quotechar=quotechar)
        first = next(reader, None)
        if first is None:
            with open(output_csv, "w", encoding="utf-8", newline="") as g:
                pass
            conn.close()
            db_path.unlink(missing_ok=True)
            if log: log_safe(log, "[Find Dups] Файл пуст — дубликатов нет.")
            return 0, 0

        data_iter = [] if has_header else [first]
        cur = conn.cursor()

        def upsert_many(rows):
            cur.executemany(
                "INSERT INTO t(key, cnt) VALUES (?, 1) "
                "ON CONFLICT(key) DO UPDATE SET cnt = cnt + 1;",
                ((row_to_key(r),) for r in rows)
            )

        buf = []
        if data_iter:
            buf.extend(data_iter)
        for row in reader:
            buf.append(row)
            if len(buf) >= batch:
                upsert_many(buf)
                conn.commit()
                lines_total += len(buf)
                elapsed = time.time() - start_time
                if log: log_safe(log, f"[Find Dups] Прочитано строк: {lines_total:,} за {elapsed:.1f}с…")
                buf.clear()
        if buf:
            upsert_many(buf)
            conn.commit()
            lines_total += len(buf)
            elapsed = time.time() - start_time
            if log: log_safe(log, f"[Find Dups] Прочитано строк: {lines_total:,} за {elapsed:.1f}с… (завершено чтение)")
            buf.clear()
        cur.close()

    dups_written = 0
    with open(output_csv, "w", encoding="utf-8", newline="") as g:
        writer = csv.writer(g, delimiter=sep, quotechar=quotechar)
        cur = conn.cursor()
        groups = 0
        for key, cnt in cur.execute("SELECT key, cnt FROM t WHERE cnt > 1"):
            groups += 1
            row = key_to_row(key)
            for _ in range(cnt):
                writer.writerow(row)
                dups_written += 1
            if log and groups % 50000 == 0:
                elapsed = time.time() - start_time
                log_safe(log, f"[Find Dups] Записано групп дублей: {groups:,} (строк: {dups_written:,}) за {elapsed:.1f}с…")
        cur.close()

    conn.close()
    db_path.unlink(missing_ok=True)
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Find Dups] Готово за {total_time:.1f}с. Дубликаты сохранены: {output_csv}")
    return lines_total, dups_written


def preview_duplicates_csv(input_csv: Path, encoding: str, sep: str, has_header: bool,
                           unique_only: bool, limit: int,
                           log: Optional[ScrolledText] = None) -> Tuple[int, List[List[str]], int]:
    """Возвращает (lines_total, preview_rows, total_duplicate_rows)."""
    start_time = time.time()
    sep = decode_escapes(sep)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (key TEXT PRIMARY KEY, cnt INTEGER NOT NULL)")
    lines_total = 0

    with open(input_csv, "r", encoding=encoding, newline="") as f:
        r = csv.reader(f, delimiter=sep, quotechar='"')
        first = next(r, None)
        if first is None:
            if log: log_safe(log, "[Find Dups] Файл пуст — дубликатов нет.")
            return 0, [], 0
        rows_iter = [] if has_header else [first]

        cur = conn.cursor()
        def upsert_many(rows):
            cur.executemany(
                "INSERT INTO t(key, cnt) VALUES (?, 1) "
                "ON CONFLICT(key) DO UPDATE SET cnt = cnt + 1;",
                ((row_to_key(x),) for x in rows)
            )

        buf = []
        if rows_iter:
            buf.extend(rows_iter)

        next_log_mark = PROGRESS_REPORT_INTERVAL

        for row in r:
            buf.append(row)
            if len(buf) >= 20000:
                upsert_many(buf); conn.commit()
                lines_total += len(buf); buf.clear()
                if log and lines_total >= next_log_mark:
                    elapsed = time.time() - start_time
                    log_safe(log, f"[Find Dups] Прочитано строк: {lines_total:,} за {elapsed:.1f}с…")
                    next_log_mark += PROGRESS_REPORT_INTERVAL
        if buf:
            upsert_many(buf); conn.commit()
            lines_total += len(buf); buf.clear()
            elapsed = time.time() - start_time
            if log:
                log_safe(log, f"[Find Dups] Прочитано строк: {lines_total:,} за {elapsed:.1f}с… (завершено чтение)")

        cur.close()

    preview: List[List[str]] = []
    total_dup_rows = 0
    dup_groups = 0
    cur = conn.cursor()
    for key, cnt in cur.execute("SELECT key, cnt FROM t WHERE cnt > 1"):
        dup_groups += 1
        row = key_to_row(key)
        total_dup_rows += cnt
        if unique_only:
            if len(preview) < limit:
                preview.append(row)
        else:
            for _ in range(cnt):
                if len(preview) < limit:
                    preview.append(row)
    cur.close()
    conn.close()

    total_time = time.time() - start_time
    if log:
        log_safe(log, f"[Find Dups] Найдено групп дублей: {dup_groups:,}; всего строк-дубликатов: {total_dup_rows:,} за {total_time:.1f}с.")
    return lines_total, preview, total_dup_rows


def dedupe_keep_one(input_csv: Path, output_csv: Path, dups_csv: Optional[Path],
                    encoding: str, sep: str, quotechar: str,
                    no_header: bool, dups_no_header: bool,
                    log: Optional[ScrolledText] = None) -> Tuple[int, int, Optional[int]]:
    """Возвращает (total_in, total_out, dups_lines_or_None)."""
    start_time = time.time()
    sep = decode_escapes(sep)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    dup_keys = set()
    dups_lines_count: Optional[int] = None
    if dups_csv:
        dups_lines_count = 0
        with open(dups_csv, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=sep, quotechar=quotechar)
            first = next(reader, None)
            if first is not None:
                if dups_no_header:
                    dup_keys.add(row_to_key(first)); dups_lines_count += 1
                for row in reader:
                    dup_keys.add(row_to_key(row)); dups_lines_count += 1
        if log: log_safe(log, f"Загружено уникальных ключей дублей: {len(dup_keys)}; строк в файле дублей: {dups_lines_count}")

    seen_any = set()
    kept_from_dups = set()
    total_in = 0
    total_out = 0

    with open(input_csv, "r", encoding=encoding, newline="") as fin, \
         open(output_csv, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin, delimiter=sep, quotechar=quotechar)
        writer = csv.writer(fout, delimiter=sep, quotechar=quotechar)

        first = next(reader, None)
        if first is None:
            total_time = time.time() - start_time
            if log: log_safe(log, f"[Remove Duplicates] Готово за {total_time:.1f}с. Входной файл пуст.")
            return 0, 0, dups_lines_count

        data_iter = [first] if no_header else []
        if not no_header:
            writer.writerow(first)

        def process_row(row: List[str]):
            nonlocal total_in, total_out
            total_in += 1
            key = row_to_key(row)
            if dup_keys:
                if key in dup_keys:
                    if key in kept_from_dups:
                        return
                    kept_from_dups.add(key)
                    writer.writerow(row); total_out += 1
                else:
                    writer.writerow(row); total_out += 1
            else:
                if key in seen_any:
                    return
                seen_any.add(key)
                writer.writerow(row); total_out += 1

        for row in data_iter:
            process_row(row)
        for i, row in enumerate(reader, 1):
            process_row(row)
            if log and i % PROGRESS_REPORT_INTERVAL == 0:
                elapsed = time.time() - start_time
                log_safe(log, f"[Remove Duplicates] Обработано строк: {i:,} за {elapsed:.1f}с")

    total_time = time.time() - start_time
    if log: log_safe(log, f"[Remove Duplicates] Готово за {total_time:.1f}с. Итог сохранён: {output_csv}")
    return total_in, total_out, dups_lines_count