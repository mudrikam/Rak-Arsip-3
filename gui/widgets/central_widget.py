from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QSpacerItem, QSizePolicy, QComboBox,
    QMenu, QApplication, QMessageBox, QDialog, QVBoxLayout as QVBoxLayout2, QRadioButton, QButtonGroup, QDialogButtonBox
)
from PySide6.QtGui import QColor, QAction, QFontMetrics, QCursor, QKeySequence, QShortcut
from PySide6.QtCore import Signal, Qt, QTimer
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import subprocess
import sys
import os
import shutil
from gui.dialogs.short_dialog import SortDialog
from helpers.show_statusbar_helper import show_statusbar_message

class CentralWidget(QWidget):
    row_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = parent.config_manager
        self.status_config = self.config_manager.get("status_options")
        self.status_options = list(self.status_config.keys())
        self.selected_row_data = None
        self.sort_field = "date"
        self.sort_order = "desc"
        self.sort_status_value = None
        self._main_window = parent if isinstance(parent, QWidget) else None
        self._selected_row_index = None

        if hasattr(parent, 'main_action_dock') and hasattr(parent.main_action_dock, 'db_manager'):
            self.db_manager = parent.main_action_dock.db_manager
        else:
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            db_config_manager = ConfigManager(str(db_config_path))
            self.db_manager = DatabaseManager(db_config_manager, self.config_manager)
        
        self.db_manager.data_changed.connect(self.auto_refresh_table)
        
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        search_section = QHBoxLayout()
        search_icon_label = QLabel()
        search_icon_label.setPixmap(qta.icon("fa6s.magnifying-glass", color="#666").pixmap(16, 16))
        search_section.addWidget(search_icon_label)
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search projects...")
        self.search_edit.setMinimumHeight(32)
        self.search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_section.addWidget(self.search_edit, 1)
        self.paste_search_btn = QPushButton()
        self.paste_search_btn.setIcon(qta.icon("fa6s.paste"))
        self.paste_search_btn.setMinimumHeight(32)
        self.paste_search_btn.setMaximumHeight(32)
        self.paste_search_btn.setFixedWidth(50)
        self.paste_search_btn.setToolTip("Paste from clipboard")
        self.paste_search_btn.clicked.connect(self.paste_to_search)
        search_section.addWidget(self.paste_search_btn)
        top_row.addLayout(search_section, 1)
        self.clear_search_btn = QPushButton("Clear", self)
        self.clear_search_btn.setIcon(qta.icon("fa6s.xmark"))
        self.clear_search_btn.setMinimumHeight(32)
        self.clear_search_btn.setToolTip("Clear search field")
        self.clear_search_btn.clicked.connect(lambda: self.search_edit.clear())
        top_row.addWidget(self.clear_search_btn)
        self.refresh_btn = QPushButton("Refresh", self)
        self.refresh_btn.setIcon(qta.icon("fa6s.arrows-rotate"))
        self.refresh_btn.setMinimumHeight(32)
        self.refresh_btn.setToolTip("Reload project table")
        top_row.addWidget(self.refresh_btn)
        self.sort_btn = QPushButton("Sort By", self)
        self.sort_btn.setIcon(qta.icon("fa6s.arrow-down-wide-short"))
        self.sort_btn.setMinimumHeight(32)
        self.sort_btn.setToolTip("Sort table data")
        self.sort_btn.clicked.connect(self.show_sort_dialog)
        top_row.addWidget(self.sort_btn)
        top_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(top_row)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        date_header = QTableWidgetItem("Date")
        date_header.setIcon(qta.icon("fa6s.calendar"))
        name_header = QTableWidgetItem("Name")
        name_header.setIcon(qta.icon("fa6s.file"))
        root_header = QTableWidgetItem("Root")
        root_header.setIcon(qta.icon("fa6s.folder"))
        path_header = QTableWidgetItem("Path")
        path_header.setIcon(qta.icon("fa6s.folder-tree"))
        status_header = QTableWidgetItem("Status")
        status_header.setIcon(qta.icon("fa6s.circle-info"))
        self.table.setHorizontalHeaderItem(0, date_header)
        self.table.setHorizontalHeaderItem(1, name_header)
        self.table.setHorizontalHeaderItem(2, root_header)
        self.table.setHorizontalHeaderItem(3, path_header)
        self.table.setHorizontalHeaderItem(4, status_header)
        self._all_data = []
        self.page_size = 20
        self.current_page = 1
        self.filtered_data = []

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(0, 100)
        header.resizeSection(1, 200)
        header.resizeSection(2, 100)
        header.resizeSection(4, 120)
        layout.addWidget(self.table)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        self.table.setMouseTracking(True)
        def table_mouseMoveEvent(event):
            # Disable hover selection: only change cursor, do not change selection
            index = self.table.indexAt(event.pos())
            if index.isValid():
                self.table.viewport().setCursor(Qt.PointingHandCursor)
            else:
                self.table.viewport().setCursor(Qt.ArrowCursor)
            return QTableWidget.mouseMoveEvent(self.table, event)
        self.table.mouseMoveEvent = table_mouseMoveEvent

        pagination_row = QHBoxLayout()
        pagination_icon = QLabel()
        pagination_icon.setPixmap(qta.icon("fa6s.bars", color="#666").pixmap(16, 16))
        pagination_row.addWidget(pagination_icon)
        self.prev_btn = QPushButton("Prev", self)
        self.prev_btn.setIcon(qta.icon("fa6s.chevron-left"))
        self.prev_btn.setMinimumHeight(32)
        self.next_btn = QPushButton("Next", self)
        self.next_btn.setIcon(qta.icon("fa6s.chevron-right"))
        self.next_btn.setMinimumHeight(32)
        self.page_label = QLabel(self)
        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addWidget(self.next_btn)
        stats_icon = QLabel()
        stats_icon.setPixmap(qta.icon("fa6s.chart-simple", color="#666").pixmap(16, 16))
        pagination_row.addWidget(stats_icon)
        self.stats_label = QLabel(self)
        self.stats_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 5px;")
        pagination_row.addWidget(self.stats_label)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(pagination_row)

        self.setLayout(layout)

        self.refresh_btn.clicked.connect(self.refresh_table)
        self.search_edit.textChanged.connect(self.apply_search)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        copy_name_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        copy_name_shortcut.activated.connect(self.copy_name)
        copy_path_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        copy_path_shortcut.activated.connect(self.copy_path)
        open_explorer_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        open_explorer_shortcut.activated.connect(self.open_explorer)

        self.load_data_from_database()

    def paste_to_search(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.search_edit.setText(text)
            show_statusbar_message(self, f"Pasted to search: {text}")

    def auto_refresh_table(self):
        self.load_data_from_database()
        show_statusbar_message(self, "Table auto-refreshed")

    def copy_name(self):
        if self.selected_row_data:
            name = str(self.selected_row_data['name'])
            QApplication.clipboard().setText(name)
            show_statusbar_message(self, f"Name copied: {name}")

    def copy_path(self):
        if self.selected_row_data:
            path = str(self.selected_row_data['path'])
            QApplication.clipboard().setText(path)
            show_statusbar_message(self, f"Path copied: {path}")

    def open_explorer(self):
        if self.selected_row_data:
            path = str(self.selected_row_data['path'])
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
            show_statusbar_message(self, f"Opened in explorer: {path}")

    def _on_table_double_click(self, row, column):
        item = self.table.item(row, 0)
        if item:
            row_data = item.data(256)
            if row_data:
                self.selected_row_data = row_data
                self._selected_row_index = row
                self.open_explorer()
                show_statusbar_message(self, f"Double-clicked: Opened {row_data['path']}")

    def _on_table_cell_clicked(self, row, column):
        self.table.selectRow(row)
        item = self.table.item(row, 0)
        if item:
            row_data = item.data(256)
            if row_data:
                self.selected_row_data = row_data
                self._selected_row_index = row
                show_statusbar_message(self, f"Selected row: {row_data['name']}")

    def load_data_from_database(self):
        try:
            self.db_manager.connect()
            rows = self.db_manager.get_all_files()
            self._all_data = []
            for row in rows:
                self._all_data.append({
                    'id': row['id'],
                    'date': row['date'],
                    'name': row['name'],
                    'root': row['root'],
                    'path': row['path'],
                    'status': row['status_name'],
                    'status_id': row['status_id'],
                    'category': row['category_name'],
                    'subcategory': row['subcategory_name']
                })
            self.filtered_data = self._all_data.copy()
            self.current_page = 1
            self.update_table()
            show_statusbar_message(self, "Loaded data from database")
        except Exception as e:
            print(f"Error loading data from database: {e}")
            self._all_data = []
            self.filtered_data = []
            self.update_table()
            show_statusbar_message(self, f"Error loading data: {e}")
        finally:
            self.db_manager.close()

    def refresh_table(self):
        self.load_data_from_database()
        show_statusbar_message(self, "Table refreshed")

    def apply_search(self):
        query = self.search_edit.text().lower()
        if query:
            self.filtered_data = [
                row for row in self._all_data
                if any(query in str(value).lower() for value in row.values() if value)
            ]
            show_statusbar_message(self, f"Search applied: {query}")
        else:
            self.filtered_data = self._all_data.copy()
            show_statusbar_message(self, "Search cleared")
        self.current_page = 1
        self.update_table()

    def _truncate_path_by_width(self, path, column_width):
        if not path:
            return ""
        font_metrics = QFontMetrics(self.table.font())
        ellipsis = "..."
        ellipsis_width = font_metrics.horizontalAdvance(ellipsis)
        available_width = column_width - 10
        if font_metrics.horizontalAdvance(path) <= available_width:
            return path
        if available_width <= ellipsis_width:
            return ellipsis
        available_for_text = available_width - ellipsis_width
        for i in range(1, len(path)):
            truncated = path[:i]
            if font_metrics.horizontalAdvance(truncated) <= available_for_text:
                continue
            else:
                if i > 1:
                    return path[:i-1] + ellipsis
                else:
                    return ellipsis
        return path

    def update_table(self):
        total_rows = len(self.filtered_data)
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, total_pages))
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        page_data = self.filtered_data[start:end]
        self.table.setRowCount(len(page_data))
        path_column_width = self.table.columnWidth(3)
        for row_idx, row_data in enumerate(page_data):
            date_item = QTableWidgetItem(row_data['date'])
            date_item.setData(256, row_data)
            self.table.setItem(row_idx, 0, date_item)
            name_item = QTableWidgetItem(row_data['name'])
            self.table.setItem(row_idx, 1, name_item)
            root_item = QTableWidgetItem(row_data['root'])
            self.table.setItem(row_idx, 2, root_item)
            truncated_path = self._truncate_path_by_width(row_data['path'], path_column_width)
            path_item = QTableWidgetItem(truncated_path)
            path_item.setToolTip(row_data['path'])
            self.table.setItem(row_idx, 3, path_item)
            combo = QComboBox(self.table)
            combo.addItems(self.status_options)
            combo.setCurrentText(row_data['status'])
            self._set_status_text_color(combo, row_data['status'])
            combo.currentTextChanged.connect(lambda val, row=row_idx: self._on_status_changed(row, val))
            self.table.setCellWidget(row_idx, 4, combo)
        self.page_label.setText(f"Page {self.current_page} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)
        self.update_stats_label()
        # Restore selection if possible
        if self._selected_row_index is not None and 0 <= self._selected_row_index < self.table.rowCount():
            self.table.selectRow(self._selected_row_index)

    def update_stats_label(self):
        total_records = len(self._all_data)
        last_date = "-"
        if self._all_data:
            last_date = self._all_data[0]['date']
        if self.search_edit.text().strip():
            found_records = len(self.filtered_data)
            self.stats_label.setText(f"Total: {total_records} | Last: {last_date} | Found: {found_records} Records")
        else:
            self.stats_label.setText(f"Total: {total_records} | Last: {last_date}")

    def on_row_selected(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            date_item = self.table.item(current_row, 0)
            if date_item:
                row_data = date_item.data(256)
                if row_data:
                    self.selected_row_data = row_data
                    self._selected_row_index = current_row
                    self.row_selected.emit(row_data)

    def _set_status_text_color(self, combo, status):
        if status in self.status_config:
            config = self.status_config[status]
            color = config.get("color", "")
            font_weight = config.get("font_weight", "normal")
            combo.setStyleSheet(f"color: {color}; font-weight: {font_weight};")
        else:
            combo.setStyleSheet("")

    def _on_status_changed(self, row, value):
        global_row = (self.current_page - 1) * self.page_size + row
        if 0 <= global_row < len(self.filtered_data):
            row_data = self.filtered_data[global_row]
            old_status = row_data['status']
            row_data['status'] = value
            try:
                self.db_manager.connect()
                status_id = self.db_manager.get_status_id(value)
                if status_id:
                    self.db_manager.update_file_status(row_data['id'], status_id)
                    row_data['status_id'] = status_id
                    for data_row in self._all_data:
                        if data_row['id'] == row_data['id']:
                            data_row['status'] = value
                            data_row['status_id'] = status_id
                            break
                    combo = self.table.cellWidget(row, 4)
                    if combo:
                        self._set_status_text_color(combo, value)
                    self.load_data_from_database()
            except Exception as e:
                print(f"Error updating status: {e}")
                row_data['status'] = old_status
                combo = self.table.cellWidget(row, 4)
                if combo:
                    combo.setCurrentText(old_status)
            finally:
                self.db_manager.close()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table()

    def next_page(self):
        total_rows = len(self.filtered_data)
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self.update_table()

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        row_data = item.data(256)
        if not row_data:
            return

        menu = QMenu(self.table)
        icon_copy_name = qta.icon("fa6s.copy")
        icon_copy_path = qta.icon("fa6s.folder-open")
        icon_open_explorer = qta.icon("fa6s.folder-tree")
        icon_delete = qta.icon("fa6s.trash")
        action_copy_name = QAction(icon_copy_name, "Copy Name\tCtrl+C", self)
        action_copy_path = QAction(icon_copy_path, "Copy Path\tCtrl+X", self)
        action_open_explorer = QAction(icon_open_explorer, "Open in Explorer\tCtrl+E", self)
        action_delete = QAction(icon_delete, "Delete Record", self)

        def do_copy_name():
            QApplication.clipboard().setText(str(row_data['name']))
            show_statusbar_message(self, f"Name copied: {row_data['name']}")

        def do_copy_path():
            QApplication.clipboard().setText(str(row_data['path']))
            show_statusbar_message(self, f"Path copied: {row_data['path']}")

        def do_open_explorer():
            path = str(row_data['path'])
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
            show_statusbar_message(self, f"Opened in explorer: {path}")

        def do_delete_record():
            confirm1 = QMessageBox.question(
                self,
                "Delete Record",
                "Delete this record?\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm1 == QMessageBox.Yes:
                confirm2 = QMessageBox.question(
                    self,
                    "Are you sure?",
                    "Are you sure you want to permanently delete this record and its project folder?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm2 == QMessageBox.Yes:
                    try:
                        self.db_manager.connect()
                        self.db_manager.delete_file(row_data['id'])
                        project_path = str(row_data['path'])
                        if os.path.isdir(project_path):
                            try:
                                shutil.rmtree(project_path)
                            except Exception as e:
                                print(f"Error deleting project folder: {e}")
                        self.load_data_from_database()
                        QMessageBox.information(self, "Success", "Record and project folder deleted.")
                        show_statusbar_message(self, f"Deleted record and folder: {project_path}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to delete record: {e}")
                        show_statusbar_message(self, f"Failed to delete record: {e}")
                    finally:
                        self.db_manager.close()

        action_copy_name.triggered.connect(do_copy_name)
        action_copy_path.triggered.connect(do_copy_path)
        action_open_explorer.triggered.connect(do_open_explorer)
        action_delete.triggered.connect(do_delete_record)
        menu.addAction(action_copy_name)
        menu.addAction(action_copy_path)
        menu.addAction(action_open_explorer)
        menu.addSeparator()
        menu.addAction(action_delete)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_sort_dialog(self):
        dlg = SortDialog(self.status_options, self)
        if dlg.exec() == QDialog.Accepted:
            field, order, status_value = dlg.get_sort_option(self.status_options)
            self.sort_field = field
            self.sort_order = order
            self.sort_status_value = status_value
            self.apply_sort()
            show_statusbar_message(self, f"Sort applied: {field} {order} {status_value if status_value else ''}")

    def apply_sort(self):
        if self.sort_field == "status" and self.sort_status_value:
            self.filtered_data = [
                row for row in self._all_data
                if row.get("status") == self.sort_status_value
            ]
            show_statusbar_message(self, f"Filtered by status: {self.sort_status_value}")
        else:
            self.filtered_data = self._all_data.copy()
        self.filtered_data = SortDialog.sort_data(
            self.filtered_data,
            self.sort_field,
            self.sort_order,
            self.sort_status_value
        )
        self.current_page = 1
        self.update_table()
        show_statusbar_message(self, f"Sorted by {self.sort_field} ({self.sort_order})")