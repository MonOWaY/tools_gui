# gui/utils.py
"""
Утилиты для GUI: логирование, потокобезопасность, общие функции
"""

import threading
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox


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
        print(text)


def run_in_thread(func, *args, **kwargs):
    """Запускает функцию в отдельном потоке."""
    def safe_run():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Thread error: {e}")
            # Можно добавить логирование в GUI если нужно
    
    t = threading.Thread(target=safe_run, daemon=True)
    t.start()


def show_error(title: str, message: str):
    """Показывает диалог ошибки."""
    messagebox.showerror(title, message)


def show_info(title: str, message: str):
    """Показывает информационный диалог."""
    messagebox.showinfo(title, message)