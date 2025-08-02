from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QSpacerItem, QSizePolicy, QComboBox,
    QMenu, QApplication, QMessageBox, QDialog, QVBoxLayout as QVBoxLayout2, QRadioButton, QButtonGroup, QDialogButtonBox, QStyledItemDelegate, QStyle, QSpinBox, QFormLayout, QToolTip
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
from gui.dialogs.sort_dialog import SortDialog
from helpers.show_statusbar_helper import show_statusbar_message
from helpers.markdown_generator import MarkdownGenerator
from gui.dialogs.edit_record_dialog import EditRecordDialog
from gui.dialogs.assign_price_dialog import AssignPriceDialog
from gui.dialogs.assign_file_url_dialog import AssignFileUrlDialog

class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

class NoHoverDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.state &= ~QStyle.State_MouseOver
        super().paint(painter, option, index)

class CentralWidget(QWidget):
    row_selected = Signal(dict)
    
    def __init__(self, parent=None, db_manager=None):
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
        self.markdown_generator = MarkdownGenerator()
        self._select_after_refresh = None

        self.db_manager = db_manager
        
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
        self.paste_search_btn.setFixedWidth(50)
        self.paste_search_btn.setToolTip("Paste from clipboard")
        self.paste_search_btn.clicked.connect(self.paste_to_search)
        search_section.addWidget(self.paste_search_btn)
        top_row.addLayout(search_section, 1)
        self.clear_search_btn = QPushButton(self)
        self.clear_search_btn.setIcon(qta.icon("fa6s.xmark"))
        self.clear_search_btn.setMinimumHeight(32)
        self.clear_search_btn.setFixedWidth(50)
        self.clear_search_btn.setToolTip("Clear search field")
        self.clear_search_btn.clicked.connect(lambda: self.search_edit.clear())
        top_row.addWidget(self.clear_search_btn)
        self.refresh_btn = QPushButton(self)
        self.refresh_btn.setIcon(qta.icon("fa6s.arrows-rotate"))
        self.refresh_btn.setMinimumHeight(32)
        self.refresh_btn.setFixedWidth(50)
        self.refresh_btn.setToolTip("Reload project table")
        top_row.addWidget(self.refresh_btn)
        self.sort_btn = QPushButton(self)
        self.sort_btn.setIcon(qta.icon("fa6s.arrow-down-wide-short"))
        self.sort_btn.setMinimumHeight(32)
        self.sort_btn.setFixedWidth(50)
        self.sort_btn.setToolTip("Sort table data")
        self.sort_btn.clicked.connect(self.show_sort_dialog)
        top_row.addWidget(self.sort_btn)
        top_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(top_row)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: rgba(13, 125, 201, 0.89); }"
            "QTableWidget::item:focus { outline: none; border: none; }"
            "QTableView::focus { border: none; outline: none; }"
            "QTableWidget::item { outline: none; border: none; }"
        )
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
        self.page_size = 20
        self.current_page = 1
        self.filtered_data = []
        self.total_records = 0
        self.found_records = 0
        self.total_draft = 0

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
        self.table.itemSelectionChanged.connect(self.on_row_selected)

        self.table.setMouseTracking(False)
        self.table.setItemDelegate(NoHoverDelegate(self.table))

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
        self.page_input = QSpinBox(self)
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(1)
        self.page_input.setFixedWidth(60)
        self.page_input.setToolTip("Go to page")
        self.page_input.setValue(1)
        self.page_input.returnPressed = lambda: None
        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addWidget(self.page_input)
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
        self.search_edit.returnPressed.connect(self.apply_search)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self._page_input_timer = QTimer(self)
        self._page_input_timer.setSingleShot(True)
        self._page_input_timer.setInterval(1000)
        self.page_input.valueChanged.connect(self._on_page_input_value_changed)
        self._pending_page_value = self.page_input.value()
        self._page_input_timer.timeout.connect(self._trigger_goto_page)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        copy_name_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        copy_name_shortcut.activated.connect(self.copy_name_with_tooltip)
        copy_path_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        copy_path_shortcut.activated.connect(self.copy_path_with_tooltip)
        open_explorer_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        open_explorer_shortcut.activated.connect(self.open_explorer)
        assign_price_shortcut = QShortcut(QKeySequence("Shift+A"), self)
        assign_price_shortcut.activated.connect(self.assign_price_shortcut)
        edit_record_shortcut = QShortcut(QKeySequence("Shift+E"), self)
        edit_record_shortcut.activated.connect(self.edit_record_shortcut)
        assign_url_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        assign_url_shortcut.activated.connect(self.assign_url_shortcut)

        self._search_query = ""
        self._status_filter = None
        self._sort_field = "date"
        self._sort_order = "desc"
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(400)
        self._search_timer.timeout.connect(self._delayed_apply_search)
        self.search_edit.returnPressed.connect(self.apply_search)
        self.search_edit.textChanged.connect(self._on_search_text_changed)

        self._empty_table_timer = QTimer(self)
        self._empty_table_timer.setSingleShot(True)
        self._empty_table_timer.setInterval(2000)
        self._empty_table_timer.timeout.connect(self._on_empty_table_timeout)

        self.load_data_from_database()

        # Connect NameFieldWidget.project_created to refresh_table
        if hasattr(parent, "main_action_dock") and hasattr(parent.main_action_dock, "_name_field_widget"):
            name_field_widget = parent.main_action_dock._name_field_widget
            name_field_widget.project_created.connect(self._on_project_created)

        self._category_changed = False
        self._subcategory_changed = False

    def _on_project_created(self):
        # Ambil data project terakhir dari database
        self.db_manager.connect()
        files = self.db_manager.get_files_page(page=1, page_size=1, sort_field="id", sort_order="desc")
        self.db_manager.close()
        if files:
            last = files[0]
            self._select_after_refresh = (last['name'], last['path'])
        self.refresh_table()

    def paste_to_search(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.search_edit.setText(text)
            self.apply_search()
            show_statusbar_message(self, f"Pasted to search: {text}")
            if self.table.rowCount() > 0:
                self.table.selectRow(0)
                item = self.table.item(0, 0)
                if item:
                    row_data = item.data(256)
                    if row_data:
                        self.selected_row_data = row_data
                        self._selected_row_index = 0
                        self.row_selected.emit(row_data)

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

    def copy_name_with_tooltip(self):
        if self.selected_row_data:
            name = str(self.selected_row_data['name'])
            QApplication.clipboard().setText(name)
            QToolTip.showText(QCursor.pos(), f"{name}\nCopied to clipboard")

    def copy_path_with_tooltip(self):
        if self.selected_row_data:
            path = str(self.selected_row_data['path'])
            QApplication.clipboard().setText(path)
            QToolTip.showText(QCursor.pos(), f"{path}\nCopied to clipboard")

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

    def assign_price_shortcut(self):
        if not self.selected_row_data:
            show_statusbar_message(self, "No record selected for assign price.")
            return
        dialog = AssignPriceDialog(self.selected_row_data, self.db_manager, self)
        if dialog.exec() == QDialog.Accepted:
            show_statusbar_message(self, "Price assigned.")

    def edit_record_shortcut(self):
        if not self.selected_row_data:
            show_statusbar_message(self, "No record selected for editing.")
            return
        row_data = self.selected_row_data
        dialog = EditRecordDialog(
            row_data,
            self.status_options,
            self.db_manager,
            self,
            main_action_dock=self._main_window.main_action_dock if hasattr(self._main_window, "main_action_dock") else None
        )
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            file_id = row_data['id']
            try:
                self.db_manager.connect()
                status_id = self.db_manager.get_status_id(new_data['status'])
                # Cek perubahan kategori/subkategori
                old_category = row_data.get('category', '')
                old_subcategory = row_data.get('subcategory', '')
                category_id = self.db_manager.get_or_create_category(new_data['category']) if new_data['category'] else None
                subcategory_id = self.db_manager.get_or_create_subcategory(
                    category_id,
                    new_data['subcategory']
                ) if new_data['subcategory'] and new_data['category'] else None
                if new_data['category'] and new_data['category'] != old_category:
                    self._category_changed = True
                if new_data['subcategory'] and new_data['subcategory'] != old_subcategory:
                    self._subcategory_changed = True
                self.db_manager.update_file_record(
                    file_id=file_id,
                    name=new_data['name'],
                    root=new_data['root'],
                    path=new_data['full_path'],
                    status_id=status_id,
                    category_id=category_id,
                    subcategory_id=subcategory_id
                )
            finally:
                self.db_manager.close()
            self.load_data_from_database()
            QMessageBox.information(self, "Success", "Record updated.")
            show_statusbar_message(self, f"Record updated: {new_data['name']}")

    def assign_url_shortcut(self):
        """Handle Ctrl+L shortcut to assign URL to selected file"""
        if not self.selected_row_data:
            show_statusbar_message(self, "No record selected for URL assignment.")
            return
        dialog = AssignFileUrlDialog(self.selected_row_data, self.db_manager, self)
        if dialog.exec() == QDialog.Accepted:
            show_statusbar_message(self, f"URL assigned to {self.selected_row_data['name']}")

    def _on_table_double_click(self, row, column):
        item = self.table.item(row, 0)
        if item:
            row_data = item.data(256)
            if row_data:
                self.selected_row_data = row_data
                self._selected_row_index = row
                self.open_explorer()
                show_statusbar_message(self, f"Double-clicked: Opened {row_data['path']}")
                self.row_selected.emit(row_data)

    def _on_table_cell_clicked(self, row, column):
        self.table.selectRow(row)
        item = self.table.item(row, 0)
        if item:
            row_data = item.data(256)
            if row_data:
                self.selected_row_data = row_data
                self._selected_row_index = row
                show_statusbar_message(self, f"Selected row: {row_data['name']}")
                self.row_selected.emit(row_data)

    def load_data_from_database(self, keep_search=False):
        try:
            self.db_manager.connect()
            self._search_query = self.search_edit.text().strip()
            self._status_filter = self.sort_status_value
            self._sort_field = self.sort_field
            self._sort_order = self.sort_order
            client_id = getattr(self, "sort_client_id", None)
            batch_number = getattr(self, "sort_batch_number", None)
            root_value = getattr(self, "sort_root_value", None)
            category_value = getattr(self, "sort_category_value", None)
            subcategory_value = getattr(self, "sort_subcategory_value", None)
            self.total_records = self.db_manager.count_files()
            self.total_draft = self.db_manager.count_files(status_value="Draft")
            self.found_records = self.db_manager.count_files(
                search_query=self._search_query,
                status_value=self._status_filter,
                client_id=client_id,
                batch_number=batch_number,
                root_value=root_value,
                category_value=category_value,
                subcategory_value=subcategory_value
            )
            self.filtered_data = self.db_manager.get_files_page(
                page=self.current_page,
                page_size=self.page_size,
                search_query=self._search_query,
                sort_field=self._sort_field,
                sort_order=self._sort_order,
                status_value=self._status_filter,
                client_id=client_id,
                batch_number=batch_number,
                root_value=root_value,
                category_value=category_value,
                subcategory_value=subcategory_value
            )
            self.update_table()
            show_statusbar_message(self, "Loaded data from database")
        except Exception as e:
            print(f"Error loading data from database: {e}")
            self.filtered_data = []
            self.update_table()
            show_statusbar_message(self, f"Error loading data: {e}")
        finally:
            self.db_manager.close()

    def refresh_table(self):
        self.load_data_from_database(keep_search=True)
        main_window = self._main_window
        if main_window and hasattr(main_window, "main_action_dock"):
            main_action = main_window.main_action_dock
            # Refresh kategori hanya jika ada perubahan
            if hasattr(main_action, "_combo_category") and hasattr(main_action, "_combo_subcategory"):
                if self._category_changed:
                    try:
                        main_action.db_manager.connect()
                        categories = main_action.db_manager.get_all_categories()
                        main_action._combo_category.clear()
                        main_action._combo_category.addItem("")
                        main_action._combo_category.addItems(categories)
                        main_action.db_manager.close()
                    except Exception as e:
                        print(f"Error refreshing categories: {e}")
                    self._category_changed = False
                current_category = main_action._combo_category.currentText().strip()
                # Refresh subkategori hanya jika ada perubahan
                if self._subcategory_changed and current_category:
                    try:
                        main_action.db_manager.connect()
                        subcategories = main_action.db_manager.get_subcategories_by_category(current_category)
                        main_action._combo_subcategory.clear()
                        main_action._combo_subcategory.addItem("")
                        main_action._combo_subcategory.addItems(subcategories)
                        main_action._combo_subcategory.setEnabled(True)
                        main_action.db_manager.close()
                    except Exception as e:
                        print(f"Error refreshing subcategories: {e}")
                    self._subcategory_changed = False
                elif not current_category:
                    main_action._combo_subcategory.clear()
                    main_action._combo_subcategory.addItem("")
                    main_action._combo_subcategory.setEnabled(False)
            if hasattr(main_action, "_combo_template"):
                try:
                    combo_template = main_action._combo_template
                    prev_index = combo_template.currentIndex()
                    prev_template_id = combo_template.itemData(prev_index) if prev_index > 0 else None
                    prev_text = combo_template.currentText()
                    main_action.db_manager.connect()
                    templates = main_action.db_manager.get_all_templates()
                    combo_template.clear()
                    combo_template.addItem("No Template")
                    found_index = 0
                    for template in templates:
                        combo_template.addItem(template['name'])
                        combo_template.setItemData(combo_template.count() - 1, template['id'])
                        if prev_template_id is not None and template['id'] == prev_template_id:
                            found_index = combo_template.count() - 1
                        elif prev_template_id is None and template['name'] == prev_text:
                            found_index = combo_template.count() - 1
                    combo_template.setCurrentIndex(found_index)
                    main_action.db_manager.close()
                except Exception as e:
                    print(f"Error refreshing templates: {e}")
        show_statusbar_message(self, "Table refreshed")
        if self._select_after_refresh:
            self._select_row_by_name_path(*self._select_after_refresh)
            self._select_after_refresh = None

    def _select_row_by_name_path(self, name, path):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                row_data = item.data(256)
                if row_data and row_data.get('name') == name and row_data.get('path') == path:
                    self.table.selectRow(row)
                    self.selected_row_data = row_data
                    self._selected_row_index = row
                    self.row_selected.emit(row_data)
                    # Trigger properties widget refresh after select
                    if hasattr(self.parent(), "properties_widget"):
                        properties_widget = getattr(self.parent(), "properties_widget")
                        if properties_widget:
                            properties_widget.update_properties(row_data)
                    break

    def _on_search_text_changed(self, text):
        self._search_timer.stop()
        self._search_timer.start()

    def _delayed_apply_search(self):
        self.apply_search()

    def apply_search(self, refresh_only=False):
        self.current_page = 1
        self.load_data_from_database(keep_search=True)
        if not refresh_only:
            query = self.search_edit.text().lower()
            if query:
                show_statusbar_message(self, f"Search applied: {query}")
            else:
                show_statusbar_message(self, "Search cleared")

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
        total_rows = self.found_records
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, total_pages))
        self.page_input.blockSignals(True)
        self.page_input.setMaximum(total_pages)
        self.page_input.setValue(self.current_page)
        self.page_input.blockSignals(False)
        page_data = self.filtered_data
        self.table.setRowCount(len(page_data))
        path_column_width = self.table.columnWidth(3)
        for row_idx, row_data in enumerate(page_data):
            price, currency, note = self.db_manager.get_item_price_detail(row_data['id'])
            if price is not None and currency:
                try:
                    price_float = float(price)
                    if price_float.is_integer():
                        price_str = f"{int(price_float):,}".replace(",", ".")
                    else:
                        price_str = f"{price_float:,.2f}".replace(",", ".")
                    price_str = f"{price_str} {currency}"
                except Exception:
                    price_str = f"{price} {currency}"
            else:
                price_str = "-"
            if note:
                price_note_str = f"{price_str} - {note}"
            else:
                price_note_str = f"{price_str} -"
            earnings = self.db_manager.get_earnings_by_file_id(row_data['id'])
            shares_str = ""
            amount_str = ""
            operational_percent_str = ""
            if earnings:
                usernames = [e['username'] for e in earnings]
                shares_str = "Shares: " + ", ".join(usernames)
                share_amount = earnings[0]['amount'] if len(earnings) > 0 else None
                if share_amount is not None and currency:
                    try:
                        share_float = float(share_amount)
                        if share_float.is_integer():
                            share_str = f"{int(share_float):,}".replace(",", ".")
                        else:
                            share_str = f"{share_float:,.2f}".replace(",", ".")
                        amount_str = f"Amount: {share_str} {currency} each"
                    except Exception:
                        amount_str = f"Amount: {share_amount} {currency} each"
                # Calculate operational percentage used for this record
                try:
                    price_float = float(price)
                    n = len(earnings)
                    share_amount_float = float(earnings[0]["amount"])
                    used_percentage = round((1 - (share_amount_float * n / price_float)) * 100)
                    operational_percent_str = f"Operational Percentage: {used_percentage}%"
                except Exception:
                    operational_percent_str = ""
            client_id = self.db_manager.get_assigned_client_id_for_file(row_data['id'])
            client_name = self.db_manager.get_client_name_by_file_id(row_data['id'])
            batch_number = "-"
            if client_id:
                batch_number_val = self.db_manager.get_assigned_batch_number(row_data['id'], client_id)
                if batch_number_val:
                    batch_number = batch_number_val
            tooltip = (
                f"Date: {row_data.get('date','')}\n"
                f"Name: {row_data.get('name','')}\n"
                f"Root: {row_data.get('root','')}\n"
                f"Path: {row_data.get('path','')}\n"
                f"Status: {row_data.get('status','')}\n"
                f"Client: {client_name}\n"
                f"Batch Number: {batch_number}\n"
                f"Price: {price_note_str}\n"
                f"{shares_str}\n"
                f"{amount_str}\n"
                f"{operational_percent_str}"
            )
            date_item = QTableWidgetItem(row_data['date'])
            date_item.setData(256, row_data)
            date_item.setToolTip(tooltip)
            self.table.setItem(row_idx, 0, date_item)
            name_item = QTableWidgetItem(row_data['name'])
            name_item.setToolTip(tooltip)
            self.table.setItem(row_idx, 1, name_item)
            root_item = QTableWidgetItem(row_data['root'])
            root_item.setToolTip(tooltip)
            self.table.setItem(row_idx, 2, root_item)
            truncated_path = self._truncate_path_by_width(row_data['path'], path_column_width)
            path_item = QTableWidgetItem(truncated_path)
            path_item.setToolTip(tooltip)
            self.table.setItem(row_idx, 3, path_item)
            combo = NoWheelComboBox(self.table)
            combo.addItems(self.status_options)
            combo.setCurrentText(row_data['status'])
            self._set_status_text_color(combo, row_data['status'])
            combo.currentTextChanged.connect(lambda val, row=row_idx: self._on_status_changed(row, val))
            combo.setFocusPolicy(Qt.StrongFocus)
            self.table.setCellWidget(row_idx, 4, combo)
            combo.setToolTip(tooltip)
        self.page_label.setText(f"Page {self.current_page} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)
        self.update_stats_label()
        if self._selected_row_index is not None and 0 <= self._selected_row_index < self.table.rowCount():
            self.table.selectRow(self._selected_row_index)
        # Trigger empty table timer if table is empty
        if self.table.rowCount() == 0:
            if not self._empty_table_timer.isActive():
                self._empty_table_timer.start()
        else:
            if self._empty_table_timer.isActive():
                self._empty_table_timer.stop()

    def _on_empty_table_timeout(self):
        if self.table.rowCount() == 0:
            self.refresh_table()

    def goto_page(self, value):
        total_rows = self.found_records
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        if 1 <= value <= total_pages:
            self.current_page = value
            self.load_data_from_database(keep_search=True)

    def _on_page_input_value_changed(self, value):
        self._pending_page_value = value
        self._page_input_timer.stop()
        self._page_input_timer.start()

    def _trigger_goto_page(self):
        value = getattr(self, "_pending_page_value", None)
        if value is not None:
            self.goto_page(value)

    def update_stats_label(self):
        last_date = "-"
        if self.filtered_data:
            last_date = self.filtered_data[0]['date']
        client_id = getattr(self, "sort_client_id", None)
        batch_number = getattr(self, "sort_batch_number", None)
        root_value = getattr(self, "sort_root_value", None)
        category_value = getattr(self, "sort_category_value", None)
        subcategory_value = getattr(self, "sort_subcategory_value", None)
        client_name = ""
        if client_id:
            try:
                clients = self.db_manager.get_all_clients_simple()
                for c in clients:
                    if c["id"] == client_id:
                        client_name = c["client_name"]
                        break
            except Exception:
                client_name = str(client_id)
        if root_value:
            self.stats_label.setText(
                f"Root: {root_value} | Found: {self.found_records} Records"
            )
        elif category_value:
            if subcategory_value:
                self.stats_label.setText(
                    f"Category: {category_value} | Sub: {subcategory_value} | Found: {self.found_records} Records"
                )
            else:
                self.stats_label.setText(
                    f"Category: {category_value} | Found: {self.found_records} Records"
                )
        elif (self.search_edit.text().strip() or self.sort_status_value) and not (client_id and batch_number):
            self.stats_label.setText(
                f"Total: {self.total_records} | Draft: {self.total_draft} | Last: {last_date} | Found: {self.found_records} Records"
            )
        elif client_id and batch_number:
            self.stats_label.setText(
                f"Batch: {batch_number} | Client: {client_name} | Found: {self.found_records} Records"
            )
        else:
            self.stats_label.setText(
                f"Total: {self.total_records} | Draft: {self.total_draft} | Last: {last_date}"
            )

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
        if row < 0 or row >= len(self.filtered_data):
            return
        row_data = self.filtered_data[row]
        old_status = row_data['status']
        row_data['status'] = value
        try:
            self.db_manager.connect()
            status_id = self.db_manager.get_status_id(value)
            if status_id is not None:
                self.db_manager.update_file_status(row_data['id'], status_id)
                row_data['status_id'] = status_id
                combo = self.table.cellWidget(row, 4)
                if combo:
                    self._set_status_text_color(combo, value)
                self.load_data_from_database(keep_search=True)
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
            self.load_data_from_database(keep_search=True)

    def next_page(self):
        total_rows = self.found_records
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_data_from_database(keep_search=True)

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
        icon_edit = qta.icon("fa6s.pen-to-square")
        icon_assign_price = qta.icon("fa6s.money-bill-wave")
        icon_assign_url = qta.icon("fa6s.link")
        action_copy_name = QAction(icon_copy_name, "Copy Name\tCtrl+C", self)
        action_copy_path = QAction(icon_copy_path, "Copy Path\tCtrl+X", self)
        action_open_explorer = QAction(icon_open_explorer, "Open in Explorer\tCtrl+E", self)
        action_delete = QAction(icon_delete, "Delete Record", self)
        action_edit = QAction(icon_edit, "Edit Record\tShift+E", self)
        action_assign_price = QAction(icon_assign_price, "Assign Price\tShift+A", self)
        action_assign_url = QAction(icon_assign_url, "Assign URL\tCtrl+L", self)

        def do_copy_name():
            QApplication.clipboard().setText(str(row_data['name']))
            show_statusbar_message(self, f"Name copied: {row_data['name']}")
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QToolTip
            QToolTip.showText(QCursor.pos(), f"{row_data['name']}\nCopied to clipboard")

        def do_copy_path():
            QApplication.clipboard().setText(str(row_data['path']))
            show_statusbar_message(self, f"Path copied: {row_data['path']}")
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QToolTip
            QToolTip.showText(QCursor.pos(), f"{row_data['path']}\nCopied to clipboard")

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
            name = row_data.get('name', '-')
            path = row_data.get('path', '-')
            date = row_data.get('date', '-')
            category = row_data.get('category', '-')
            subcategory = row_data.get('subcategory', '-')
            status = row_data.get('status', '-')
            file_id = row_data.get('id', None)
            related_info = self.db_manager.get_file_related_delete_info(file_id)
            item_price_info = [
                f"ID: {ip['id']}, Price: {ip['price']} {ip['currency']}, Note: {ip['note']}"
                for ip in related_info["item_price"]
            ]
            earnings_info = [
                f"ID: {e['id']}, TeamID: {e['team_id']}, Amount: {e['amount']}, Note: {e['note']}"
                for e in related_info["earnings"]
            ]
            file_client_price_info = [
                f"ID: {fcp['id']}, ClientID: {fcp['client_id']}"
                for fcp in related_info["file_client_price"]
            ]
            file_client_batch_info = [
                f"ID: {fcb['id']}, ClientID: {fcb['client_id']}, Batch: {fcb['batch_number']}"
                for fcb in related_info["file_client_batch"]
            ]
            details = (
                f"• Name: {name}\n"
                f"• Path: {path}\n"
                f"• Date: {date}\n"
                f"• Category: {category}\n"
                f"• Subcategory: {subcategory}\n"
                f"• Status: {status}\n"
                "\nThe following related data will also be deleted:\n"
                f"• Project Price:\n"
                + ("\n".join(f"   - {item}" for item in item_price_info) if item_price_info else "   - None") + "\n\n"
                f"• Team Earnings:\n"
                + ("\n".join(f"   - {item}" for item in earnings_info) if earnings_info else "   - None") + "\n\n"
                f"• Client Assignments:\n"
                + ("\n".join(f"   - {item}" for item in file_client_price_info) if file_client_price_info else "   - None") + "\n\n"
                f"• Batch Assignments:\n"
                + ("\n".join(f"   - {item}" for item in file_client_batch_info) if file_client_batch_info else "   - None")
            )
            confirm1 = QMessageBox.warning(
                self,
                "Delete Record",
                f"Delete this record?\n\n"
                f"Details:\n{details}\n\n"
                "This action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm1 == QMessageBox.Yes:
                confirm2 = QMessageBox.warning(
                    self,
                    "Are you sure?",
                    f"Are you sure you want to permanently delete this record and its project folder?\n\n"
                    f"Details:\n{details}",
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
        def do_edit_record():
            dialog = EditRecordDialog(
                row_data,
                self.status_options,
                self.db_manager,
                self,
                main_action_dock=self._main_window.main_action_dock if hasattr(self._main_window, "main_action_dock") else None
            )
            if dialog.exec() == QDialog.Accepted:
                new_data = dialog.get_data()
                file_id = row_data['id']
                try:
                    self.db_manager.connect()
                    status_id = self.db_manager.get_status_id(new_data['status'])
                    category_id = self.db_manager.get_or_create_category(new_data['category']) if new_data['category'] else None
                    subcategory_id = self.db_manager.get_or_create_subcategory(
                        category_id,
                        new_data['subcategory']
                    ) if new_data['subcategory'] and new_data['category'] else None
                    self.db_manager.update_file_record(
                        file_id=file_id,
                        name=new_data['name'],
                        root=new_data['root'],
                        path=new_data['full_path'],
                        status_id=status_id,
                        category_id=category_id,
                        subcategory_id=subcategory_id
                    )
                finally:
                    self.db_manager.close()
                self.load_data_from_database()
                QMessageBox.information(self, "Success", "Record updated.")
                show_statusbar_message(self, f"Record updated: {new_data['name']}")

        def do_assign_price():
            dialog = AssignPriceDialog(row_data, self.db_manager, self)
            if dialog.exec() == QDialog.Accepted:
                show_statusbar_message(self, "Price assigned.")

        def do_assign_url():
            dialog = AssignFileUrlDialog(row_data, self.db_manager, self)
            if dialog.exec() == QDialog.Accepted:
                show_statusbar_message(self, f"URL assigned to {row_data['name']}")

        action_copy_name.triggered.connect(do_copy_name)
        action_copy_path.triggered.connect(do_copy_path)
        action_open_explorer.triggered.connect(do_open_explorer)
        action_assign_price.triggered.connect(do_assign_price)
        action_assign_url.triggered.connect(do_assign_url)
        action_edit.triggered.connect(do_edit_record)
        action_delete.triggered.connect(do_delete_record)
        menu.addAction(action_copy_name)
        menu.addAction(action_copy_path)
        menu.addAction(action_open_explorer)
        menu.addAction(action_assign_price)
        menu.addAction(action_assign_url)
        menu.addAction(action_edit)
        menu.addSeparator()
        menu.addAction(action_delete)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_sort_dialog(self):
        dlg = SortDialog(self.status_options, self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_sort_option(self.status_options)
            field, order, status_value, client_id, batch_number, root_value, category_value, subcategory_value = result
            self.sort_field = field
            self.sort_order = order
            self.sort_status_value = status_value
            self.sort_client_id = client_id
            self.sort_batch_number = batch_number
            self.sort_root_value = root_value
            self.sort_category_value = category_value
            self.sort_subcategory_value = subcategory_value
            self.current_page = 1
            self.load_data_from_database(keep_search=True)
            show_statusbar_message(
                self,
                f"Sort applied: {field} {order} {status_value if status_value else ''} {client_id if client_id else ''} {batch_number if batch_number else ''} {root_value if root_value else ''} {category_value if category_value else ''} {subcategory_value if subcategory_value else ''}"
            )

    def do_edit_record(self):
        if not self.selected_row_data:
            show_statusbar_message(self, "No record selected for editing.")
            return
        row_data = self.selected_row_data
        dialog = EditRecordDialog(
            row_data,
            self.status_options,
            self.db_manager,
            self,
            main_action_dock=self._main_window.main_action_dock if hasattr(self._main_window, "main_action_dock") else None
        )
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            file_id = row_data['id']
            try:
                self.db_manager.connect()
                status_id = self.db_manager.get_status_id(new_data['status'])
                old_category = row_data.get('category', '')
                old_subcategory = row_data.get('subcategory', '')
                category_id = self.db_manager.get_or_create_category(new_data['category']) if new_data['category'] else None
                subcategory_id = self.db_manager.get_or_create_subcategory(
                    category_id,
                    new_data['subcategory']
                ) if new_data['subcategory'] and new_data['category'] else None
                if new_data['category'] and new_data['category'] != old_category:
                    self._category_changed = True
                if new_data['subcategory'] and new_data['subcategory'] != old_subcategory:
                    self._subcategory_changed = True
                self.db_manager.update_file_record(
                    file_id=file_id,
                    name=new_data['name'],
                    root=new_data['root'],
                    path=new_data['full_path'],
                    status_id=status_id,
                    category_id=category_id,
                    subcategory_id=subcategory_id
                )
            finally:
                self.db_manager.close()
            self.load_data_from_database()
            QMessageBox.information(self, "Success", "Record updated.")
            show_statusbar_message(self, f"Record updated: {new_data['name']}")