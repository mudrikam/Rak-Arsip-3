from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QMessageBox, QDialog, QFormLayout, QTextEdit, QLabel, QApplication, QToolTip
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor
import qtawesome as qta


class PlatformEditDialog(QDialog):
    """Dialog for adding or editing a microstock platform."""

    def __init__(self, name="", url="", description="", note="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Platform Details")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setText(name)
        self.name_edit.setPlaceholderText("e.g. Freepik, Shutterstock...")
        form.addRow("Name *:", self.name_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setText(url)
        self.url_edit.setPlaceholderText("https://...")

        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(4)
        url_row.addWidget(self.url_edit, 1)
        paste_btn = QPushButton()
        paste_btn.setIcon(qta.icon("fa6s.paste"))
        paste_btn.setFixedSize(30, 30)
        paste_btn.setToolTip("Paste from clipboard")
        paste_btn.setFocusPolicy(Qt.NoFocus)
        paste_btn.clicked.connect(self._paste_url)
        url_row.addWidget(paste_btn)

        url_widget = QWidget()
        url_widget.setLayout(url_row)
        form.addRow("URL:", url_widget)

        self.description_edit = QLineEdit()
        self.description_edit.setText(description)
        self.description_edit.setPlaceholderText("Short description...")
        form.addRow("Description:", self.description_edit)

        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(note)
        self.note_edit.setPlaceholderText("Additional notes...")
        self.note_edit.setMaximumHeight(80)
        form.addRow("Note:", self.note_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(qta.icon("fa6s.check"), " Save")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton(qta.icon("fa6s.xmark"), " Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _paste_url(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_edit.setText(text)

    def _on_save(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Platform name cannot be empty.")
            return
        self.accept()

    def get_values(self):
        return (
            self.name_edit.text().strip(),
            self.url_edit.text().strip(),
            self.description_edit.text().strip(),
            self.note_edit.toPlainText().strip()
        )


class PreferencesMicrostockHelper:
    """Helper for the Microstock tab in the Preferences window."""

    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager

    def create_microstock_tab(self):
        """Create and return the Microstock tab widget."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Microstock Platforms")
        group_layout = QVBoxLayout(group)

        # Toolbar row
        row = QHBoxLayout()
        self.parent.microstock_search_edit = QLineEdit()
        self.parent.microstock_search_edit.setPlaceholderText("Search platform name or description...")
        self.parent.microstock_search_edit.setMinimumHeight(32)
        self.parent.microstock_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.parent.microstock_search_edit, 1)
        row.addStretch()

        self.parent.microstock_add_btn = QPushButton(qta.icon("fa6s.plus"), " Add Platform")
        self.parent.microstock_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), " Edit Platform")
        self.parent.microstock_delete_btn = QPushButton(qta.icon("fa6s.trash"), " Delete Platform")
        row.addWidget(self.parent.microstock_add_btn)
        row.addWidget(self.parent.microstock_edit_btn)
        row.addWidget(self.parent.microstock_delete_btn)
        group_layout.addLayout(row)

        # Table
        self.parent.microstock_table = QTableWidget()
        self.parent.microstock_table.setColumnCount(5)
        self.parent.microstock_table.setHorizontalHeaderLabels(
            ["Name", "URL", "Description", "Note", "Files"]
        )
        self.parent.microstock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.parent.microstock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.parent.microstock_table.setSelectionMode(QTableWidget.SingleSelection)
        header = self.parent.microstock_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(0, 160)
        header.resizeSection(1, 220)
        header.resizeSection(4, 60)
        group_layout.addWidget(self.parent.microstock_table)
        layout.addWidget(group)

        # Signals
        self.parent.microstock_add_btn.clicked.connect(self.on_platform_add)
        self.parent.microstock_edit_btn.clicked.connect(self.on_platform_edit)
        self.parent.microstock_delete_btn.clicked.connect(self.on_platform_delete)
        self.parent.microstock_table.cellDoubleClicked.connect(self.on_platform_edit)
        self.parent.microstock_search_edit.textChanged.connect(self.on_search_changed)
        self.parent.microstock_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent.microstock_table.customContextMenuRequested.connect(self.show_context_menu)

        return tab

    def load_platforms(self):
        """Reload all platforms from database into the table."""
        self.parent.microstock_table.setRowCount(0)
        try:
            platforms = self.db_manager.get_all_microstock_platforms()
            self.parent.microstock_table.setRowCount(len(platforms))
            for row_idx, p in enumerate(platforms):
                name_item = QTableWidgetItem(p["platform_name"])
                name_item.setData(Qt.UserRole, p["id"])
                self.parent.microstock_table.setItem(row_idx, 0, name_item)
                self.parent.microstock_table.setItem(row_idx, 1, QTableWidgetItem(p["platform_url"] or ""))
                self.parent.microstock_table.setItem(row_idx, 2, QTableWidgetItem(p["platform_description"] or ""))
                self.parent.microstock_table.setItem(row_idx, 3, QTableWidgetItem(p["platform_note"] or ""))
                self.parent.microstock_table.setItem(row_idx, 4, QTableWidgetItem(str(p["file_count"])))
        except Exception as e:
            print(f"[Microstock Prefs] Error loading platforms: {e}")

    def on_search_changed(self):
        search = self.parent.microstock_search_edit.text().strip().lower()
        for row in range(self.parent.microstock_table.rowCount()):
            name_item = self.parent.microstock_table.item(row, 0)
            desc_item = self.parent.microstock_table.item(row, 2)
            name_text = name_item.text().lower() if name_item else ""
            desc_text = desc_item.text().lower() if desc_item else ""
            hidden = search not in name_text and search not in desc_text
            self.parent.microstock_table.setRowHidden(row, hidden)

    def show_context_menu(self, pos):
        index = self.parent.microstock_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self.parent.microstock_table)
        action_edit = QAction(qta.icon("fa6s.pen-to-square"), "Edit Platform", self.parent)
        action_delete = QAction(qta.icon("fa6s.trash"), "Delete Platform", self.parent)

        def do_edit():
            self.parent.microstock_table.selectRow(row)
            self.on_platform_edit()

        def do_delete():
            self.parent.microstock_table.selectRow(row)
            self.on_platform_delete()

        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.exec(self.parent.microstock_table.viewport().mapToGlobal(pos))

    def _get_selected_platform_id(self):
        row = self.parent.microstock_table.currentRow()
        if row < 0:
            return None, None, None, None, None
        name_item = self.parent.microstock_table.item(row, 0)
        if not name_item:
            return None, None, None, None, None
        platform_id = name_item.data(Qt.UserRole)
        name = name_item.text()
        url = self.parent.microstock_table.item(row, 1).text() if self.parent.microstock_table.item(row, 1) else ""
        desc = self.parent.microstock_table.item(row, 2).text() if self.parent.microstock_table.item(row, 2) else ""
        note = self.parent.microstock_table.item(row, 3).text() if self.parent.microstock_table.item(row, 3) else ""
        return platform_id, name, url, desc, note

    def on_platform_add(self):
        dialog = PlatformEditDialog(parent=self.parent)
        if dialog.exec() == QDialog.Accepted:
            name, url, description, note = dialog.get_values()
            try:
                self.db_manager.add_microstock_platform(name, url, description, note)
                self.load_platforms()
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to add platform: {e}")

    def on_platform_edit(self):
        platform_id, name, url, desc, note = self._get_selected_platform_id()
        if platform_id is None:
            QMessageBox.warning(self.parent, "Selection", "Please select a platform to edit.")
            return
        dialog = PlatformEditDialog(name=name, url=url, description=desc, note=note, parent=self.parent)
        if dialog.exec() == QDialog.Accepted:
            new_name, new_url, new_desc, new_note = dialog.get_values()
            try:
                self.db_manager.update_microstock_platform(platform_id, new_name, new_url, new_desc, new_note)
                self.load_platforms()
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to update platform: {e}")

    def on_platform_delete(self):
        platform_id, name, url, desc, note = self._get_selected_platform_id()
        if platform_id is None:
            QMessageBox.warning(self.parent, "Selection", "Please select a platform to delete.")
            return

        # First confirmation
        confirm1 = QMessageBox.warning(
            self.parent, "Delete Platform",
            f"Delete platform <b>{name}</b>?<br><br>"
            "This will remove any microstock status assignments on existing files, "
            "but the files themselves will NOT be deleted.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm1 != QMessageBox.Yes:
            return

        # Second confirmation
        confirm2 = QMessageBox.critical(
            self.parent, "Final Confirmation",
            f"Are you absolutely sure you want to permanently delete <b>{name}</b> "
            "and all its related microstock status assignments?\n\n"
            "Files themselves will remain untouched. This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm2 != QMessageBox.Yes:
            return

        try:
            self.db_manager.delete_microstock_platform(platform_id)
            self.load_platforms()
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to delete platform: {e}")
