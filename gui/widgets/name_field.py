from PySide6.QtWidgets import QFrame, QVBoxLayout, QLineEdit, QCheckBox, QHBoxLayout, QLabel

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
        self.sanitize_label = QLabel("-", self)
        sanitize_row.addWidget(self.sanitize_check)
        sanitize_row.addWidget(self.sanitize_label)
        sanitize_row.addStretch()
        layout.addLayout(sanitize_row)
        self.setLayout(layout)

    def set_disk_and_folder(self, disk, folder):
        disk = (disk or "")
        # Ambil hanya drive letter (misal D:\) tanpa label volume
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        disk = disk.replace(" ", "")
        folder = (folder or "").replace(" ", "")
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
