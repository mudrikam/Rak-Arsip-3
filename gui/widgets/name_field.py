from PySide6.QtWidgets import QFrame, QVBoxLayout, QLineEdit, QCheckBox, QHBoxLayout, QLabel
from PySide6.QtGui import QIcon
import qtawesome as qta

class NameFieldWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        self.line_edit = QLineEdit(self)
        self.line_edit.setMinimumHeight(40)
        self.line_edit.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.line_edit)
        sanitize_row = QHBoxLayout()
        self.sanitize_check = QCheckBox("Sanitize Name", self)
        self.folder_icon_label = QLabel(self)
        self.folder_icon_label.setPixmap(qta.icon("fa6s.folder", color="#1976d2").pixmap(20, 20))
        self.sanitize_label = QLabel("-", self)
        self.sanitize_label.setStyleSheet("color: #1976d2;")
        sanitize_row.addWidget(self.sanitize_check)
        sanitize_row.addWidget(self.folder_icon_label)
        sanitize_row.addWidget(self.sanitize_label)
        sanitize_row.addStretch()
        layout.addLayout(sanitize_row)
        self.setLayout(layout)

    def set_disk_and_folder(self, disk, folder):
        disk = (disk or "")
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        if disk and folder:
            if disk.endswith("\\") or disk.endswith("/"):
                path = f"{disk}{folder}"
            else:
                path = f"{disk}\\{folder}"
            self.sanitize_label.setText(path)
        elif disk:
            self.sanitize_label.setText(disk)
        else:
            self.sanitize_label.setText("-")

    def set_disk_and_folder_with_date(self, disk, folder, date_path):
        disk = (disk or "")
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        path = ""
        if disk and folder:
            if disk.endswith("\\") or disk.endswith("/"):
                path = f"{disk}{folder}"
            else:
                path = f"{disk}\\{folder}"
            if date_path:
                path = f"{path}\\{date_path}"
            self.sanitize_label.setText(path)
        elif disk:
            if date_path:
                path = f"{disk}\\{date_path}"
                self.sanitize_label.setText(path)
            else:
                self.sanitize_label.setText(disk)
        else:
            self.sanitize_label.setText("-")
