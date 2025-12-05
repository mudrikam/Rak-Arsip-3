from datetime import datetime
import sys
from PySide6.QtWidgets import QStatusBar, QMainWindow


def find_main_window(widget):
    parent = widget
    while parent is not None:
        if isinstance(parent, QMainWindow):
            return parent
        parent = parent.parent()
    return widget.window()


def show_statusbar_message(widget, message, timeout=3000):
    main_window = find_main_window(widget)
    if hasattr(main_window, "statusBar"):
        statusbar = main_window.statusBar()
        if statusbar:
            statusbar.showMessage(message, timeout)


def get_datetime_string():
    now = datetime.now()
    if sys.platform == "win32":
        return now.strftime("%#d\\%B\\%Y %H:%M")
