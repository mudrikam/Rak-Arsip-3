from datetime import datetime
import sys


def show_statusbar_message(widget, message, timeout=2000):
    main_window = widget.window()
    if hasattr(main_window, "statusBar"):
        statusbar = main_window.statusBar()
        if statusbar:
            statusbar.showMessage(message, timeout)


def get_datetime_string():
    now = datetime.now()
    if sys.platform == "win32":
        return now.strftime("%#d\\%B\\%Y %H:%M")
    else:
        return now.strftime("%-d\\%B\\%Y %H:%M")
