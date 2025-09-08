# core/file_utils.py
"""
Утилиты для работы с файлами, кодировками и общими операциями
"""

import csv
from pathlib import Path
from typing import List, Tuple
from config import DEFAULT_DELIMS

# Для авто-детекта кодировки
try:
    import chardet
except ImportError:
    chardet = None


def detect_encoding(file_path: str, default: str = "utf-8") -> str:
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


def safe_mkdirs(filepath: str):
    """Создает директории для файла."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


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