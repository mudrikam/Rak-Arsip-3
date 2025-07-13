from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

class AboutDialog(QDialog):
    def __init__(self, about_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(about_config["title"])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 16, 32, 16)

        icon_path = "res/rakikon.ico"
        icon = QIcon(icon_path)
        pixmap = icon.pixmap(128, 128)
        icon_label = QLabel(self)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        title_label = QLabel(about_config["title"], self)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        layout.addWidget(title_label)

        layout.addSpacing(8)

        desc_label = QLabel(about_config["text"], self)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(8)

        line1 = QFrame(self)
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line1)

        layout.addSpacing(8)

        author_label = QLabel(f"Author: {about_config['author']}", self)
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label)

        license_label = QLabel(f"License: {about_config['license']}", self)
        license_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_label)

        if "year" in about_config:
            year_label = QLabel(f"Copyright © {about_config['year']}", self)
            year_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(year_label)
