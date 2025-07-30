from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QLabel,
    QFormLayout, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QSizePolicy, QHeaderView, QComboBox, QTextEdit, QSpinBox, QSpacerItem, QApplication, QToolTip, QMenu, QMainWindow, QInputDialog
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCursor, QKeySequence, QShortcut, QAction
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import webbrowser
import qtawesome as qta
import sys
import os
import subprocess
from helpers.show_statusbar_helper import show_statusbar_message

class BatchEditDialog(QDialog):
    def __init__(self, batch_number="", note="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Batch")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.batch_number_edit = QLineEdit(batch_number)
        self.note_edit = QLineEdit(note)
        form.addRow("Batch Number:", self.batch_number_edit)
        form.addRow("Note:", self.note_edit)
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_values(self):
        return self.batch_number_edit.text().strip(), self.note_edit.text().strip()

def find_main_window(widget):
    parent = widget
    while parent is not None:
        if isinstance(parent, QMainWindow):
            return parent
        parent = parent.parent()
    return widget.window()

class ClientDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Data")
        self.setMinimumSize(800, 500)
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)
        self._init_clients_tab()
        self._init_details_tab()
        self._init_files_tab()
        self._init_batch_list_tab()

    def _init_clients_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.clients_table = QTableWidget(tab)
        self.clients_table.setColumnCount(6)
        self.clients_table.setHorizontalHeaderLabels([
            "Name", "Contact", "Links", "Status", "Note", "Files"
        ])
        self.clients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setSelectionMode(QTableWidget.SingleSelection)
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.clients_table.cellClicked.connect(self._on_client_row_clicked)
        self.clients_table.cellDoubleClicked.connect(self._on_client_row_double_clicked)
        tab_layout.addWidget(self.clients_table)
        self.tab_widget.addTab(tab, qta.icon("fa6s.users"), "Clients")
        self._load_clients_data()

    def _load_clients_data(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        clients = db_manager.get_all_clients()
        self.clients_table.setRowCount(len(clients))
        self._clients_data = []
        for row_idx, client in enumerate(clients):
            self._clients_data.append(client)
            for col_idx, key in enumerate(["client_name", "contact", "links", "status", "note"]):
                value = client.get(key, "")
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.clients_table.setItem(row_idx, col_idx, item)
            file_count = db_manager.get_file_count_by_client_id(client["id"])
            item = QTableWidgetItem(str(file_count))
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.clients_table.setItem(row_idx, 5, item)

    def _init_details_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.details_layout = QFormLayout()
        tab_layout.addLayout(self.details_layout)
        self.details_widgets = {}
        self.details_editable = {}
        self.details_copy_buttons = {}
        fields = [
            ("Name", "client_name", True),
            ("Contact", "contact", True),
            ("Links", "links", True),
            ("Status", "status", True),
            ("Note", "note", True)
        ]
        for label, key, editable in fields:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            if key == "note":
                w = QTextEdit("")
                row_layout.addWidget(w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            elif key == "links":
                links_widget = QWidget()
                links_layout = QVBoxLayout(links_widget)
                links_layout.setContentsMargins(0, 0, 0, 0)
                entry_row = QHBoxLayout()
                self.link_entry = QLineEdit("")
                self.link_entry.setPlaceholderText("Enter link and press Add")
                self.add_link_btn = QPushButton("Add Link")
                self.add_link_btn.clicked.connect(self._add_link)
                entry_row.addWidget(self.link_entry)
                entry_row.addWidget(self.add_link_btn)
                links_layout.addLayout(entry_row)
                self.links_table = QTableWidget()
                self.links_table.setColumnCount(2)
                self.links_table.setHorizontalHeaderLabels(["Link", "Actions"])
                self.links_table.setEditTriggers(QTableWidget.NoEditTriggers)
                self.links_table.setSelectionBehavior(QTableWidget.SelectRows)
                self.links_table.setSelectionMode(QTableWidget.SingleSelection)
                self.links_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                self.links_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
                links_layout.addWidget(self.links_table)
                row_layout.addWidget(links_widget)
                self.details_widgets[key] = self.links_table
                self.details_editable[key] = True
                self.links_table.cellClicked.connect(self._on_link_table_cell_clicked)
            elif key == "status":
                self.status_combo = QComboBox()
                self.status_combo.addItems(["Active", "Repeat", "Dormant"])
                row_layout.addWidget(self.status_combo)
                self.details_widgets[key] = self.status_combo
                self.details_editable[key] = True
            else:
                w = QLineEdit("")
                row_layout.addWidget(w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            # Only add copy button for client_name, contact, note
            if key not in ("links", "status"):
                copy_btn = QPushButton()
                copy_btn.setIcon(qta.icon("fa6s.copy"))
                copy_btn.setFixedWidth(28)
                copy_btn.setFixedHeight(28)
                copy_btn.setToolTip(f"Copy {label}")
                copy_btn.clicked.connect(lambda _, k=key, btn=copy_btn: self._copy_detail_to_clipboard(k, btn))
                row_layout.addWidget(copy_btn)
                self.details_copy_buttons[key] = copy_btn
            self.details_layout.addRow(label, row_widget)
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_client_details)
        self.add_button = QPushButton("Add Client")
        self.add_button.clicked.connect(self._add_client_mode)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.add_button)
        tab_layout.addLayout(button_layout)
        self.tab_widget.addTab(tab, qta.icon("fa6s.id-card"), "Details")
        self._selected_client_index = None
        self._add_mode = False
        self.save_button.setEnabled(False)
        self._editing_link_index = None

    def _copy_detail_to_clipboard(self, key, btn=None):
        widget = self.details_widgets.get(key)
        value = ""
        if key == "note" and isinstance(widget, QTextEdit):
            value = widget.toPlainText()
        elif isinstance(widget, QLineEdit):
            value = widget.text()
        else:
            value = ""
        clipboard = self.parent().clipboard() if self.parent() and hasattr(self.parent(), "clipboard") else None
        if clipboard is None:
            clipboard = QApplication.clipboard()
        clipboard.setText(value)
        if btn is not None:
            global_pos = btn.mapToGlobal(btn.rect().bottomRight())
            QToolTip.showText(global_pos, "Copied!", btn)

    def _init_files_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.files_summary_widget = QWidget()
        self.files_summary_layout = QVBoxLayout(self.files_summary_widget)
        self.files_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.files_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.files_summary_widget)
        self.files_search_row = QHBoxLayout()
        self.files_search_edit = QLineEdit()
        self.files_search_edit.setPlaceholderText("Search by status, name, date, price, note...")
        self.files_search_edit.setMinimumHeight(32)
        self.files_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.files_search_row.addWidget(self.files_search_edit)
        self.files_sort_combo = QComboBox()
        self.files_sort_combo.addItems(["File Name", "Date", "Price", "Status", "Note", "Batch"])
        self.files_sort_order_combo = QComboBox()
        self.files_sort_order_combo.addItems(["Ascending", "Descending"])
        self.files_search_row.addWidget(QLabel("Sort by:"))
        self.files_search_row.addWidget(self.files_sort_combo)
        self.files_search_row.addWidget(self.files_sort_order_combo)
        # Batch filter combobox
        self.files_batch_filter_combo = QComboBox()
        self.files_batch_filter_combo.setMinimumWidth(120)
        self.files_batch_filter_combo.addItem("All Batches")
        self.files_search_row.addWidget(QLabel("Batch:"))
        self.files_search_row.addWidget(self.files_batch_filter_combo)
        tab_layout.addLayout(self.files_search_row)
        self.files_table = QTableWidget(tab)
        self.files_table.setColumnCount(6)
        self.files_table.setHorizontalHeaderLabels([
            "File Name", "Date", "Price", "Status", "Note", "Batch"
        ])
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.files_table)
        pagination_row = QHBoxLayout()
        self.files_prev_btn = QPushButton("Prev")
        self.files_next_btn = QPushButton("Next")
        self.files_page_label = QLabel()
        self.files_page_input = QSpinBox()
        self.files_page_input.setMinimum(1)
        self.files_page_input.setMaximum(1)
        self.files_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.files_prev_btn)
        pagination_row.addWidget(self.files_page_label)
        pagination_row.addWidget(self.files_page_input)
        pagination_row.addWidget(self.files_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        self.tab_widget.addTab(tab, qta.icon("fa6s.folder-open"), "Files")
        self.files_prev_btn.clicked.connect(self._files_prev_page)
        self.files_next_btn.clicked.connect(self._files_next_page)
        self.files_page_input.valueChanged.connect(self._files_goto_page)
        self.files_search_edit.textChanged.connect(self._on_files_search_changed)
        self.files_sort_combo.currentIndexChanged.connect(self._on_files_sort_changed)
        self.files_sort_order_combo.currentIndexChanged.connect(self._on_files_sort_changed)
        self.files_batch_filter_combo.currentIndexChanged.connect(self._on_files_batch_filter_changed)
        self.files_records_all = []
        self.files_records_filtered = []
        self.files_page_size = 20
        self.files_current_page = 1
        self.files_sort_field = "File Name"
        self.files_sort_order = "Descending"
        self._selected_client_name = ""
        self._selected_client_id = None
        self._batch_filter_value = None

        self.files_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_table.customContextMenuRequested.connect(self._show_files_context_menu)
        self._files_shortcut_copy_name = QShortcut(QKeySequence("Ctrl+C"), self.files_table)
        self._files_shortcut_copy_name.activated.connect(self._files_copy_name_shortcut)
        self._files_shortcut_copy_path = QShortcut(QKeySequence("Ctrl+X"), self.files_table)
        self._files_shortcut_copy_path.activated.connect(self._files_copy_path_shortcut)
        self._files_shortcut_open_explorer = QShortcut(QKeySequence("Ctrl+E"), self.files_table)
        self._files_shortcut_open_explorer.activated.connect(self._files_open_explorer_shortcut)
        self.files_table.cellDoubleClicked.connect(self._on_files_row_double_clicked)

    def _init_batch_list_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.batch_table = QTableWidget(tab)
        self.batch_table.setColumnCount(3)
        self.batch_table.setHorizontalHeaderLabels([
            "Batch Number", "Note", "File Count"
        ])
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setSelectionMode(QTableWidget.SingleSelection)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.batch_table)

        batch_btn_row = QHBoxLayout()
        self.batch_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Batch")
        self.batch_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Batch")
        self.batch_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Batch")
        batch_btn_row.addWidget(self.batch_add_btn)
        batch_btn_row.addWidget(self.batch_edit_btn)
        batch_btn_row.addWidget(self.batch_delete_btn)
        batch_btn_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(batch_btn_row)
        self.tab_widget.addTab(tab, qta.icon("fa6s.layer-group"), "Batch List")

        self.batch_add_btn.clicked.connect(self._on_batch_add)
        self.batch_edit_btn.clicked.connect(self._on_batch_edit)
        self.batch_delete_btn.clicked.connect(self._on_batch_delete)
        self.batch_table.cellDoubleClicked.connect(self._on_batch_edit)
        self.batch_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.batch_table.customContextMenuRequested.connect(self._show_batch_context_menu)

    def _show_batch_context_menu(self, pos):
        index = self.batch_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu(self.batch_table)
        icon_edit = qta.icon("fa6s.pen-to-square")
        icon_delete = qta.icon("fa6s.trash")
        action_edit = QAction(icon_edit, "Edit Batch", self)
        action_delete = QAction(icon_delete, "Delete Batch", self)
        def do_edit():
            self.batch_table.selectRow(row)
            self._on_batch_edit()
        def do_delete():
            self.batch_table.selectRow(row)
            self._on_batch_delete()
        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.exec(self.batch_table.viewport().mapToGlobal(pos))

    def _load_batch_list_for_client(self, client_id):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        batch_numbers = db_manager.get_batch_numbers_by_client(client_id)
        batch_data = []
        for batch_number in batch_numbers:
            note, _ = db_manager.get_batch_list_note_and_client(batch_number)
            file_count = db_manager.count_file_client_batch_by_batch_number(batch_number)
            batch_data.append((batch_number, note, file_count))
        self.batch_table.setRowCount(len(batch_data))
        for row_idx, (batch_number, note, file_count) in enumerate(batch_data):
            self.batch_table.setItem(row_idx, 0, QTableWidgetItem(str(batch_number)))
            self.batch_table.setItem(row_idx, 1, QTableWidgetItem(str(note)))
            self.batch_table.setItem(row_idx, 2, QTableWidgetItem(str(file_count)))

    def _on_batch_add(self):
        client_id = self._selected_client_id
        if not client_id:
            QMessageBox.warning(self, "No Client Selected", "Please select a client first.")
            return
        dialog = BatchEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            batch_number, note = dialog.get_values()
            if not batch_number:
                QMessageBox.warning(self, "Validation Error", "Batch Number cannot be empty.")
                return
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            config_manager = ConfigManager(str(db_config_path))
            db_manager = DatabaseManager(config_manager, config_manager)
            try:
                db_manager.add_batch_number(batch_number, note, client_id)
                self._load_batch_list_for_client(client_id)
                QMessageBox.information(self, "Success", "Batch added successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _on_batch_edit(self, *args):
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Batch Selected", "Please select a batch to edit.")
            return
        batch_number = self.batch_table.item(row, 0).text()
        note = self.batch_table.item(row, 1).text()
        dialog = BatchEditDialog(batch_number, note, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_batch_number, new_note = dialog.get_values()
            if not new_batch_number:
                QMessageBox.warning(self, "Validation Error", "Batch Number cannot be empty.")
                return
            client_id = self._selected_client_id
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            config_manager = ConfigManager(str(db_config_path))
            db_manager = DatabaseManager(config_manager, config_manager)
            try:
                db_manager.update_batch_number_and_note_and_client(batch_number, new_batch_number, new_note, client_id)
                self._load_batch_list_for_client(client_id)
                QMessageBox.information(self, "Success", "Batch updated successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _on_batch_delete(self):
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Batch Selected", "Please select a batch to delete.")
            return
        batch_number = self.batch_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Delete Batch", f"Are you sure you want to delete batch '{batch_number}'?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        try:
            db_manager.delete_batch_and_file_client_batch(batch_number)
            self._load_batch_list_for_client(self._selected_client_id)
            QMessageBox.information(self, "Success", "Batch deleted successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _fill_details_form(self, row):
        if 0 <= row < len(self._clients_data):
            client = self._clients_data[row]
            self._selected_client_index = row
            self._add_mode = False
            for key, widget in self.details_widgets.items():
                if key == "note":
                    widget.setPlainText(str(client.get(key, "")))
                elif key == "links":
                    self._populate_links_table(str(client.get("links", "")))
                elif key == "status":
                    status_val = str(client.get("status", "Active"))
                    idx = self.status_combo.findText(status_val)
                    if idx != -1:
                        self.status_combo.setCurrentIndex(idx)
                    else:
                        self.status_combo.setCurrentIndex(0)
                else:
                    widget.setText(str(client.get(key, "")))
            self.save_button.setEnabled(True)
            self._selected_client_name = client.get("client_name", "")
            self._selected_client_id = client.get("id", None)
            self._load_files_for_client(client["id"])
            self._load_batch_list_for_client(client["id"])

    def _populate_links_table(self, links_str):
        self.links_table.setRowCount(0)
        links = [l for l in links_str.split("|") if l.strip()]
        for idx, link in enumerate(links):
            self.links_table.insertRow(idx)
            link_item = QTableWidgetItem(link)
            self.links_table.setItem(idx, 0, link_item)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            open_btn = QPushButton()
            open_btn.setIcon(qta.icon("fa6s.up-right-from-square"))
            open_btn.setToolTip("Open link")
            open_btn.clicked.connect(lambda _, url=link: webbrowser.open(url))
            edit_btn = QPushButton()
            edit_btn.setIcon(qta.icon("fa6s.pen-to-square"))
            edit_btn.setToolTip("Edit link")
            edit_btn.clicked.connect(lambda _, idx=idx: self._edit_link(idx))
            delete_btn = QPushButton()
            delete_btn.setIcon(qta.icon("fa6s.trash"))
            delete_btn.setToolTip("Delete link")
            delete_btn.clicked.connect(lambda _, idx=idx: self._delete_link(idx))
            actions_layout.addWidget(open_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.links_table.setCellWidget(idx, 1, actions_widget)

    def _get_links_list(self):
        links = []
        for i in range(self.links_table.rowCount()):
            item = self.links_table.item(i, 0)
            if item:
                links.append(item.text())
        return links

    def _add_link(self):
        link_text = self.link_entry.text().strip()
        if not link_text:
            QMessageBox.warning(self, "Validation Error", "Link cannot be empty.")
            return
        if self._editing_link_index is not None:
            item = self.links_table.item(self._editing_link_index, 0)
            if item:
                item.setText(link_text)
            self._editing_link_index = None
            self.add_link_btn.setText("Add Link")
            self.link_entry.clear()
            return
        for i in range(self.links_table.rowCount()):
            item = self.links_table.item(i, 0)
            if item and item.text() == link_text:
                QMessageBox.warning(self, "Duplicate Link", "Link already exists.")
                return
        row = self.links_table.rowCount()
        self.links_table.insertRow(row)
        link_item = QTableWidgetItem(link_text)
        self.links_table.setItem(row, 0, link_item)
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        open_btn = QPushButton()
        open_btn.setIcon(qta.icon("fa6s.up-right-from-square"))
        open_btn.setToolTip("Open link")
        open_btn.clicked.connect(lambda _, url=link_text: webbrowser.open(url))
        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa6s.pen-to-square"))
        edit_btn.setToolTip("Edit link")
        edit_btn.clicked.connect(lambda _, idx=row: self._edit_link(idx))
        delete_btn = QPushButton()
        delete_btn.setIcon(qta.icon("fa6s.trash"))
        delete_btn.setToolTip("Delete link")
        delete_btn.clicked.connect(lambda _, idx=row: self._delete_link(idx))
        actions_layout.addWidget(open_btn)
        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(delete_btn)
        self.links_table.setCellWidget(row, 1, actions_widget)
        self.link_entry.clear()

    def _edit_link(self, idx):
        item = self.links_table.item(idx, 0)
        if item:
            self.link_entry.setText(item.text())
            self._editing_link_index = idx
            self.add_link_btn.setText("Update Link")

    def _delete_link(self, idx):
        reply = QMessageBox.question(self, "Delete Link", "Are you sure you want to delete this link?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.links_table.removeRow(idx)
            self._editing_link_index = None
            self.add_link_btn.setText("Add Link")
            self.link_entry.clear()

    def _on_link_table_cell_clicked(self, row, col):
        pass

    def _load_files_for_client(self, client_id):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        files = db_manager.get_files_by_client_id(client_id)
        for f in files:
            batch_number = db_manager.get_batch_number_for_file_client(f.get("file_id", None) or f.get("id", None), client_id)
            f["batch"] = batch_number
        self.files_records_all = files
        self.files_current_page = 1
        self._selected_client_id = client_id
        self._refresh_batch_filter_combo()
        self._update_files_table()

    def _refresh_batch_filter_combo(self):
        self.files_batch_filter_combo.blockSignals(True)
        self.files_batch_filter_combo.clear()
        self.files_batch_filter_combo.addItem("All Batches")
        batch_set = set()
        for f in self.files_records_all:
            batch = f.get("batch", "")
            if batch:
                batch_set.add(batch)
        batch_list = sorted(batch_set)
        for batch in batch_list:
            self.files_batch_filter_combo.addItem(batch)
        self.files_batch_filter_combo.setCurrentIndex(0)
        self._batch_filter_value = None
        self.files_batch_filter_combo.blockSignals(False)

    def _on_files_batch_filter_changed(self, idx):
        if idx == 0:
            self._batch_filter_value = None
        else:
            self._batch_filter_value = self.files_batch_filter_combo.currentText()
        self.files_current_page = 1
        self._update_files_table()

    def _on_files_search_changed(self):
        self.files_current_page = 1
        self._update_files_table()

    def _on_files_sort_changed(self):
        self.files_current_page = 1
        self.files_sort_field = self.files_sort_combo.currentText()
        self.files_sort_order = self.files_sort_order_combo.currentText()
        self._update_files_table()

    def _files_prev_page(self):
        if self.files_current_page > 1:
            self.files_current_page -= 1
            self._update_files_table()

    def _files_next_page(self):
        total_rows = len(self.files_records_filtered)
        total_pages = max(1, (total_rows + self.files_page_size - 1) // self.files_page_size)
        if self.files_current_page < total_pages:
            self.files_current_page += 1
            self._update_files_table()

    def _files_goto_page(self, value):
        total_rows = len(self.files_records_filtered)
        total_pages = max(1, (total_rows + self.files_page_size - 1) // self.files_page_size)
        if 1 <= value <= total_pages:
            self.files_current_page = value
            self._update_files_table()

    def _get_global_file_index(self, row_in_page):
        start_idx = (self.files_current_page - 1) * self.files_page_size
        return start_idx + row_in_page

    def _update_files_table(self):
        search_text = self.files_search_edit.text().strip().lower()
        batch_filter = self._batch_filter_value
        if search_text or batch_filter:
            self.files_records_filtered = []
            for f in self.files_records_all:
                match_search = (
                    not search_text or
                    search_text in str(f.get("name", "")).lower() or
                    search_text in str(f.get("date", "")).lower() or
                    search_text in str(f.get("price", "")).lower() or
                    search_text in str(f.get("status", "")).lower() or
                    search_text in str(f.get("note", "")).lower() or
                    search_text in str(f.get("batch", "")).lower()
                )
                match_batch = (not batch_filter or f.get("batch", "") == batch_filter)
                if match_search and match_batch:
                    self.files_records_filtered.append(f)
        else:
            self.files_records_filtered = list(self.files_records_all)
        sort_field = self.files_sort_field
        sort_order = self.files_sort_order
        sort_map = {
            "File Name": "name",
            "Date": "date",
            "Price": "price",
            "Status": "status",
            "Note": "note",
            "Batch": "batch"
        }
        key = sort_map.get(sort_field, "name")
        reverse = sort_order == "Descending"
        try:
            self.files_records_filtered.sort(key=lambda x: (float(x[key]) if key == "price" and x[key] not in ["", None] else str(x[key]).lower()), reverse=reverse)
        except Exception:
            self.files_records_filtered.sort(key=lambda x: str(x[key]).lower(), reverse=reverse)
        total_rows = len(self.files_records_filtered)
        total_pages = max(1, (total_rows + self.files_page_size - 1) // self.files_page_size)
        self.files_page_input.blockSignals(True)
        self.files_page_input.setMaximum(total_pages)
        self.files_page_input.setValue(self.files_current_page)
        self.files_page_input.blockSignals(False)
        self.files_page_label.setText(f"Page {self.files_current_page} / {total_pages}")
        start_idx = (self.files_current_page - 1) * self.files_page_size
        end_idx = start_idx + self.files_page_size
        page_records = self.files_records_filtered[start_idx:end_idx]
        self.files_table.setRowCount(len(page_records))
        total_price = 0
        status_counts = {}
        currency = ""
        for row_idx, file in enumerate(page_records):
            file_name = file.get("name", "")
            file_date = file.get("date", "")
            price = file.get("price", "")
            currency = file.get("currency", "") if not currency else currency
            note = file.get("note", "")
            status = file.get("status", "")
            batch = file.get("batch", "")
            try:
                price_float = float(price)
                if price_float.is_integer():
                    price_str = f"{int(price_float):,}".replace(",", ".")
                else:
                    price_str = f"{price_float:,.2f}".replace(",", ".")
            except Exception:
                price_str = str(price)
            price_display = f"{currency} {price_str}" if currency else price_str
            self.files_table.setItem(row_idx, 0, QTableWidgetItem(str(file_name)))
            self.files_table.setItem(row_idx, 1, QTableWidgetItem(str(file_date)))
            self.files_table.setItem(row_idx, 2, QTableWidgetItem(price_display))
            self.files_table.setItem(row_idx, 3, QTableWidgetItem(str(status)))
            self.files_table.setItem(row_idx, 4, QTableWidgetItem(str(note)))
            self.files_table.setItem(row_idx, 5, QTableWidgetItem(str(batch)))
            try:
                total_price += float(price)
            except Exception:
                pass
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        while self.files_summary_layout.count():
            item = self.files_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        client_name = self._selected_client_name if hasattr(self, "_selected_client_name") else ""
        if client_name:
            client_label = QLabel(f"Client: {client_name}")
            client_label.setStyleSheet("font-size:13px; font-weight:bold; margin-bottom:2px;")
            self.files_summary_layout.addWidget(client_label)
        summary_label = QLabel(f"Total Files: {total_rows}")
        summary_label.setStyleSheet("font-size:12px; font-weight:bold; margin-bottom:2px;")
        self.files_summary_layout.addWidget(summary_label)
        try:
            total_price_str = f"{int(total_price):,}".replace(",", ".") if float(total_price).is_integer() else f"{total_price:,.2f}".replace(",", ".")
        except Exception:
            total_price_str = str(total_price)
        total_price_display = f"{currency} {total_price_str}" if currency else total_price_str
        price_label = QLabel(f"Total Price: {total_price_display}")
        price_label.setStyleSheet("font-size:12px; font-weight:bold; margin-bottom:2px;")
        self.files_summary_layout.addWidget(price_label)
        for status, count in status_counts.items():
            status_label = QLabel(f"{status}: {count}")
            status_label.setStyleSheet("font-size:12px; margin-bottom:2px;")
            self.files_summary_layout.addWidget(status_label)

    def _show_files_context_menu(self, pos):
        index = self.files_table.indexAt(pos)
        if not index.isValid():
            return
        row_in_page = index.row()
        global_idx = self._get_global_file_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.files_records_filtered):
            return
        record = self.files_records_filtered[global_idx]
        file_name = record.get("name", "")
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = ""
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        if file_id:
            db_manager.connect(write=False)
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT path FROM files WHERE id = ?", (file_id,))
            row_db = cursor.fetchone()
            db_manager.close()
            if row_db and row_db[0]:
                file_path = row_db[0]
        menu = QMenu(self.files_table)
        icon_copy_name = qta.icon("fa6s.copy")
        icon_copy_path = qta.icon("fa6s.folder-open")
        icon_open_explorer = qta.icon("fa6s.folder-tree")
        action_copy_name = QAction(icon_copy_name, "Copy Name\tCtrl+C", self)
        action_copy_path = QAction(icon_copy_path, "Copy Path\tCtrl+X", self)
        action_open_explorer = QAction(icon_open_explorer, "Open in Explorer\tCtrl+E", self)
        def do_copy_name():
            QApplication.clipboard().setText(str(file_name))
            QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")
        def do_copy_path():
            QApplication.clipboard().setText(str(file_path))
            QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")
        def do_open_explorer():
            path = file_path
            if not path:
                return
            if sys.platform == "win32":
                if os.path.isfile(path):
                    subprocess.Popen(f'explorer /select,"{path}"')
                elif os.path.isdir(path):
                    subprocess.Popen(f'explorer "{path}"')
                else:
                    parent_dir = os.path.dirname(path)
                    if os.path.exists(parent_dir):
                        subprocess.Popen(f'explorer "{parent_dir}"')
            else:
                subprocess.Popen(["xdg-open", path if os.path.exists(path) else os.path.dirname(path)])
            QToolTip.showText(QCursor.pos(), f"Opened: {path}")
        action_copy_name.triggered.connect(do_copy_name)
        action_copy_path.triggered.connect(do_copy_path)
        action_open_explorer.triggered.connect(do_open_explorer)
        menu.addAction(action_copy_name)
        menu.addAction(action_copy_path)
        menu.addAction(action_open_explorer)
        menu.exec(self.files_table.viewport().mapToGlobal(pos))

    def _files_copy_name_shortcut(self):
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self._get_global_file_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.files_records_filtered):
            return
        record = self.files_records_filtered[global_idx]
        file_name = record.get("name", "")
        QApplication.clipboard().setText(str(file_name))
        QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")

    def _files_copy_path_shortcut(self):
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self._get_global_file_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.files_records_filtered):
            return
        record = self.files_records_filtered[global_idx]
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = ""
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        if file_id:
            db_manager.connect(write=False)
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT path FROM files WHERE id = ?", (file_id,))
            row_db = cursor.fetchone()
            db_manager.close()
            if row_db and row_db[0]:
                file_path = row_db[0]
        QApplication.clipboard().setText(str(file_path))
        QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")

    def _files_open_explorer_shortcut(self):
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self._get_global_file_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.files_records_filtered):
            return
        record = self.files_records_filtered[global_idx]
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = ""
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        if file_id:
            db_manager.connect(write=False)
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT path FROM files WHERE id = ?", (file_id,))
            row_db = cursor.fetchone()
            db_manager.close()
            if row_db and row_db[0]:
                file_path = row_db[0]
        if not file_path:
            return
        if sys.platform == "win32":
            if os.path.isfile(file_path):
                subprocess.Popen(f'explorer /select,"{file_path}"')
            elif os.path.isdir(file_path):
                subprocess.Popen(f'explorer "{file_path}"')
            else:
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    subprocess.Popen(f'explorer "{parent_dir}"')
        else:
            subprocess.Popen(["xdg-open", file_path if os.path.exists(file_path) else os.path.dirname(file_path)])
        QToolTip.showText(QCursor.pos(), f"Opened: {file_path}")

    def _on_files_row_double_clicked(self, row_in_page, col):
        global_idx = self._get_global_file_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.files_records_filtered):
            return
        record = self.files_records_filtered[global_idx]
        file_name = record.get("name", "")
        QApplication.clipboard().setText(str(file_name))
        show_statusbar_message(self, f"Copied: {file_name}")
        main_window = find_main_window(self)
        central_widget = getattr(main_window, "central_widget", None)
        if central_widget and hasattr(central_widget, "paste_to_search"):
            central_widget.paste_to_search()
        self.accept()

    def _on_client_row_clicked(self, row, col):
        self._fill_details_form(row)

    def _on_client_row_double_clicked(self, row, col):
        self._fill_details_form(row)
        self.tab_widget.setCurrentIndex(1)
        client = self._clients_data[row]
        self._load_files_for_client(client["id"])
        self._load_batch_list_for_client(client["id"])
        self.tab_widget.setCurrentIndex(2)

    def _add_client_mode(self):
        self._selected_client_index = None
        self._add_mode = True
        for key, widget in self.details_widgets.items():
            if key == "note":
                widget.setPlainText("")
            elif key == "links":
                self.links_table.setRowCount(0)
                self.link_entry.clear()
                self._editing_link_index = None
                self.add_link_btn.setText("Add Link")
            elif key == "status":
                self.status_combo.setCurrentIndex(0)
            else:
                widget.setText("")
        self.save_button.setEnabled(True)
        self.tab_widget.setCurrentIndex(1)
        self.files_table.setRowCount(0)
        while self.files_summary_layout.count():
            item = self.files_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.files_records_all = []
        self.files_current_page = 1
        self._update_files_table()
        self.batch_table.setRowCount(0)

    def _save_client_details(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        updated_data = {}
        for key, widget in self.details_widgets.items():
            if key == "note":
                updated_data[key] = widget.toPlainText()
            elif key == "links":
                links = self._get_links_list()
                updated_data[key] = "|".join(links)
            elif key == "status":
                updated_data[key] = self.status_combo.currentText()
            else:
                updated_data[key] = widget.text()
        if not updated_data["client_name"].strip():
            QMessageBox.warning(self, "Validation Error", "Client Name cannot be empty.")
            return
        if self._add_mode:
            clients = db_manager.get_all_clients()
            existing_names = {client["client_name"] for client in clients}
            if updated_data["client_name"] in existing_names:
                QMessageBox.warning(self, "Duplicate Client Name", "Client name already exists. Please choose another name.")
                return
            try:
                db_manager.add_client(
                    client_name=updated_data["client_name"],
                    contact=updated_data["contact"],
                    links=updated_data["links"],
                    status=updated_data["status"],
                    note=updated_data["note"]
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self._load_clients_data()
            self._selected_client_index = None
            self._add_mode = False
            for key, widget in self.details_widgets.items():
                if key == "note":
                    widget.setPlainText("")
                elif key == "links":
                    self.links_table.setRowCount(0)
                    self.link_entry.clear()
                    self._editing_link_index = None
                    self.add_link_btn.setText("Add Link")
                elif key == "status":
                    self.status_combo.setCurrentIndex(0)
                else:
                    widget.setText("")
            self.save_button.setEnabled(False)
            self.tab_widget.setCurrentIndex(0)
            self.files_table.setRowCount(0)
            while self.files_summary_layout.count():
                item = self.files_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.files_records_all = []
            self.files_current_page = 1
            self._update_files_table()
            QMessageBox.information(self, "Success", "Client added successfully.")
        else:
            idx = self._selected_client_index
            if idx is None or idx >= len(self._clients_data):
                QMessageBox.warning(self, "No Client Selected", "Please select a client to update.")
                return
            client = self._clients_data[idx]
            old_id = client["id"]
            try:
                db_manager.update_client(
                    client_id=old_id,
                    client_name=updated_data["client_name"],
                    contact=updated_data["contact"],
                    links=updated_data["links"],
                    status=updated_data["status"],
                    note=updated_data["note"]
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self._load_clients_data()
            self._selected_client_index = None
            self.save_button.setEnabled(False)
            self.files_table.setRowCount(0)
            while self.files_summary_layout.count():
                item = self.files_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.files_records_all = []
            self.files_current_page = 1
            self._update_files_table()
            QMessageBox.information(self, "Success", "Client data updated successfully.")
            self._load_clients_data()
            self._selected_client_index = None
            self.save_button.setEnabled(False)
            self.files_table.setRowCount(0)
            while self.files_summary_layout.count():
                item = self.files_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.files_records_all = []
            self.files_current_page = 1
            self._update_files_table()
            QMessageBox.information(self, "Success", "Client data updated successfully.")

