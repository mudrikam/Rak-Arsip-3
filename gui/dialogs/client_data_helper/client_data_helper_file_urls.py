from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QComboBox, QLabel, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
import qtawesome as qta

class ClientDataFileUrlsHelper:
    """Helper class for File URLs tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # Data storage
        self._file_urls_data_all = []
        self._file_urls_data_filtered = []
        self._selected_client_id = None
        self._selected_batch_number = None
        
        # Stats labels
        self._client_name_label = None
        self._total_files_label = None
        self._batch_number_label = None
    
    def init_file_urls_tab(self, tab_widget):
        """Initialize the file URLs tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # Stats section
        stats_layout = QHBoxLayout()
        self._client_name_label = QLabel("Client: -")
        self._total_files_label = QLabel("Total Files: 0")
        self._batch_number_label = QLabel("Batch Number: -")
        
        stats_layout.addWidget(self._client_name_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self._total_files_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self._batch_number_label)
        tab_layout.addLayout(stats_layout)
        
        # Search and sort row
        controls_layout = QHBoxLayout()
        
        # Search
        self.file_urls_search_edit = QLineEdit()
        self.file_urls_search_edit.setPlaceholderText("Search filename, provider, URL, or note...")
        self.file_urls_search_edit.setMinimumHeight(32)
        self.file_urls_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_layout.addWidget(self.file_urls_search_edit, 1)
        
        # Sort controls
        controls_layout.addWidget(QLabel("Sort by:"))
        self.file_urls_sort_combo = QComboBox()
        self.file_urls_sort_combo.addItems(["Filename", "Provider", "URL", "Note"])
        self.file_urls_sort_combo.setCurrentText("Filename")
        controls_layout.addWidget(self.file_urls_sort_combo)
        
        self.file_urls_order_combo = QComboBox()
        self.file_urls_order_combo.addItems(["Ascending", "Descending"])
        self.file_urls_order_combo.setCurrentText("Ascending")
        controls_layout.addWidget(self.file_urls_order_combo)
        
        tab_layout.addLayout(controls_layout)
        
        # File URLs table
        self.file_urls_table = QTableWidget(tab)
        self.file_urls_table.setColumnCount(4)
        self.file_urls_table.setHorizontalHeaderLabels([
            "Filename", "Provider", "URL", "Note"
        ])
        self.file_urls_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.file_urls_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_urls_table.setSelectionMode(QTableWidget.SingleSelection)
        self.file_urls_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.file_urls_table)
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.link"), "File URLs")
        
        # Connect signals
        self.file_urls_search_edit.textChanged.connect(self.on_file_urls_search_changed)
        self.file_urls_sort_combo.currentTextChanged.connect(self.on_file_urls_sort_changed)
        self.file_urls_order_combo.currentTextChanged.connect(self.on_file_urls_sort_changed)
        self.file_urls_table.cellDoubleClicked.connect(self.on_file_urls_row_double_clicked)
        self.file_urls_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_urls_table.customContextMenuRequested.connect(self.show_file_urls_context_menu)
    
    def load_file_urls_for_batch(self, client_id, batch_number, client_name=""):
        """Load file URLs for selected batch"""
        self._selected_client_id = client_id
        self._selected_batch_number = batch_number
        
        # Update stats
        self._client_name_label.setText(f"Client: {client_name}")
        self._batch_number_label.setText(f"Batch Number: {batch_number}")
        
        # Get files in this batch
        try:
            # Get file IDs for this batch and client
            file_urls_data = self.db_helper.get_file_urls_by_batch_and_client(batch_number, client_id)
            self._file_urls_data_all = file_urls_data
            
            # Update total files count
            self._total_files_label.setText(f"Total Files: {len(file_urls_data)}")
            
            self.update_file_urls_table()
        except Exception as e:
            print(f"Error loading file URLs: {e}")
            self._file_urls_data_all = []
            self._total_files_label.setText("Total Files: 0")
            self.update_file_urls_table()
    
    def on_file_urls_search_changed(self):
        """Handle file URLs search text change"""
        self.update_file_urls_table()
    
    def on_file_urls_sort_changed(self):
        """Handle file URLs sort change"""
        self.update_file_urls_table()
    
    def update_file_urls_table(self):
        """Update the file URLs table with filtered and sorted data"""
        search_text = self.file_urls_search_edit.text().strip().lower()
        
        # Filter data - data is tuple: (filename, provider_name, url_value, note)
        if search_text:
            self._file_urls_data_filtered = [
                item for item in self._file_urls_data_all
                if (search_text in str(item[0]).lower() or  # filename
                    search_text in str(item[1]).lower() or  # provider_name
                    search_text in str(item[2]).lower() or  # url_value
                    search_text in str(item[3] or "").lower())  # note
            ]
        else:
            self._file_urls_data_filtered = list(self._file_urls_data_all)
        
        # Sort data
        sort_field = self.file_urls_sort_combo.currentText()
        sort_ascending = self.file_urls_order_combo.currentText() == "Ascending"
        
        field_map = {
            "Filename": 0,
            "Provider": 1, 
            "URL": 2,
            "Note": 3
        }
        
        sort_index = field_map.get(sort_field, 0)
        self._file_urls_data_filtered.sort(
            key=lambda x: str(x[sort_index] or "").lower(),
            reverse=not sort_ascending
        )
        
        # Update table
        self.file_urls_table.setRowCount(len(self._file_urls_data_filtered))
        for row_idx, item in enumerate(self._file_urls_data_filtered):
            self.file_urls_table.setItem(row_idx, 0, QTableWidgetItem(str(item[0] or "")))  # filename
            self.file_urls_table.setItem(row_idx, 1, QTableWidgetItem(str(item[1] or "")))  # provider
            self.file_urls_table.setItem(row_idx, 2, QTableWidgetItem(str(item[2] or "")))  # url
            self.file_urls_table.setItem(row_idx, 3, QTableWidgetItem(str(item[3] or "")))  # note
    
    def show_file_urls_context_menu(self, pos):
        """Show context menu for file URLs table"""
        index = self.file_urls_table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        if row >= len(self._file_urls_data_filtered):
            return
        
        menu = QMenu(self.file_urls_table)
        icon_copy = qta.icon("fa6s.copy")
        icon_open = qta.icon("fa6s.external-link-alt")
        
        action_copy_filename = QAction(icon_copy, "Copy Filename", self.parent)
        action_copy_url = QAction(icon_copy, "Copy URL", self.parent)
        action_open_url = QAction(icon_open, "Open URL", self.parent)
        
        def copy_filename():
            filename = self._file_urls_data_filtered[row][0]  # first element is filename
            QApplication.clipboard().setText(filename)
        
        def copy_url():
            url = self._file_urls_data_filtered[row][2]  # third element is url
            QApplication.clipboard().setText(url)
        
        def open_url():
            url = self._file_urls_data_filtered[row][2]  # third element is url
            if url:
                import webbrowser
                webbrowser.open(url)
        
        action_copy_filename.triggered.connect(copy_filename)
        action_copy_url.triggered.connect(copy_url)
        action_open_url.triggered.connect(open_url)
        
        menu.addAction(action_copy_filename)
        menu.addAction(action_copy_url)
        menu.addAction(action_open_url)
        menu.exec(self.file_urls_table.viewport().mapToGlobal(pos))
    
    def on_file_urls_row_double_clicked(self, row, col):
        """Handle file URLs row double click - copy filename and search in main window"""
        if row >= len(self._file_urls_data_filtered):
            return
        
        file_data = self._file_urls_data_filtered[row]
        file_name = file_data[0]  # first element is filename
        
        if file_name:
            # Copy filename to clipboard
            QApplication.clipboard().setText(str(file_name))
            
            # Try to paste to main window search
            from ..client_data_dialog import find_main_window
            main_window = find_main_window(self.parent)
            central_widget = getattr(main_window, "central_widget", None)
            if central_widget and hasattr(central_widget, "paste_to_search"):
                central_widget.paste_to_search()
            
            # Close the client data dialog
            self.parent.accept()
    
    def clear_file_urls_tab(self):
        """Clear the file URLs tab"""
        self.file_urls_table.setRowCount(0)
        self._file_urls_data_all = []
        self._file_urls_data_filtered = []
        self._selected_client_id = None
        self._selected_batch_number = None
        
        # Reset stats
        self._client_name_label.setText("Client: -")
        self._total_files_label.setText("Total Files: 0")
        self._batch_number_label.setText("Batch Number: -")
