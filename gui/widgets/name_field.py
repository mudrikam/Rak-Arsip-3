from PySide6.QtWidgets import QFrame, QVBoxLayout, QLineEdit, QCheckBox, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import qtawesome as qta

class NameFieldWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)

        input_row = QHBoxLayout()
        self.line_edit = QLineEdit(self)
        self.line_edit.setMinimumHeight(40)
        self.line_edit.setStyleSheet("font-size: 20px;")
        input_row.addWidget(self.line_edit)

        self.make_btn = QPushButton("Make", self)
        self.make_btn.setIcon(qta.icon("fa6s.play"))
        self.make_btn.setFixedSize(80, 36)
        self.make_btn.setToolTip("Make")
        self.make_btn.setCursor(Qt.PointingHandCursor)
        self.make_btn.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        input_row.addWidget(self.make_btn)

        self.star_btn = QPushButton(self)
        self.star_btn.setIcon(qta.icon("fa6s.star"))
        self.star_btn.setFixedSize(36, 36)
        self.star_btn.setToolTip("Star")
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self.star_btn.setStyleSheet("border: none;")
        input_row.addWidget(self.star_btn)

        layout.addLayout(input_row)

        sanitize_row = QHBoxLayout()
        self.clear_btn = QPushButton(self)
        self.clear_btn.setIcon(qta.icon("fa6s.xmark"))
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setToolTip("Clear")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("border: none;")
        self.sanitize_check = QCheckBox("Sanitize Name", self)
        self.folder_icon_label = QLabel(self)
        self.folder_icon_label.setPixmap(qta.icon("fa6s.folder", color="#1976d2").pixmap(20, 20))
        self.sanitize_label = QLabel("-", self)
        self.sanitize_label.setStyleSheet("color: #1976d2;")
        sanitize_row.addWidget(self.clear_btn)
        sanitize_row.addWidget(self.sanitize_check)
        sanitize_row.addWidget(self.folder_icon_label)
        sanitize_row.addWidget(self.sanitize_label)
        sanitize_row.addStretch()
        layout.addLayout(sanitize_row)
        self.setLayout(layout)

        self._forbidden_chars = '<>:"/\\|?*#&$%@!^()[]{};=+`~\''

        self.line_edit.textChanged.connect(self._on_text_changed)
        self.sanitize_check.stateChanged.connect(self._on_sanitize_check_changed)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self._block_signal = False

    def _sanitize_text(self, text):
        sanitized = text.replace(" ", "_")
        sanitized = "".join(c for c in sanitized if c not in self._forbidden_chars)
        return sanitized

    def _on_text_changed(self, text):
        if self.sanitize_check.isChecked() and not self._block_signal:
            sanitized = self._sanitize_text(text)
            if sanitized != text:
                self._block_signal = True
                self.line_edit.setText(sanitized)
                self._block_signal = False

    def _on_sanitize_check_changed(self, state):
        if self.sanitize_check.isChecked():
            text = self.line_edit.text()
            sanitized = self._sanitize_text(text)
            if sanitized != text:
                self._block_signal = True
                self.line_edit.setText(sanitized)
                self._block_signal = False

    def _on_clear_clicked(self):
        self.line_edit.clear()

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

    def set_disk_and_folder_with_date(self, disk, folder, date_path, name_input):
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
            if name_input:
                path = f"{path}\\{name_input}"
            self.sanitize_label.setText(path)
        elif disk:
            if date_path:
                path = f"{disk}\\{date_path}"
                if name_input:
                    path = f"{path}\\{name_input}"
                self.sanitize_label.setText(path)
            else:
                self.sanitize_label.setText(disk)
        else:
            self.sanitize_label.setText("-")
