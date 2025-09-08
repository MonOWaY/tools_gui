# core/email_scanner.py
"""
Сканер email дубликатов с live выводом результатов
"""

import csv
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from tkinter.scrolledtext import ScrolledText

from config import EMAIL_REPORT_INTERVAL, EMAIL_BATCH_SIZE
from .file_utils import safe_mkdirs
from .duplicates import log_safe


def find_email_duplicates_live(input_csv: Path, col_email: str, col_pass: str, encoding: str,
                               output_csv: Optional[Path], log: Optional[ScrolledText],
                               results_widget: Optional[ScrolledText]) -> Tuple[int, int]:
    """Live поиск повторных email с разными паролями."""
    start_time = time.time()
    if log: log_safe(log, f"→ Поиск повторных email с разными паролями (LIVE): {input_csv}")
    enc_read = "utf-8" if encoding == "auto" else encoding

    next_report = EMAIL_REPORT_INTERVAL
    passes_by_email: Dict[str, Set[str]] = {}
    rows_by_email: Dict[str, List[Dict[str, str]]] = {}
    emitted_email: Set[str] = set()
    batch_lines: List[str] = []

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
                next_report += EMAIL_REPORT_INTERVAL

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
                        if len(batch_lines) >= EMAIL_BATCH_SIZE:
                            append_result_lines(batch_lines)
                            batch_lines.clear()
                elif e in emitted_email:
                    batch_lines.append(f"{row.get(col_email,'')},{row.get(col_pass,'')}\n")
                    if len(batch_lines) >= EMAIL_BATCH_SIZE:
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