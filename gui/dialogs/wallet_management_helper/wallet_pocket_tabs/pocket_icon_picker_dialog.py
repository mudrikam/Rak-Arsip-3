from pathlib import Path
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QWidget, QGridLayout, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta


class PocketIconPickerDialog(QDialog):
    """Icon picker dialog that loads icons from configs/fontawesome-v6.4.2-free.json.

    Usage:
        dlg = PocketIconPickerDialog(parent)
        if dlg.exec_() == QDialog.Accepted:
            chosen = dlg.selected_icon  # string like 'wallet' or 'file-invoice'
    """

    def __init__(self, parent=None, current_icon: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Select Icon")
        self.resize(640, 420)
        self.selected_icon = None
        self._buttons = {}
        self._last_selected_button = None

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search icons...")
        self.search_edit.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_edit)

        self.btn_clear = QPushButton(qta.icon("fa6s.eraser"), " Clear")
        self.btn_clear.setToolTip("Clear search")
        self.btn_clear.clicked.connect(lambda: self.search_edit.clear())
        top_layout.addWidget(self.btn_clear)

        layout.addLayout(top_layout)

        # scroll area with grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # bottom controls
        bottom = QHBoxLayout()
        self.preview_label = QLabel("Selected: None")
        bottom.addWidget(self.preview_label)
        bottom.addStretch()

        self.btn_select = QPushButton(qta.icon("fa6s.check"), " Select")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self._on_select)
        bottom.addWidget(self.btn_select)

        self.btn_cancel = QPushButton(qta.icon("fa6s.circle-xmark"), " Cancel")
        self.btn_cancel.setToolTip("Cancel and close")
        self.btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(self.btn_cancel)

        layout.addLayout(bottom)

        # load icons from config
        self._icons = self._load_icons()
        self._filtered = list(self._icons)
        self._build_grid()

        # if a current icon provided, try to preselect it
        if current_icon:
            self._preselect(current_icon)

    def _load_icons(self):
        # Strict: use BASEDIR from main.py as the single source of truth for config location.
        try:
            from main import BASEDIR
        except Exception as e:
            QMessageBox.critical(self, "Error", f"BASEDIR import failed: {e}")
            return []

        cfg = Path(BASEDIR) / "configs" / "fontawesome-v6.4.2-free.json"
        if not cfg.exists():
            QMessageBox.critical(self, "Error", f"Icon config not found at expected path: {cfg}")
            return []

        icons = []
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
                # combine several style groups if present
                for key in ("solid", "regular", "brands"):
                    arr = data.get(key)
                    if isinstance(arr, list):
                        for item in arr:
                            # item may look like 'fa-wallet' or 'fa-file-invoice'
                            if item.startswith("fa-"):
                                icons.append(item[3:])
                            elif item.startswith("fa") and item.startswith("fa") and item.count("-") >= 1:
                                # keep as-is without leading 'fa'
                                icons.append(item.replace("fa", "", 1).lstrip("-"))
                            else:
                                icons.append(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load icon list: {e}")

        # dedupe while keeping order
        seen = set()
        out = []
        for name in icons:
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out

    def _build_grid(self):
        # clear existing
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        cols = max(6, int(self.width() / 80))
        row = 0
        col = 0
        self._buttons.clear()
        for name in self._filtered:
            btn = QPushButton()
            btn.setToolTip(name)
            btn.setFixedSize(QSize(64, 48))
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            try:
                icon = qta.icon(f"fa6s.{name}")
                btn.setIcon(icon)
                btn.setIconSize(QSize(24, 24))
            except Exception:
                # fallback: text label
                btn.setText(name)
            btn.clicked.connect(lambda checked, n=name, b=btn: self._on_icon_clicked(n, b))
            self.grid.addWidget(btn, row, col)
            self._buttons[name] = btn
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_icon_clicked(self, name: str, btn: QPushButton):
        # mark selection visually
        if self._last_selected_button is not None:
            self._last_selected_button.setStyleSheet("")
        btn.setStyleSheet("border: 2px solid #0078d7;")
        self._last_selected_button = btn
        self.selected_icon = name
        self.preview_label.setText(f"Selected: {name}")
        self.btn_select.setEnabled(True)

    def _on_search(self, text: str):
        text = text.strip().lower()
        if not text:
            self._filtered = list(self._icons)
        else:
            self._filtered = [n for n in self._icons if text in n.lower()]
        self._build_grid()

    def _on_select(self):
        if not self.selected_icon:
            QMessageBox.information(self, "No selection", "Please select an icon first")
            return
        self.accept()

    def get_selected_icon(self):
        return self.selected_icon

    def _preselect(self, name: str):
        # prefer exact match (name might be with/without fa6s. or fa- prefix)
        clean = name
        if name.startswith("fa6s."):
            clean = name.split('.', 1)[1]
        if name.startswith("fa-"):
            clean = name[3:]
        # if exists in list, simulate click
        if clean in self._buttons:
            self._on_icon_clicked(clean, self._buttons[clean])
