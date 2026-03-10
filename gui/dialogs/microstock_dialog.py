from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QMenu, QApplication, QToolTip, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QAction, QPixmap
import qtawesome as qta
import webbrowser
from pathlib import Path


class _NoWheelCombo(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class MicrostockDialog(QDialog):
    """Dialog to manage microstock upload status per platform for a file.

    Shows every platform as a row. The Status column is a combo box — choosing
    a status saves the assignment immediately. Choosing the blank top option
    removes any existing assignment for that platform.
    """

    def __init__(self, file_record, db_manager, status_config, parent=None):
        super().__init__(parent)
        self.file_record = file_record
        self.db_manager = db_manager
        self.status_config = status_config
        self._statuses = []
        self._blocking = False
        self.setWindowTitle(f"Microstock: {file_record.get('name', '')}")
        self.setMinimumSize(780, 440)
        self.setModal(True)
        self._init_ui()
        self._load_statuses()
        self._load_table()
        self._load_preview()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # === Body: left panel + table side by side ===
        body = QHBoxLayout()
        body.setSpacing(8)

        # --- Left panel ---
        left = QWidget()
        left.setFixedWidth(185)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(180, 150)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("No Preview")
        self.preview_label.setStyleSheet(
            "background:#1e1e1e; border:1px solid #333; border-radius:4px; color:#666;"
        )
        left_layout.addWidget(self.preview_label)

        def _detail(icon_name, text):
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            ic = QLabel()
            ic.setPixmap(qta.icon(icon_name, color="#888").pixmap(13, 13))
            ic.setFixedSize(13, 13)
            lbl = QLabel(str(text) if text else "-")
            lbl.setWordWrap(True)
            lbl.setMaximumWidth(168)
            h.addWidget(ic)
            h.addWidget(lbl, 1)
            return h

        name = self.file_record.get('name') or '-'
        date = self.file_record.get('date') or '-'
        status = self.file_record.get('status') or '-'
        category = self.file_record.get('category') or ''
        subcategory = self.file_record.get('subcategory') or ''
        cat_text = f"{category}/{subcategory}" if category and subcategory else (category or subcategory or '-')

        left_layout.addLayout(_detail("fa6s.file-lines", name))
        left_layout.addLayout(_detail("fa6s.calendar", date))
        left_layout.addLayout(_detail("fa6s.circle-info", status))
        left_layout.addLayout(_detail("fa6s.folder-tree", cat_text))
        left_layout.addStretch()
        body.addWidget(left)

        # --- Right panel: table ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Platform", "Status", "Platform URL", "Description", "Note"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.resizeSection(0, 150)
        header.resizeSection(1, 150)
        header.resizeSection(2, 160)
        right_layout.addWidget(self.table)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        body.addLayout(right_layout, 1)
        outer.addLayout(body)

        hint = QLabel("Tip: Select a status to assign it directly.")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        outer.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(qta.icon("fa6s.xmark"), " Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)

    def _load_statuses(self):
        try:
            self._statuses = self.db_manager.get_all_microstock_statuses()
        except Exception as e:
            print(f"[Microstock] Error loading statuses: {e}")
            self._statuses = []

    def _load_table(self):
        """Build one row per platform; status column is a live combo box."""
        self._blocking = True
        self.table.setRowCount(0)
        try:
            all_platforms = self.db_manager.get_all_microstock_platforms()
            assignments = self.db_manager.get_file_microstock_statuses(self.file_record["id"])
            assigned_map = {a["platform_id"]: a for a in assignments}

            self.table.setRowCount(len(all_platforms))
            for row_idx, p in enumerate(all_platforms):
                platform_id = p["id"]
                platform_name = p["platform_name"]
                platform_url = p["platform_url"] or ""
                platform_desc = p["platform_description"] or ""
                platform_note = p["platform_note"] or ""

                name_item = QTableWidgetItem(platform_name)
                name_item.setData(Qt.UserRole, platform_id)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                tip = platform_name
                if platform_url:
                    tip += f"\nURL: {platform_url}"
                if platform_desc:
                    tip += f"\n{platform_desc}"
                if platform_note:
                    tip += f"\nNote: {platform_note}"
                name_item.setToolTip(tip)
                self.table.setItem(row_idx, 0, name_item)

                combo = _NoWheelCombo()
                for s in self._statuses:
                    combo.addItem(s["name"], s["id"])

                current_assignment = assigned_map.get(platform_id)
                if current_assignment:
                    for i in range(combo.count()):
                        if combo.itemData(i) == current_assignment["status_id"]:
                            combo.setCurrentIndex(i)
                            color = next((s["color"] for s in self._statuses if s["id"] == current_assignment["status_id"]), None)
                            self._apply_combo_color(combo, color)
                            break
                else:
                    for i in range(combo.count()):
                        if combo.itemText(i) == "Draft":
                            combo.setCurrentIndex(i)
                            color = next((s["color"] for s in self._statuses if s["name"] == "Draft"), None)
                            self._apply_combo_color(combo, color)
                            break

                combo.currentIndexChanged.connect(
                    lambda idx, pid=platform_id, cb=combo: self._on_status_changed(pid, cb)
                )
                self.table.setCellWidget(row_idx, 1, combo)

                def _item(text, tooltip=None):
                    it = QTableWidgetItem(text)
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    if tooltip:
                        it.setToolTip(tooltip)
                    elif text:
                        it.setToolTip(text)
                    return it

                self.table.setItem(row_idx, 2, _item(platform_url))
                self.table.setItem(row_idx, 3, _item(platform_desc))
                self.table.setItem(row_idx, 4, _item(platform_note))

        except Exception as e:
            print(f"[Microstock] Error loading table: {e}")
        finally:
            self._blocking = False

    def _find_first_image(self, directory, supported, max_depth=3, _depth=0):
        """Recursively find the first image in directory (same strategy as properties widget)."""
        if _depth > max_depth:
            return None
        try:
            items = sorted(directory.iterdir(), key=lambda x: (x.is_dir(), str(x).lower()))
            for item in items:
                if item.is_file() and item.suffix.lower() in supported:
                    return item
            for item in items:
                if item.is_dir():
                    result = self._find_first_image(item, supported, max_depth, _depth + 1)
                    if result:
                        return result
        except Exception:
            pass
        return None

    def _load_preview(self):
        file_path = self.file_record.get('path', '')
        file_name = self.file_record.get('name', '')
        if not file_path:
            return
        try:
            path_obj = Path(file_path)
            directory = path_obj if path_obj.is_dir() else path_obj.parent
            if not directory.exists():
                return
            supported = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.tif']
            image_path = None

            # 1. preview/ subdir with exact name
            preview_dir = directory / "preview"
            if preview_dir.exists() and preview_dir.is_dir():
                for ext in supported:
                    candidate = preview_dir / f"{file_name}{ext}"
                    if candidate.is_file():
                        image_path = candidate
                        break

            # 2. Root dir with exact name
            if not image_path:
                for ext in supported:
                    candidate = directory / f"{file_name}{ext}"
                    if candidate.is_file():
                        image_path = candidate
                        break

            # 3. Recursive scan: preview/ first, then directory
            if not image_path and preview_dir.exists():
                image_path = self._find_first_image(preview_dir, supported)

            if not image_path:
                image_path = self._find_first_image(directory, supported)

            if image_path:
                pixmap = QPixmap(str(image_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(180, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_label.setPixmap(scaled)
                    self.preview_label.setText("")
        except Exception as e:
            print(f"[Microstock Preview] Error: {e}")

    def _apply_combo_color(self, combo, color):
        if color:
            combo.setStyleSheet(f"color: {color};")
        else:
            combo.setStyleSheet("")

    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        url_item = self.table.item(row, 2)
        url = url_item.text().strip() if url_item else ""

        menu = QMenu(self.table)
        action_open = QAction(qta.icon("fa6s.globe"), "Open URL in Browser", self)
        action_copy_url = QAction(qta.icon("fa6s.copy"), "Copy URL", self)
        action_open.setEnabled(bool(url))
        action_copy_url.setEnabled(bool(url))

        def do_open():
            webbrowser.open(url)

        def do_copy():
            QApplication.clipboard().setText(url)
            QToolTip.showText(QCursor.pos(), f"{url}\nCopied to clipboard")

        action_open.triggered.connect(do_open)
        action_copy_url.triggered.connect(do_copy)
        menu.addAction(action_open)
        menu.addAction(action_copy_url)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_status_changed(self, platform_id, combo):
        if self._blocking:
            return
        status_id = combo.currentData()
        file_id = self.file_record["id"]
        try:
            if status_id is None:
                self.db_manager.delete_file_microstock_status(file_id, platform_id)
                combo.setStyleSheet("")
            else:
                self.db_manager.upsert_file_microstock_status(file_id, platform_id, status_id)
                color = next((s["color"] for s in self._statuses if s["id"] == status_id), None)
                self._apply_combo_color(combo, color)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save status: {e}")
