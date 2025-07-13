from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QSpacerItem, QSizePolicy, QComboBox
)
from PySide6.QtGui import QColor, QAction, QFontMetrics
from PySide6.QtCore import Signal
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path

class CentralWidget(QWidget):
    row_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = parent.config_manager
        self.status_config = self.config_manager.get("status_options")
        self.status_options = list(self.status_config.keys())
        
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        db_config_manager = ConfigManager(str(db_config_path))
        self.db_manager = DatabaseManager(db_config_manager, self.config_manager)
        
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search...")
        search_icon = qta.icon("fa6s.magnifying-glass")
        search_action = QAction(self)
        search_action.setIcon(search_icon)
        self.search_edit.addAction(search_action, QLineEdit.LeadingPosition)
        top_row.addWidget(self.search_edit)

        self.refresh_btn = QPushButton("Refresh", self)
        self.refresh_btn.setIcon(qta.icon("fa6s.rotate"))
        top_row.addWidget(self.refresh_btn)

        top_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(top_row)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Name", "Root", "Path", "Status"])
        self._all_data = []
        self.page_size = 5
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

        pagination_row = QHBoxLayout()
        self.prev_btn = QPushButton("Prev", self)
        self.prev_btn.setIcon(qta.icon("fa6s.angle-left"))
        self.next_btn = QPushButton("Next", self)
        self.next_btn.setIcon(qta.icon("fa6s.angle-right"))
        self.page_label = QLabel(self)
        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addWidget(self.next_btn)

        self.stats_label = QLabel(self)
        self.stats_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 20px;")
        pagination_row.addWidget(self.stats_label)

        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(pagination_row)

        self.setLayout(layout)

        self.refresh_btn.clicked.connect(self.refresh_table)
        self.search_edit.textChanged.connect(self.apply_search)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.table.itemSelectionChanged.connect(self.on_row_selected)

        self.load_data_from_database()

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
            
        except Exception as e:
            print(f"Error loading data from database: {e}")
            self._all_data = []
            self.filtered_data = []
            self.update_table()
        finally:
            self.db_manager.close()

    def refresh_table(self):
        self.load_data_from_database()

    def apply_search(self):
        query = self.search_edit.text().lower()
        if query:
            self.filtered_data = [
                row for row in self._all_data
                if any(query in str(value).lower() for value in row.values() if value)
            ]
        else:
            self.filtered_data = self._all_data.copy()
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
            
            self.table.setItem(row_idx, 1, QTableWidgetItem(row_data['name']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row_data['root']))
            
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

    def update_stats_label(self):
        total_records = len(self._all_data)
        last_date = "-"
        if self._all_data:
            last_date = self._all_data[0]['date']
        self.stats_label.setText(f"Total: {total_records} | Last: {last_date}")

    def on_row_selected(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            date_item = self.table.item(current_row, 0)
            if date_item:
                row_data = date_item.data(256)
                if row_data:
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
