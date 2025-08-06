from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QComboBox, QLabel, QApplication, QToolTip, QDialog, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
import qtawesome as qta
import webbrowser
import csv
import os
from datetime import datetime

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
        
        # Payment controls
        self.payment_status_combo = None
        self.payment_method_combo = None
        
        # Action buttons
        self.upload_proof_btn = None
        self.sync_drive_btn = None
        self.export_csv_btn = None
        
        # Invoice helper reference (will be set after initialization)
        self._invoice_helper = None
    
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
        self.file_urls_table.setColumnCount(5)
        self.file_urls_table.setHorizontalHeaderLabels([
            "Filename", "Provider", "URL", "Note", "Actions"
        ])
        self.file_urls_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.file_urls_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_urls_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Set column widths
        header = self.file_urls_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Filename
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Provider
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # URL
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Note
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # Actions
        self.file_urls_table.setColumnWidth(4, 120)  # Fixed width for Actions column
        
        tab_layout.addWidget(self.file_urls_table)
        
        # Bottom controls row - payment controls and action buttons in one row
        bottom_controls_layout = QHBoxLayout()
        
        # Payment Status
        bottom_controls_layout.addWidget(QLabel("Payment Status:"))
        self.payment_status_combo = QComboBox()
        self.payment_status_combo.addItems(["Pending", "Paid"])
        self.payment_status_combo.setCurrentText("Pending")
        self.payment_status_combo.setMinimumWidth(100)
        bottom_controls_layout.addWidget(self.payment_status_combo)
        
        bottom_controls_layout.addSpacing(20)
        
        # Payment Method
        bottom_controls_layout.addWidget(QLabel("Payment Method:"))
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems([
            "GoPay", "DANA", "OVO", "LinkAja", "Bank Jago", 
            "BCA", "BRI", "PayPal", "QRIS"
        ])
        self.payment_method_combo.setCurrentText("GoPay")
        self.payment_method_combo.setMinimumWidth(120)
        bottom_controls_layout.addWidget(self.payment_method_combo)
        
        bottom_controls_layout.addStretch()
        
        # Action buttons
        # Upload Payment Proof button
        self.upload_proof_btn = QPushButton("Upload Payment Proof")
        self.upload_proof_btn.setIcon(qta.icon("fa6s.upload"))
        self.upload_proof_btn.setMinimumHeight(32)
        bottom_controls_layout.addWidget(self.upload_proof_btn)
        
        # Sync to Drive button
        self.sync_drive_btn = QPushButton("Sync to Drive")
        self.sync_drive_btn.setIcon(qta.icon("fa6b.google-drive"))
        self.sync_drive_btn.setMinimumHeight(32)
        bottom_controls_layout.addWidget(self.sync_drive_btn)
        
        # Export CSV button
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setIcon(qta.icon("fa6s.file-csv"))
        self.export_csv_btn.setMinimumHeight(32)
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        bottom_controls_layout.addWidget(self.export_csv_btn)
        
        tab_layout.addLayout(bottom_controls_layout)
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.link"), "File URLs")
        
        # Connect signals
        self.file_urls_search_edit.textChanged.connect(self.on_file_urls_search_changed)
        self.file_urls_sort_combo.currentTextChanged.connect(self.on_file_urls_sort_changed)
        self.file_urls_order_combo.currentTextChanged.connect(self.on_file_urls_sort_changed)
        self.file_urls_table.cellDoubleClicked.connect(self.on_file_urls_row_double_clicked)
        self.file_urls_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_urls_table.customContextMenuRequested.connect(self.show_file_urls_context_menu)
        
        # Connect invoice helper if available
        self._connect_invoice_helper()
        
        # Connect upload button
        if self.upload_proof_btn:
            self.upload_proof_btn.clicked.connect(self.upload_payment_proof)
    
    def upload_payment_proof(self):
        """Upload payment proof file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Select Payment Proof",
                "",
                "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;PDF Files (*.pdf);;All Files (*)"
            )
            
            if file_path:
                print(f"Payment proof selected: {file_path}")
                QMessageBox.information(
                    self.parent, 
                    "Upload Payment Proof", 
                    f"Payment proof file selected:\n{file_path}\n\nUpload functionality will be implemented later."
                )
            
        except Exception as e:
            print(f"Error selecting payment proof: {e}")
            QMessageBox.warning(self.parent, "Error", f"Failed to select payment proof: {str(e)}")
    
    def _connect_invoice_helper(self):
        """Connect sync button to invoice helper functionality"""
        try:
            # Get invoice helper from parent dialog
            if hasattr(self.parent, 'invoice_helper'):
                self._invoice_helper = self.parent.invoice_helper
                if self.sync_drive_btn and self._invoice_helper:
                    self.sync_drive_btn.clicked.connect(lambda: self._invoice_helper.sync_to_drive(self))
                    print("Sync to Drive button connected to invoice helper")
        except Exception as e:
            print(f"Error connecting invoice helper: {e}")
    
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
        
        # Filter data - data is tuple: (file_id, filename, provider_name, url_value, note, date, root, path, status_id, category_id, subcategory_id)
        if search_text:
            self._file_urls_data_filtered = [
                item for item in self._file_urls_data_all
                if (search_text in str(item[1]).lower() or  # filename
                    search_text in str(item[2]).lower() or  # provider_name
                    search_text in str(item[3]).lower() or  # url_value
                    search_text in str(item[4] or "").lower())  # note
            ]
        else:
            self._file_urls_data_filtered = list(self._file_urls_data_all)
        
        # Sort data
        sort_field = self.file_urls_sort_combo.currentText()
        sort_ascending = self.file_urls_order_combo.currentText() == "Ascending"
        
        field_map = {
            "Filename": 1,   # filename
            "Provider": 2,   # provider_name
            "URL": 3,        # url_value
            "Note": 4        # note
        }
        
        sort_index = field_map.get(sort_field, 1)
        self._file_urls_data_filtered.sort(
            key=lambda x: str(x[sort_index] or "").lower(),
            reverse=not sort_ascending
        )
        
        # Update table
        self.file_urls_table.setRowCount(len(self._file_urls_data_filtered))
        for row_idx, item in enumerate(self._file_urls_data_filtered):
            self.file_urls_table.setItem(row_idx, 0, QTableWidgetItem(str(item[1] or "")))  # filename
            self.file_urls_table.setItem(row_idx, 1, QTableWidgetItem(str(item[2] or "")))  # provider
            self.file_urls_table.setItem(row_idx, 2, QTableWidgetItem(str(item[3] or "")))  # url
            self.file_urls_table.setItem(row_idx, 3, QTableWidgetItem(str(item[4] or "")))  # note
            
            # Add action buttons widget
            self._create_action_buttons(row_idx, item)
    
    def _create_action_buttons(self, row_idx, item):
        """Create action buttons widget for a table row"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 2, 5, 2)
        actions_layout.setSpacing(2)
        
        # Edit button
        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa6s.pen-to-square"))
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip("Edit URL assignment")
        edit_btn.clicked.connect(lambda: self._edit_file_url(item))
        actions_layout.addWidget(edit_btn)
        
        # Copy URL button
        copy_btn = QPushButton()
        copy_btn.setIcon(qta.icon("fa6s.copy"))
        copy_btn.setFixedSize(28, 28)
        copy_btn.setToolTip("Copy URL to clipboard")
        copy_btn.clicked.connect(lambda: self._copy_url(item, copy_btn))
        actions_layout.addWidget(copy_btn)
        
        # Open URL button
        open_btn = QPushButton()
        open_btn.setIcon(qta.icon("fa6s.arrow-up-right-from-square"))
        open_btn.setFixedSize(28, 28)
        open_btn.setToolTip("Open URL in browser")
        open_btn.clicked.connect(lambda: self._open_url(item))
        actions_layout.addWidget(open_btn)
        
        actions_layout.addStretch()
        self.file_urls_table.setCellWidget(row_idx, 4, actions_widget)
    
    def _edit_file_url(self, item):
        """Edit URL assignment for the file"""
        try:
            file_id = item[0]
            filename = item[1]
            
            # Create file record dictionary similar to central widget format
            file_record = {
                "id": file_id,
                "name": filename,
                "date": item[5],
                "root": item[6], 
                "path": item[7],
                "status_id": item[8],
                "category_id": item[9],
                "subcategory_id": item[10]
            }
            
            # Import and show assign file URL dialog
            from gui.dialogs.assign_file_url_dialog import AssignFileUrlDialog
            
            # Get the actual database manager from the helper
            db_manager = self.db_helper.get_db_manager()
            
            dialog = AssignFileUrlDialog(file_record, db_manager, self.parent)
            if dialog.exec() == QDialog.Accepted:
                # Refresh the table
                self.load_file_urls_for_batch(self._selected_client_id, self._selected_batch_number, 
                                            self._client_name_label.text().replace("Client: ", ""))
                
        except Exception as e:
            print(f"Error editing file URL: {e}")
            QMessageBox.warning(self.parent, "Error", f"Failed to edit URL assignment: {str(e)}")
    
    def _copy_url(self, item, button):
        """Copy URL to clipboard"""
        try:
            url = item[3]  # url_value
            if url:
                QApplication.clipboard().setText(str(url))
                QToolTip.showText(QCursor.pos(), f"{url}\nCopied to clipboard", button)
            else:
                QToolTip.showText(QCursor.pos(), "No URL to copy", button)
        except Exception as e:
            print(f"Error copying URL: {e}")
    
    def _open_url(self, item):
        """Open URL in browser"""
        try:
            url = item[3]  # url_value
            if url:
                webbrowser.open(str(url))
            else:
                QMessageBox.information(self.parent, "Info", "No URL to open")
        except Exception as e:
            print(f"Error opening URL: {e}")
            QMessageBox.warning(self.parent, "Error", f"Failed to open URL: {str(e)}")
    
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
            filename = self._file_urls_data_filtered[row][1]  # second element is filename
            QApplication.clipboard().setText(filename)
        
        def copy_url():
            url = self._file_urls_data_filtered[row][3]  # fourth element is url
            QApplication.clipboard().setText(url)
        
        def open_url():
            url = self._file_urls_data_filtered[row][3]  # fourth element is url
            if url:
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
        file_name = file_data[1]  # second element is filename
        
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
    
    def export_to_csv(self):
        """Export file URLs data to CSV with detailed information"""
        if not self._selected_client_id or not self._selected_batch_number:
            QMessageBox.information(self.parent, "Export CSV", "No client or batch selected.")
            return
        
        try:
            # Get client name and batch number
            client_name = self._client_name_label.text().replace("Client: ", "")
            batch_number = self._selected_batch_number or "unknown"
            
            # Get ALL files in this batch with complete details using proper database helper
            all_files_data = self.db_helper.get_all_files_by_batch_and_client_with_details(
                batch_number, self._selected_client_id
            )
            
            if not all_files_data:
                QMessageBox.information(self.parent, "Export CSV", "No files found in this batch.")
                return
            
            # Extract root from first file if available
            root_folder = "unknown"
            if all_files_data:
                root_folder = all_files_data[0][3] or "unknown"  # root is at index 3
            
            # Generate filename: root_datetime_batch_totalfiles.csv
            current_datetime = datetime.now().strftime("%Y_%B_%d_%H%M%S")
            total_files = len(all_files_data)
            filename = f"{root_folder}_{current_datetime}_{batch_number}_{total_files}.csv"
            
            # Set initial directory to the root folder path if available
            initial_dir = ""
            if all_files_data and all_files_data[0][4]:  # path is at index 4
                full_path = all_files_data[0][4]
                # Extract the drive and root folder
                path_parts = full_path.replace('\\', '/').split('/')
                if len(path_parts) >= 2:
                    # Construct path like K:\SURYA_ALAN
                    initial_dir = f"{path_parts[0]}\\{path_parts[1]}"
            
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Export File URLs to CSV",
                os.path.join(initial_dir, filename),
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Prepare CSV data
            csv_data = []
            
            for i, item in enumerate(all_files_data, 1):
                file_id = item[0]
                filename = item[1] or ""
                date = item[2] or ""
                root = item[3] or ""
                path = item[4] or ""
                status_id = item[5]
                category_id = item[6]
                subcategory_id = item[7]
                category_name = item[8] or ""  # Already fetched from JOIN
                subcategory_name = item[9] or ""  # Already fetched from JOIN
                url_value = item[10] or ""  # URL from LEFT JOIN
                provider_name = item[11] or ""  # Provider name from LEFT JOIN
                price_value = item[12]  # Price from LEFT JOIN
                currency = item[13] or ""  # Currency from LEFT JOIN
                
                # Format price
                price = ""
                if price_value is not None:
                    # Format as integer if it's a whole number, otherwise keep decimal
                    if isinstance(price_value, (int, float)) and price_value == int(price_value):
                        price = str(int(price_value))
                    else:
                        price = str(price_value)
                
                # Add row to CSV data
                csv_data.append([
                    i,  # No
                    date,  # Date
                    filename,  # Filename
                    category_name,  # Category
                    subcategory_name,  # Subcategory
                    batch_number,  # Batch Number
                    url_value,  # URL
                    price  # Price
                ])
            
            # Write CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                
                # Write header
                writer.writerow([
                    "No", "Date", "Filename", "Category", "Subcategory", 
                    "Batch Number", "URL", "Price"
                ])
                
                # Write data
                writer.writerows(csv_data)
            
            QMessageBox.information(
                self.parent, 
                "Export Complete", 
                f"File URLs exported successfully to:\n{file_path}\n\nTotal records: {len(csv_data)}"
            )
            
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            QMessageBox.critical(self.parent, "Export Error", f"Failed to export CSV file:\n{str(e)}")
    
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
        
        # Reset payment controls
        if self.payment_status_combo:
            self.payment_status_combo.setCurrentText("Pending")
        if self.payment_method_combo:
            self.payment_method_combo.setCurrentText("GoPay")
    
    def get_payment_status(self):
        """Get current payment status"""
        if self.payment_status_combo:
            return self.payment_status_combo.currentText()
        return "Pending"
    
    def get_payment_method(self):
        """Get current payment method"""
        if self.payment_method_combo:
            return self.payment_method_combo.currentText()
        return "GoPay"
    
    def set_payment_status(self, status):
        """Set payment status"""
        if self.payment_status_combo and status in ["Pending", "Paid"]:
            self.payment_status_combo.setCurrentText(status)
    
    def set_payment_method(self, method):
        """Set payment method"""
        if self.payment_method_combo:
            methods = ["GoPay", "DANA", "OVO", "LinkAja", "Bank Jago", "BCA", "BRI", "PayPal", "QRIS"]
            if method in methods:
                self.payment_method_combo.setCurrentText(method)
