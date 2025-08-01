from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView, QFrame
)
from PySide6.QtCore import Qt
import qtawesome as qta

class ClientDataClientsHelper:
    """Helper class for Clients tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # Data storage
        self._clients_data_all = []
        self._clients_data_sorted = []
        self._clients_data_filtered = []
        self._clients_data = []
        
        # State variables
        self.clients_sort_field = "Name"
        self.clients_sort_order = "Ascending"
        self.clients_search_text = ""
    
    def init_clients_tab(self, tab_widget):
        """Initialize the clients tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # Statistics panel
        self._create_statistics_panel(tab_layout)
        
        # Search and sort row
        row = QHBoxLayout()
        self.clients_search_edit = QLineEdit()
        self.clients_search_edit.setPlaceholderText("Search by name, contact, status, note, files...")
        self.clients_search_edit.setMinimumHeight(32)
        self.clients_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.clients_search_edit, 1)
        row.addStretch()
        
        self.clients_sort_combo = QComboBox()
        self.clients_sort_combo.addItems(["Name", "Contact", "Status", "Note", "Files"])
        self.clients_sort_order_combo = QComboBox()
        self.clients_sort_order_combo.addItems(["Ascending", "Descending"])
        row.addWidget(QLabel("Sort by:"))
        row.addWidget(self.clients_sort_combo)
        row.addWidget(self.clients_sort_order_combo)
        tab_layout.addLayout(row)
        
        # Clients table
        self.clients_table = QTableWidget(tab)
        self.clients_table.setColumnCount(6)
        self.clients_table.setHorizontalHeaderLabels([
            "Name", "Contact", "Links", "Status", "Note", "Files"
        ])
        self.clients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setSelectionMode(QTableWidget.SingleSelection)
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.clients_table.cellClicked.connect(self.on_client_row_clicked)
        self.clients_table.cellDoubleClicked.connect(self.on_client_row_double_clicked)
        tab_layout.addWidget(self.clients_table)
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.users"), "Clients")
        
        # Connect signals
        self.clients_sort_combo.currentIndexChanged.connect(self.on_clients_sort_changed)
        self.clients_sort_order_combo.currentIndexChanged.connect(self.on_clients_sort_changed)
        self.clients_search_edit.textChanged.connect(self.on_clients_search_changed)
        
        # Load initial data
        self.load_clients_data()
    
    def _create_statistics_panel(self, parent_layout):
        """Create the statistics panel above the search"""
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_frame.setLineWidth(1)
        stats_frame.setMinimumHeight(60)
        stats_frame.setMaximumHeight(80)
        
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 8, 10, 8)
        
        # Total Queue (Draft files)
        queue_layout = QVBoxLayout()
        self.queue_label = QLabel("Total Queue:")
        self.queue_label.setStyleSheet("font-weight: bold; color: #e67e22;")
        self.queue_label.setAlignment(Qt.AlignCenter)
        self.queue_value = QLabel("0")
        self.queue_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.queue_value.setAlignment(Qt.AlignCenter)
        queue_layout.addWidget(self.queue_label)
        queue_layout.addWidget(self.queue_value)
        queue_layout.setAlignment(Qt.AlignCenter)
        
        # Total Files
        files_layout = QVBoxLayout()
        self.files_label = QLabel("Total Files:")
        self.files_label.setStyleSheet("font-weight: bold; color: #3498db;")
        self.files_label.setAlignment(Qt.AlignCenter)
        self.files_value = QLabel("0")
        self.files_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.files_value.setAlignment(Qt.AlignCenter)
        files_layout.addWidget(self.files_label)
        files_layout.addWidget(self.files_value)
        files_layout.setAlignment(Qt.AlignCenter)
        
        # Total Asset Value USD
        usd_layout = QVBoxLayout()
        self.usd_label = QLabel("Total Asset Value (USD):")
        self.usd_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.usd_label.setAlignment(Qt.AlignCenter)
        self.usd_value = QLabel("$0.00")
        self.usd_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.usd_value.setAlignment(Qt.AlignCenter)
        usd_layout.addWidget(self.usd_label)
        usd_layout.addWidget(self.usd_value)
        usd_layout.setAlignment(Qt.AlignCenter)
        
        # Total Asset Value IDR
        idr_layout = QVBoxLayout()
        self.idr_label = QLabel("Total Asset Value (IDR):")
        self.idr_label.setStyleSheet("font-weight: bold; color: #8e44ad;")
        self.idr_label.setAlignment(Qt.AlignCenter)
        self.idr_value = QLabel("Rp 0")
        self.idr_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.idr_value.setAlignment(Qt.AlignCenter)
        idr_layout.addWidget(self.idr_label)
        idr_layout.addWidget(self.idr_value)
        idr_layout.setAlignment(Qt.AlignCenter)
        
        # Add layouts to stats layout with separators
        stats_layout.addLayout(queue_layout)
        stats_layout.addWidget(self._create_separator())
        stats_layout.addLayout(files_layout)
        stats_layout.addWidget(self._create_separator())
        stats_layout.addLayout(usd_layout)
        stats_layout.addWidget(self._create_separator())
        stats_layout.addLayout(idr_layout)
        
        parent_layout.addWidget(stats_frame)
    
    def _create_separator(self):
        """Create a vertical separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        return separator
    
    def on_clients_sort_changed(self):
        """Handle sort changes"""
        self.clients_sort_field = self.clients_sort_combo.currentText()
        self.clients_sort_order = self.clients_sort_order_combo.currentText()
        self.update_clients_table()
    
    def on_clients_search_changed(self):
        """Handle search text changes"""
        self.clients_search_text = self.clients_search_edit.text().strip().lower()
        self.update_clients_table()
    
    def load_clients_data(self):
        """Load clients data from database"""
        self._clients_data_all = self.db_helper.get_all_clients()
        self.update_clients_table()
        self.update_statistics()
    
    def update_statistics(self):
        """Update the statistics panel with current data"""
        try:
            stats = self.db_helper.get_overall_statistics()
            
            # Update Total Queue (draft count)
            draft_count = stats.get("draft_count", 0)
            self.queue_value.setText(str(draft_count))
            
            # Update Total Files
            total_files = stats.get("total_files", 0)
            self.files_value.setText(str(total_files))
            
            # Update Asset Values
            asset_values = stats.get("asset_values", {})
            
            # Format USD value
            usd_value = asset_values.get("USD", 0)
            self.usd_value.setText(f"${usd_value:,.2f}")
            
            # Format IDR value
            idr_value = asset_values.get("IDR", 0)
            self.idr_value.setText(f"Rp {idr_value:,.0f}")
            
        except Exception as e:
            print(f"Error updating statistics: {e}")
            # Set default values if error occurs
            self.queue_value.setText("0")
            self.files_value.setText("0")
            self.usd_value.setText("$0.00")
            self.idr_value.setText("Rp 0")
    
    def update_clients_table(self):
        """Update the clients table with filtered and sorted data"""
        sort_field = self.clients_sort_field
        sort_order = self.clients_sort_order
        search_text = self.clients_search_edit.text().strip().lower()
        
        # Map display names to database fields
        sort_map = {
            "Name": "client_name",
            "Contact": "contact",
            "Status": "status",
            "Note": "note",
            "Files": "_file_count"
        }
        key = sort_map.get(sort_field, "client_name")
        reverse = sort_order == "Descending"
        
        # Filter data
        if search_text:
            self._clients_data_filtered = []
            for client in self._clients_data_all:
                if (
                    search_text in str(client.get("client_name", "")).lower()
                    or search_text in str(client.get("contact", "")).lower()
                    or search_text in str(client.get("status", "")).lower()
                    or search_text in str(client.get("note", "")).lower()
                    or search_text in str(client.get("_file_count", "")).lower()
                ):
                    self._clients_data_filtered.append(client)
        else:
            self._clients_data_filtered = list(self._clients_data_all)
        
        # Sort data
        try:
            if key == "_file_count":
                self._clients_data_sorted = sorted(
                    self._clients_data_filtered, 
                    key=lambda x: int(x.get("_file_count", 0)), 
                    reverse=reverse
                )
            else:
                self._clients_data_sorted = sorted(
                    self._clients_data_filtered, 
                    key=lambda x: str(x.get(key, "")).lower(), 
                    reverse=reverse
                )
        except Exception:
            self._clients_data_sorted = list(self._clients_data_filtered)
        
        # Update table
        self.clients_table.setRowCount(len(self._clients_data_sorted))
        self._clients_data = []
        
        for row_idx, client in enumerate(self._clients_data_sorted):
            self._clients_data.append(client)
            
            # Add data columns
            for col_idx, key_col in enumerate(["client_name", "contact", "links", "status", "note"]):
                value = client.get(key_col, "")
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.clients_table.setItem(row_idx, col_idx, item)
            
            # Add file count column
            file_count = client.get("_file_count", 0)
            item = QTableWidgetItem(str(file_count))
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.clients_table.setItem(row_idx, 5, item)
    
    def on_client_row_clicked(self, row, col):
        """Handle client row click - delegate to parent"""
        # Select the row visually
        self.clients_table.selectRow(row)
        
        # Call parent's method to update shared state and all tabs
        if hasattr(self.parent, '_fill_details_form'):
            self.parent._fill_details_form(row)
    
    def on_client_row_double_clicked(self, row, col):
        """Handle client row double-click - delegate to parent"""
        # Select the row visually
        self.clients_table.selectRow(row)
        
        # Call parent's method to update shared state and all tabs
        if hasattr(self.parent, '_fill_details_form'):
            self.parent._fill_details_form(row)
            self.parent.tab_widget.setCurrentIndex(1)
            # Switch to files tab after filling details
            self.parent.tab_widget.setCurrentIndex(2)
    
    def get_clients_data(self):
        """Get current clients data"""
        return self._clients_data
    
    def refresh_data(self):
        """Refresh clients data from database"""
        self.load_clients_data()
    
    def refresh_statistics(self):
        """Refresh only the statistics without reloading all data"""
        self.update_statistics()
    
    def select_client_by_name(self, client_name):
        """Select client by name after refresh"""
        for row in range(self.clients_table.rowCount()):
            item = self.clients_table.item(row, 0)  # Name column
            if item and item.text() == client_name:
                self.clients_table.selectRow(row)
                # Trigger the selection to update details
                if hasattr(self.parent, '_fill_details_form'):
                    self.parent._fill_details_form(row)
                break
