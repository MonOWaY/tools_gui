# core/file_ops.py
"""
Операции с файлами: разделение больших файлов, объединение множества файлов
"""

import csv
import time
from pathlib import Path
from typing import List, Optional, Tuple
from tkinter.scrolledtext import ScrolledText

from config import RESULT_FOLDER_TEMPLATE, RESULT_FILE_TEMPLATE, SEPARATOR_PROGRESS_INTERVAL
from .duplicates import log_safe


def separate_file(input_path: Path, output_dir: Path, lines_per_file: int, output_format: str,
                  input_encoding: str, log: Optional[ScrolledText] = None) -> Tuple[int, int]:
    """Разделяет большой файл на множество маленьких."""
    start_time = time.time()
    
    timestamp = time.strftime("%m%d_%H%M")
    result_dir = output_dir / RESULT_FOLDER_TEMPLATE.format(timestamp=timestamp)
    result_dir.mkdir(parents=True, exist_ok=True)
    
    current_part = 1
    current_lines = 0
    total_lines = 0
    
    input_ext = input_path.suffix.lower()
    file_timestamp = time.strftime("%H%M")
    
    if input_ext == '.csv' and output_format == 'csv':
        # CSV to CSV - сохраняем заголовки
        with open(input_path, 'r', encoding=input_encoding, errors='replace', newline='') as infile:
            reader = csv.reader(infile)
            headers = next(reader, None)
            
            if headers:
                current_file_path = result_dir / RESULT_FILE_TEMPLATE.format(
                    timestamp=file_timestamp, part=current_part, ext="csv"
                )
                current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                writer = csv.writer(current_file)
                writer.writerow(headers)
                
                for row in reader:
                    if current_lines >= lines_per_file:
                        current_file.close()
                        current_part += 1
                        current_lines = 0
                        current_file_path = result_dir / RESULT_FILE_TEMPLATE.format(
                            timestamp=file_timestamp, part=current_part, ext="csv"
                        )
                        current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                        writer = csv.writer(current_file)
                        writer.writerow(headers)
                    
                    writer.writerow(row)
                    current_lines += 1
                    total_lines += 1
                    
                    if total_lines % SEPARATOR_PROGRESS_INTERVAL == 0:
                        elapsed = time.time() - start_time
                        if log: log_safe(log, f"[File Separator] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
                
                current_file.close()
    else:
        # Обычная обработка построчно
        current_file_path = result_dir / RESULT_FILE_TEMPLATE.format(
            timestamp=file_timestamp, part=current_part, ext=output_format
        )
        current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
        
        with open(input_path, 'r', encoding=input_encoding, errors='replace') as infile:
            for line in infile:
                if current_lines >= lines_per_file:
                    current_file.close()
                    current_part += 1
                    current_lines = 0
                    current_file_path = result_dir / RESULT_FILE_TEMPLATE.format(
                        timestamp=file_timestamp, part=current_part, ext=output_format
                    )
                    current_file = open(current_file_path, 'w', encoding='utf-8', newline='')
                
                current_file.write(line)
                current_lines += 1
                total_lines += 1
                
                if total_lines % SEPARATOR_PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    if log: log_safe(log, f"[File Separator] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
        
        current_file.close()
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[File Separator] Готово за {total_time:.1f}с. Создано {current_part} файлов в: {result_dir}")
    return total_lines, current_part


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
                        
                        if total_lines % SEPARATOR_PROGRESS_INTERVAL == 0:
                            elapsed = time.time() - start_time
                            if log: log_safe(log, f"[Copy Files] Обработано строк: {total_lines:,} за {elapsed:.1f}с")
                    
                    if log: log_safe(log, f"[Copy Files] Файл {file_path.name}: {file_lines:,} строк")
            except Exception as e:
                if log: log_safe(log, f"[Copy Files] Ошибка при обработке {file_path}: {e}")
    
    total_time = time.time() - start_time
    if log: log_safe(log, f"[Copy Files] Готово за {total_time:.1f}с. Объединено {total_files} файлов, {total_lines:,} строк в: {output_path}")
    return total_files, total_lines