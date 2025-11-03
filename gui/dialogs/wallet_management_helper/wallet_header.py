from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
import qtawesome as qta


class WalletHeader(QWidget):
    """Reusable page header for wallet pages.

    Usage:
        header = WalletHeader("Title", "Optional subtitle")
        header.add_action(icon="fa6s.plus", text=" Add", callback=self.on_add)
    """

    def __init__(self, title: str, subtitle: str = None, parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        text_layout.addWidget(self.title_label)

        if self._subtitle:
            self.subtitle_label = QLabel(self._subtitle)
            self.subtitle_label.setStyleSheet("color: #666; font-size: 12px;")
            text_layout.addWidget(self.subtitle_label)
        else:
            # keep layout consistent
            spacer = QLabel("")
            spacer.setFixedHeight(0)
            text_layout.addWidget(spacer)

        layout.addLayout(text_layout)
        layout.addStretch()

        # area for action buttons (populate via add_action)
        self._actions_layout = QHBoxLayout()
        self._actions_layout.setSpacing(6)
        layout.addLayout(self._actions_layout)

        self.setLayout(layout)

    def add_action(self, icon: str = None, text: str = "", callback=None):
        """Add an action button to the header.

        icon: qtawesome icon name (e.g. 'fa6s.plus') or None
        text: button text
        callback: callable connected to clicked
        Returns the created QPushButton.
        """
        if icon:
            try:
                btn = QPushButton(qta.icon(icon), text)
            except Exception:
                btn = QPushButton(text)
        else:
            btn = QPushButton(text)

        if callback:
            try:
                btn.clicked.connect(callback)
            except Exception:
                pass

        self._actions_layout.addWidget(btn)
        return btn
