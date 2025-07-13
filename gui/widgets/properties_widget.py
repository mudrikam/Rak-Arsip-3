from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class PropertiesWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        container = QWidget(self)
        layout = QVBoxLayout(container)

        self.image_frame = QFrame(container)
        self.image_frame.setFixedSize(180, 180)
        self.image_label = QLabel(self.image_frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setGeometry(0, 0, 180, 180)
        layout.addWidget(self.image_frame)

        self.date_label = QLabel("Date: -", container)
        layout.addWidget(self.date_label)

        self.name_label = QLabel("Name: -", container)
        layout.addWidget(self.name_label)

        self.status_label = QLabel("Status: -", container)
        layout.addWidget(self.status_label)

        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)
        container.setLayout(layout)
        self.setWidget(container)
