from PySide6.QtWidgets import QApplication, QToolTip, QLineEdit, QLabel, QDateEdit
from PySide6.QtCore import QDate
from PySide6.QtGui import QCursor
from datetime import datetime

class UIHelper:
    def __init__(self, dialog):
        self.dialog = dialog

    def format_date_indonesian(self, date_str, with_time=False, language="id"):
        if language == "en":
            hari_map = {
                0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
            }
            bulan_map = {
                1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
            }
        else:
            hari_map = {
                0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"
            }
            bulan_map = {
                1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
                7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
            }
        if not date_str:
            return "-"
        try:
            if with_time:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            hari = hari_map[dt.weekday()]
            bulan = bulan_map[dt.month]
            if with_time:
                return f"{hari}, {dt.day} {bulan} {dt.year} {dt.strftime('%H:%M:%S')}"
            else:
                return f"{hari}, {dt.day} {bulan} {dt.year}"
        except Exception:
            return date_str

    def copy_detail_to_clipboard(self, key, btn=None):
        widget = self.dialog.details_widgets.get(key)
        value = ""
        if isinstance(widget, QLineEdit):
            value = widget.text()
        elif isinstance(widget, QLabel):
            value = widget.text()
        elif isinstance(widget, QDateEdit):
            value = widget.date().toString("yyyy-MM-dd")
        clipboard = self.dialog.parent().clipboard() if self.dialog.parent() and hasattr(self.dialog.parent(), "clipboard") else None
        if clipboard is None:
            clipboard = QApplication.clipboard()
        clipboard.setText(value)
        if btn is not None:
            global_pos = btn.mapToGlobal(btn.rect().bottomRight())
            QToolTip.showText(global_pos, "Copied!", btn)
