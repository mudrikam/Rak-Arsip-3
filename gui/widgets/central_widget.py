from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QSpacerItem, QSizePolicy, QComboBox
)
from PySide6.QtGui import QColor, QAction
import qtawesome as qta

class CentralWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = parent.config_manager
        self.status_config = self.config_manager.get("status_options")
        self.status_options = list(self.status_config.keys())
        
        layout = QVBoxLayout(self)

        # Search and refresh row
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

        # Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Name", "Root", "Path", "Status"])
        self._all_data = [
            ["2025-01-01", "Project Alpha", "Arsip", "D:\\Arsip\\Alpha", "Draft"],
            ["2025-01-02", "Project Beta", "Arsip", "D:\\Arsip\\Beta", "Active"],
            ["2025-01-03", "Project Gamma", "Arsip", "D:\\Arsip\\Gamma", "Modelling"],
            ["2025-01-04", "Project Delta", "Arsip", "D:\\Arsip\\Delta", "Rendering"],
            ["2025-01-05", "Project Epsilon", "Arsip", "D:\\Arsip\\Epsilon", "Photoshop"],
            ["2025-01-06", "Project Zeta", "Arsip", "D:\\Arsip\\Zeta", "Approved"],
            ["2025-01-07", "Project Eta", "Arsip", "D:\\Arsip\\Eta", "Rejected"],
            ["2025-01-08", "Project Theta", "Arsip", "D:\\Arsip\\Theta", "Finished"],
            ["2025-01-09", "Project Iota", "Arsip", "D:\\Arsip\\Iota", "Draft"],
            ["2025-01-10", "Project Kappa", "Arsip", "D:\\Arsip\\Kappa", "Active"],
            ["2025-01-11", "Project Lambda", "Arsip", "D:\\Arsip\\Lambda", "Modelling"],
            ["2025-01-12", "Project Mu", "Arsip", "D:\\Arsip\\Mu", "Rendering"],
        ]
        self.page_size = 5
        self.current_page = 1
        self.filtered_data = self._all_data.copy()

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Pagination row
        pagination_row = QHBoxLayout()
        self.prev_btn = QPushButton("Prev", self)
        self.prev_btn.setIcon(qta.icon("fa6s.angle-left"))
        self.next_btn = QPushButton("Next", self)
        self.next_btn.setIcon(qta.icon("fa6s.angle-right"))
        self.page_label = QLabel(self)
        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addWidget(self.next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(pagination_row)

        self.setLayout(layout)

        self.refresh_btn.clicked.connect(self.refresh_table)
        self.search_edit.textChanged.connect(self.apply_search)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)

        self.refresh_table()

    def refresh_table(self):
        self.apply_search()

    def apply_search(self):
        query = self.search_edit.text().lower()
        if query:
            self.filtered_data = [
                row for row in self._all_data
                if any(query in str(cell).lower() for cell in row)
            ]
        else:
            self.filtered_data = self._all_data.copy()
        self.current_page = 1
        self.update_table()

    def update_table(self):
        total_rows = len(self.filtered_data)
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, total_pages))
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        page_data = self.filtered_data[start:end]

        self.table.setRowCount(len(page_data))
        for row_idx, row_data in enumerate(page_data):
            for col_idx, value in enumerate(row_data):
                if col_idx == 4:
                    combo = QComboBox(self.table)
                    combo.addItems(self.status_options)
                    combo.setCurrentText(value)
                    self._set_status_text_color(combo, value)
                    combo.currentTextChanged.connect(lambda val, row=row_idx: self._on_status_changed(row, val))
                    self.table.setCellWidget(row_idx, col_idx, combo)
                else:
                    item = QTableWidgetItem(value)
                    self.table.setItem(row_idx, col_idx, item)
        self.page_label.setText(f"Page {self.current_page} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

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
            self.filtered_data[global_row][4] = value
            for idx, row_data in enumerate(self._all_data):
                if row_data[:4] == self.filtered_data[global_row][:4]:
                    self._all_data[idx][4] = value
                    break
        combo = self.table.cellWidget(row, 4)
        if combo:
            self._set_status_text_color(combo, value)

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
