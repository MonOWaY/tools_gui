# core/__init__.py
"""
Core модуль с основными функциями обработки данных
"""

from .file_utils import (
    detect_encoding,
    decode_escapes, 
    parse_delims,
    parse_delims_input,
    safe_mkdirs,
    scan_txt_stats,
    scan_csv_lines
)

from .duplicates import (
    find_duplicates_csv,
    preview_duplicates_csv,
    dedupe_keep_one,
    find_duplicates_txt,
    preview_duplicates_txt,
    dedupe_txt_keep_one,
    row_to_key,
    key_to_row
)

from .converters import (
    iter_rows_from_input,
    write_csv_stream,
    write_excel_single_or_split,
    find_split
)

from .file_ops import (
    separate_file,
    copy_text_files
)

from .email_scanner import (
    find_email_duplicates_live
)

__all__ = [
    # File utilities
    'detect_encoding', 'decode_escapes', 'parse_delims', 'parse_delims_input',
    'safe_mkdirs', 'scan_txt_stats', 'scan_csv_lines',
    
    # Duplicates
    'find_duplicates_csv', 'preview_duplicates_csv', 'dedupe_keep_one',
    'find_duplicates_txt', 'preview_duplicates_txt', 'dedupe_txt_keep_one',
    'row_to_key', 'key_to_row',
    
    # Converters
    'iter_rows_from_input', 'write_csv_stream', 'write_excel_single_or_split', 'find_split',
    
    # File operations
    'separate_file', 'copy_text_files',
    
    # Email scanner
    'find_email_duplicates_live'
]