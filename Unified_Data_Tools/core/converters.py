# core/converters.py
"""
Функции конвертации между форматами файлов (TXT→CSV/XLSX, CSV→TXT)
"""

import csv
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

from config import EXCEL_BUFFER_SIZE, EXCEL_DATA_ROWS_LIMIT, EXCEL_ENGINE
from .file_utils import decode_escapes


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
                     header1: str = "До разделителя", header2: str = "После разделителя") -> int:
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


def write_excel_single_or_split(rows: Iterable[Tuple[str, str, str]], base_xlsx_path: Path,
                                split: bool, include_source: bool,
                                header1: str = "До разделителя", header2: str = "После разделителя") -> int:
    """Записывает данные в Excel файл(ы)."""
    import pandas as pd
    base_xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    def new_writer(path: Path):
        return pd.ExcelWriter(path, engine=EXCEL_ENGINE, mode='w')

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
            if len(buf_before) >= EXCEL_BUFFER_SIZE:
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