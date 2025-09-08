# config.py
"""
Конфигурационные константы для Unified Data Tools
"""

# Общие константы
DEFAULT_DELIMS = [';', ':']
EXCEL_MAX_ROWS = 1_048_576
EXCEL_DATA_ROWS_LIMIT = EXCEL_MAX_ROWS - 1
TECHNICAL_SEPARATOR = "\x1f"  # для ключей CSV строк

# Настройки обработки файлов
DEFAULT_BATCH_SIZE = 20000
PROGRESS_REPORT_INTERVAL = 100000
SEPARATOR_PROGRESS_INTERVAL = 100000

# Кодировки по умолчанию
DEFAULT_ENCODINGS = ["utf-8-sig", "utf-8", "cp1251", "utf-16", "iso-8859-1"]
AUTO_DETECT_ENCODING = "auto"

# GUI настройки
DEFAULT_WINDOW_SIZE = "1200x900"
LOG_HEIGHT = 12
PREVIEW_LIMIT = 5000

# Настройки Excel
EXCEL_BUFFER_SIZE = 50000
EXCEL_ENGINE = "openpyxl"

# Настройки File Separator
DEFAULT_LINES_PER_FILE = 1000000
RESULT_FOLDER_TEMPLATE = "Result_{timestamp}"
RESULT_FILE_TEMPLATE = "result_{timestamp}_{part}.{ext}"

# Email Scanner настройки  
EMAIL_REPORT_INTERVAL = 50000
EMAIL_BATCH_SIZE = 100

# Временные файлы
TEMP_DB_SUFFIX = ".dups_tmp.sqlite3"