from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QDialog,
    QLabel, QScrollArea, QFrame, QComboBox, QSpacerItem, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
import qtawesome as qta

# BatchEditDialog will be imported when needed to avoid circular imports

class BatchFilesDetailDialog(QDialog):
    """Dialog to show files in a batch before batch update operations"""
    
    def __init__(self, parent, files_data, batch_number, client_name, operation_title="Batch Operation"):
        super().__init__(parent)
        self.files_data = files_data
        self.batch_number = batch_number
        self.client_name = client_name
        self.operation_title = operation_title
        
        self.setWindowTitle(f"{operation_title} - Batch {batch_number}")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header information
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        title_label = QLabel(f"<h3>{self.operation_title}</h3>")
        client_label = QLabel(f"<b>Client:</b> {self.client_name}")
        batch_label = QLabel(f"<b>Batch Number:</b> {self.batch_number}")
        count_label = QLabel(f"<b>Total Files:</b> {len(self.files_data)}")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(client_label)
        header_layout.addWidget(batch_label)
        header_layout.addWidget(count_label)
        layout.addWidget(header_frame)
        
        # Files table
        files_table = QTableWidget()
        files_table.setColumnCount(6)
        files_table.setHorizontalHeaderLabels([
            "File Name", "Date", "Root", "Current Status", "Category", "Subcategory"
        ])
        files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        files_table.setSelectionBehavior(QTableWidget.SelectRows)
        files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Populate table
        files_table.setRowCount(len(self.files_data))
        for row_idx, file_data in enumerate(self.files_data):
            files_table.setItem(row_idx, 0, QTableWidgetItem(file_data.get("name", "")))
            files_table.setItem(row_idx, 1, QTableWidgetItem(file_data.get("date", "")))
            files_table.setItem(row_idx, 2, QTableWidgetItem(file_data.get("root", "")))
            files_table.setItem(row_idx, 3, QTableWidgetItem(file_data.get("status_name", "")))
            files_table.setItem(row_idx, 4, QTableWidgetItem(file_data.get("category_name", "") or ""))
            files_table.setItem(row_idx, 5, QTableWidgetItem(file_data.get("subcategory_name", "") or ""))
        
        layout.addWidget(files_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton(f"Confirm {self.operation_title}")
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setDefault(True)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)

class ClientDataBatchHelper:
    """Helper class for Batch List tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper

        # Data storage
        self._batch_data_all = []
        self._batch_data_filtered = []
        self._selected_client_id = None

        # Sort settings
        self._batch_sort_field = "Created At"
        self._batch_sort_order = "Ascending"

        # Pagination
        self._batch_page = 1
        self._batch_rows_per_page = 20
        self._batch_total_pages = 1
    
    def get_finished_color_from_config(self):
        """Get the finished status color from window config"""
        try:
            # Get window config manager
            if hasattr(self.parent, 'db_helper'):
                config_manager = self.parent.db_helper.get_config_manager("window")
                finished_color = config_manager.get("status_options.Finished.color")
                return finished_color
            return "#43a047"  # Default green color
        except Exception as e:
            print(f"Error getting finished color from config: {e}")
            return "#43a047"  # Default green color
    
    def check_batch_all_finished(self, batch_number, client_id):
        """Check if all files in a batch have 'Finished' status"""
        try:
            # Get all files in this batch
            files_data = self.db_helper.get_files_by_batch_and_client(batch_number, client_id)
            
            if not files_data:
                return False  # No files means not finished
            
            # Check if all files have "Finished" status
            for file_data in files_data:
                if file_data.get("status_name", "").lower() != "finished":
                    return False
            
            return True  # All files are finished
        except Exception as e:
            print(f"Error checking batch finished status: {e}")
            return False
    
    def init_batch_list_tab(self, tab_widget):
        """Initialize the batch list tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # Search and action buttons row
        row = QHBoxLayout()
        self.batch_search_edit = QLineEdit()
        self.batch_search_edit.setPlaceholderText("Search batch number or note...")
        self.batch_search_edit.setMinimumHeight(32)
        self.batch_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.batch_search_edit, 1)
        
        # Sort controls
        self.batch_sort_combo = QComboBox()
        self.batch_sort_combo.addItems(["Client Name", "Batch Number", "Note", "File Count", "Created At"])
        self.batch_sort_combo.setCurrentText(self._batch_sort_field)
        self.batch_sort_order_combo = QComboBox()
        self.batch_sort_order_combo.addItems(["Ascending", "Descending"])
        self.batch_sort_order_combo.setCurrentText(self._batch_sort_order)
        row.addWidget(QLabel("Sort by:"))
        row.addWidget(self.batch_sort_combo)
        row.addWidget(self.batch_sort_order_combo)
        row.addStretch()
        
        # Action buttons
        self.batch_refresh_btn = QPushButton(qta.icon("fa6s.arrows-rotate"), "Refresh")
        self.batch_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Batch")
        self.batch_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Batch")
        self.batch_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Batch")
        row.addWidget(self.batch_refresh_btn)
        row.addWidget(self.batch_add_btn)
        row.addWidget(self.batch_edit_btn)
        row.addWidget(self.batch_delete_btn)
        tab_layout.addLayout(row)
        
        # Batch table
        self.batch_table = QTableWidget(tab)
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels([
            "Client Name", "Batch Number", "Note", "File Count", "Created At"
        ])
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setSelectionMode(QTableWidget.SingleSelection)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.batch_table)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.batch_prev_btn = QPushButton("Previous")
        self.batch_next_btn = QPushButton("Next")
        self.batch_page_label = QLabel("Page 1/1")
        self.batch_page_spinner = QSpinBox()
        self.batch_page_spinner.setMinimum(1)
        self.batch_page_spinner.setMaximum(1)
        self.batch_page_spinner.setValue(1)
        self.batch_page_spinner.setFixedWidth(60)
        self.batch_rows_per_page_combo = QComboBox()
        self.batch_rows_per_page_combo.addItems(["10", "20", "50", "100"])
        self.batch_rows_per_page_combo.setCurrentText(str(self._batch_rows_per_page))
        pagination_layout.addWidget(self.batch_prev_btn)
        pagination_layout.addWidget(self.batch_next_btn)
        pagination_layout.addWidget(QLabel("Page:"))
        pagination_layout.addWidget(self.batch_page_spinner)
        pagination_layout.addWidget(self.batch_page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(QLabel("Rows per page:"))
        pagination_layout.addWidget(self.batch_rows_per_page_combo)
        tab_layout.addLayout(pagination_layout)

        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.layer-group"), "Batch List")
        
        # Connect signals
        self.batch_refresh_btn.clicked.connect(self.on_batch_refresh)
        self.batch_add_btn.clicked.connect(self.on_batch_add)
        self.batch_edit_btn.clicked.connect(self.on_batch_edit)
        self.batch_delete_btn.clicked.connect(self.on_batch_delete)
        self.batch_table.cellDoubleClicked.connect(self.on_batch_row_double_clicked)
        self.batch_table.cellClicked.connect(self.on_batch_row_clicked)
        self.batch_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.batch_table.customContextMenuRequested.connect(self.show_batch_context_menu)
        self.batch_search_edit.textChanged.connect(self.on_batch_search_changed)
        self.batch_sort_combo.currentIndexChanged.connect(self.on_batch_sort_changed)
        self.batch_sort_order_combo.currentIndexChanged.connect(self.on_batch_sort_changed)
        self.batch_prev_btn.clicked.connect(self.on_batch_prev_page)
        self.batch_next_btn.clicked.connect(self.on_batch_next_page)
        self.batch_rows_per_page_combo.currentIndexChanged.connect(self.on_batch_rows_per_page_changed)
        self.batch_page_spinner.valueChanged.connect(self.on_batch_page_spinner_changed)

        # Load all batch list by default (no client selected)
        self.load_batch_list_for_client(None)
    
    def show_batch_context_menu(self, pos):
        """Show context menu for batch table"""
        index = self.batch_table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        menu = QMenu(self.batch_table)
        icon_edit = qta.icon("fa6s.pen-to-square")
        icon_delete = qta.icon("fa6s.trash")
        icon_finished = qta.icon("fa6s.circle-check")
        icon_refresh = qta.icon("fa6s.arrows-rotate")

        action_edit = QAction(icon_edit, "Edit Batch", self.parent)
        action_delete = QAction(icon_delete, "Delete Batch", self.parent)
        action_mark_finished = QAction(icon_finished, "Mark as Finished", self.parent)
        action_refresh = QAction(icon_refresh, "Refresh", self.parent)

        def do_edit():
            self.batch_table.selectRow(row)
            self.on_batch_edit()

        def do_delete():
            self.batch_table.selectRow(row)
            self.on_batch_delete()

        def do_mark_finished():
            self.batch_table.selectRow(row)
            self.on_batch_mark_finished(row)

        def do_refresh():
            self.on_batch_refresh()

        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        action_mark_finished.triggered.connect(do_mark_finished)
        action_refresh.triggered.connect(do_refresh)

        menu.addAction(action_edit)
        menu.addAction(action_mark_finished)
        menu.addSeparator()
        menu.addAction(action_refresh)
        menu.addAction(action_delete)
        menu.exec(self.batch_table.viewport().mapToGlobal(pos))
    
    def load_batch_list_for_client(self, client_id):
        """Load batch list for selected client, or all if client_id is None"""
        self._selected_client_id = client_id
        batch_data = []
        if client_id is not None:
            batch_rows = self.db_helper.get_batch_numbers_by_client(client_id)
            for batch_row in batch_rows:
                # batch_row: (batch_number, note, created_at)
                batch_number, note, created_at = batch_row
                file_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
                client_name = self.db_helper.get_client_name_by_id(client_id)
                batch_data.append((client_name, batch_number, note, file_count, created_at, client_id))
        else:
            # Load all batch numbers from all clients
            batch_rows = self.db_helper.get_all_batch_numbers()
            for batch_row in batch_rows:
                # batch_row: (batch_number, client_id, note, created_at)
                batch_number, client_id_row, note, created_at = batch_row
                file_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
                client_name = self.db_helper.get_client_name_by_id(client_id_row)
                batch_data.append((client_name, batch_number, note, file_count, created_at, client_id_row))
        self._batch_data_all = batch_data
        self._batch_page = 1
        self.update_batch_table()
    
    def on_batch_refresh(self):
        """Handle refresh button click - reload batch data"""
        # If a client is selected, show only that client's batches; otherwise show all
        self.load_batch_list_for_client(self._selected_client_id)
    
    def on_batch_search_changed(self):
        """Handle batch search text change"""
        self._batch_page = 1
        self.update_batch_table()
    
    def on_batch_sort_changed(self):
        """Handle sort change"""
        self._batch_sort_field = self.batch_sort_combo.currentText()
        self._batch_sort_order = self.batch_sort_order_combo.currentText()
        self._batch_page = 1
        self.update_batch_table()
    
    def on_batch_prev_page(self):
        """Handle previous page button click"""
        if self._batch_page > 1:
            self._batch_page -= 1
            self.update_batch_table()
    
    def on_batch_next_page(self):
        """Handle next page button click"""
        if self._batch_page < self._batch_total_pages:
            self._batch_page += 1
            self.update_batch_table()
    
    def on_batch_rows_per_page_changed(self):
        """Handle rows per page combo box change"""
        self._batch_rows_per_page = int(self.batch_rows_per_page_combo.currentText())
        self._batch_page = 1
        self.update_batch_table()
    
    def on_batch_page_spinner_changed(self, value):
        """Handle page spinner value change"""
        if value != self._batch_page:
            self._batch_page = value
            self.update_batch_table()
    
    def update_batch_table(self):
        """Update the batch table with filtered and sorted data"""
        search_text = self.batch_search_edit.text().strip().lower()
        
        # Apply search filter
        if search_text:
            self._batch_data_filtered = [
                (client_name, batch_number, note, file_count, created_at, client_id)
                for client_name, batch_number, note, file_count, created_at, client_id in self._batch_data_all
                if search_text in str(client_name).lower()
                or search_text in str(batch_number).lower()
                or search_text in str(note).lower()
            ]
        else:
            self._batch_data_filtered = list(self._batch_data_all)
        
        # Apply sorting
        self._apply_batch_sorting()
        
        total_rows = len(self._batch_data_filtered)
        rows_per_page = self._batch_rows_per_page
        self._batch_total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
        if self._batch_page > self._batch_total_pages:
            self._batch_page = self._batch_total_pages

        start_idx = (self._batch_page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        page_data = self._batch_data_filtered[start_idx:end_idx]

        # Get finished color from config
        finished_color = self.get_finished_color_from_config()
        
        self.batch_table.setRowCount(len(page_data))
        for row_idx, (client_name, batch_number, note, file_count, created_at, client_id_row) in enumerate(page_data):
            client_item = QTableWidgetItem(str(client_name))
            batch_item = QTableWidgetItem(str(batch_number))
            note_item = QTableWidgetItem(str(note))
            count_item = QTableWidgetItem(str(file_count))
            created_item = QTableWidgetItem(str(created_at) if created_at else "")
            
            highlight_client_id = self._selected_client_id if self._selected_client_id else client_id_row
            if highlight_client_id and self.check_batch_all_finished(batch_number, highlight_client_id):
                green_color = QColor(finished_color)
                green_color.setAlpha(80)
                client_item.setBackground(green_color)
                batch_item.setBackground(green_color)
                note_item.setBackground(green_color)
                count_item.setBackground(green_color)
                created_item.setBackground(green_color)
            
            self.batch_table.setItem(row_idx, 0, client_item)
            self.batch_table.setItem(row_idx, 1, batch_item)
            self.batch_table.setItem(row_idx, 2, note_item)
            self.batch_table.setItem(row_idx, 3, count_item)
            self.batch_table.setItem(row_idx, 4, created_item)

        self.batch_page_label.setText(f"Page {self._batch_page}/{self._batch_total_pages}")
        self.batch_prev_btn.setEnabled(self._batch_page > 1)
        self.batch_next_btn.setEnabled(self._batch_page < self._batch_total_pages)
        self.batch_page_spinner.blockSignals(True)
        self.batch_page_spinner.setMaximum(self._batch_total_pages)
        self.batch_page_spinner.setValue(self._batch_page)
        self.batch_page_spinner.blockSignals(False)

    def _apply_batch_sorting(self):
        """Apply sorting to filtered batch data"""
        if not self._batch_data_filtered:
            return
        
        reverse = self._batch_sort_order == "Descending"
        field = self._batch_sort_field

        if field == "Client Name":
            self._batch_data_filtered.sort(
                key=lambda item: str(item[0]).lower(),
                reverse=reverse
            )
        elif field == "Batch Number":
            def sort_key(item):
                batch_number = item[1]
                try:
                    return (0, int(batch_number))
                except (ValueError, TypeError):
                    return (1, str(batch_number).lower())
            self._batch_data_filtered.sort(key=sort_key, reverse=reverse)
        elif field == "Note":
            self._batch_data_filtered.sort(
                key=lambda item: str(item[2]).lower(), 
                reverse=reverse
            )
        elif field == "File Count":
            self._batch_data_filtered.sort(
                key=lambda item: int(item[3]) if item[3] else 0, 
                reverse=reverse
            )
        elif field == "Created At":
            self._batch_data_filtered.sort(
                key=lambda item: item[4] if item[4] else "", 
                reverse=reverse
            )
    
    def on_batch_add(self):
        """Handle add batch button click"""
        if not self._selected_client_id:
            QMessageBox.warning(self.parent, "No Client Selected", "Please select a client first.")
            return
        
        # Import the dialog to avoid circular imports
        from ..client_data_dialog import BatchEditDialog
        
        dialog = BatchEditDialog(parent=self.parent, client_id=self._selected_client_id, show_client_combo=False)
        if dialog.exec() == QDialog.Accepted:
            batch_number, note, _ = dialog.get_values()
            if not batch_number:
                QMessageBox.warning(self.parent, "Validation Error", "Batch Number cannot be empty.")
                return
            
            try:
                self.db_helper.add_batch_number(batch_number, note, self._selected_client_id)
                self.load_batch_list_for_client(self._selected_client_id)
                QMessageBox.information(self.parent, "Success", "Batch added successfully.")
            except Exception as e:
                QMessageBox.warning(self.parent, "Error", str(e))
    
    def on_batch_edit(self, *args):
        """Handle edit batch button click"""
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self.parent, "No Batch Selected", "Please select a batch to edit.")
            return

        batch_number = self.batch_table.item(row, 1).text()
        note = self.batch_table.item(row, 2).text()

        from ..client_data_dialog import BatchEditDialog

        dialog = BatchEditDialog(
            batch_number, note, self._selected_client_id, None,
            parent=self.parent, show_client_combo=False
        )

        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            new_batch_number, new_note, client_id = values[:3]
            # Ensure client_id is always set
            if not client_id:
                client_id = self._selected_client_id
            if not new_batch_number:
                QMessageBox.warning(self.parent, "Input Error", "Batch number cannot be empty.")
                return

            try:
                if new_batch_number != batch_number:
                    self.db_helper.update_batch_number_and_note_and_client(
                        batch_number, new_batch_number, new_note, client_id
                    )
                else:
                    self.db_helper.update_batch_list_note_and_client(
                        batch_number, new_note, client_id
                    )

                self.load_batch_list_for_client(self._selected_client_id)
                QMessageBox.information(self.parent, "Success", "Batch updated successfully.")
            except Exception as e:
                QMessageBox.warning(self.parent, "Error", str(e))
    
    def on_batch_delete(self):
        """Handle delete batch button click"""
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self.parent, "No Batch Selected", "Please select a batch to delete.")
            return
        
        batch_number = self.batch_table.item(row, 1).text()
        affected_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
        
        # First confirmation
        msg1 = (
            f"Deleting batch number '{batch_number}' will also delete {affected_count} related record(s) in File Client Batch records.\n"
            "This will affect all files/projects using this batch number.\n\n"
            "Do you want to continue?"
        )
        reply1 = QMessageBox.warning(self.parent, "Delete Batch", msg1, QMessageBox.Yes | QMessageBox.No)
        if reply1 != QMessageBox.Yes:
            return
        
        # Second confirmation
        msg2 = (
            f"Are you sure you want to permanently delete batch number '{batch_number}'?\n"
            "This action cannot be undone."
        )
        reply2 = QMessageBox.warning(self.parent, "Are you sure?", msg2, QMessageBox.Yes | QMessageBox.No)
        if reply2 != QMessageBox.Yes:
            return
        
        try:
            self.db_helper.delete_batch_and_file_client_batch(batch_number)
            self.load_batch_list_for_client(self._selected_client_id)
            QMessageBox.information(self.parent, "Success", "Batch deleted successfully.")
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", str(e))
    
    def clear_batch_tab(self):
        """Clear the batch tab"""
        self.batch_table.setRowCount(0)
        self._batch_data_all = []
        self._batch_data_filtered = []
        self._selected_client_id = None
        self._batch_page = 1
        self.update_batch_table()
        # After clearing, reload all batch list
        self.load_batch_list_for_client(None)
    
    def on_batch_row_clicked(self, row, col):
        """Handle batch row click - load file URLs for selected batch"""
        actual_row = (self._batch_page - 1) * self._batch_rows_per_page + row
        if actual_row >= len(self._batch_data_filtered):
            return

        client_name = self._batch_data_filtered[actual_row][0]
        batch_number = self._batch_data_filtered[actual_row][1]
        client_id = self._batch_data_filtered[actual_row][5]
        if self._selected_client_id is None:
            selected_client_id = client_id
        else:
            selected_client_id = self._selected_client_id

        if hasattr(self.parent, '_load_file_urls_for_batch'):
            self.parent._load_file_urls_for_batch(selected_client_id, batch_number, client_name)

    def on_batch_row_double_clicked(self, row, col):
        """Handle batch row double click - switch to File URLs tab"""
        actual_row = (self._batch_page - 1) * self._batch_rows_per_page + row
        if actual_row >= len(self._batch_data_filtered):
            return

        client_name = self._batch_data_filtered[actual_row][0]
        batch_number = self._batch_data_filtered[actual_row][1]
        client_id = self._batch_data_filtered[actual_row][5]
        if self._selected_client_id is None:
            selected_client_id = client_id
        else:
            selected_client_id = self._selected_client_id

        if hasattr(self.parent, '_load_file_urls_for_batch'):
            self.parent._load_file_urls_for_batch(selected_client_id, batch_number, client_name)

        if hasattr(self.parent, 'tab_widget'):
            for i in range(self.parent.tab_widget.count()):
                tab_text = self.parent.tab_widget.tabText(i)
                if "File URLs" in tab_text:
                    self.parent.tab_widget.setCurrentIndex(i)
                    break

    def on_batch_mark_finished(self, row):
        """Handle mark as finished for all files in batch"""
        actual_row = (self._batch_page - 1) * self._batch_rows_per_page + row
        if actual_row >= len(self._batch_data_filtered):
            return

        batch_number = self._batch_data_filtered[actual_row][1]
        client_name = self.parent._selected_client_name

        try:
            files_data = self.db_helper.get_files_by_batch_and_client(batch_number, self._selected_client_id)
            if not files_data:
                QMessageBox.information(self.parent, "No Files", f"No files found in batch '{batch_number}'.")
                return

            dialog = BatchFilesDetailDialog(
                parent=self.parent,
                files_data=files_data,
                batch_number=batch_number,
                client_name=client_name,
                operation_title="Mark as Finished"
            )

            if dialog.exec() != QDialog.Accepted:
                return

            finished_status_id = self.db_helper.get_status_id("Finished")
            if not finished_status_id:
                QMessageBox.warning(self.parent, "Status Not Found", 
                                   "Could not find 'Finished' status in database. Please ensure the status exists.")
                return

            updated_count = self.db_helper.update_files_status_by_batch(
                batch_number, self._selected_client_id, finished_status_id
            )

            # Update batch note to 'Finished'
            self.db_helper.mark_batch_note_finished(batch_number)

            # Refresh batch list to show updated data
            self.load_batch_list_for_client(self._selected_client_id)

            if updated_count > 0:
                QMessageBox.information(
                    self.parent, 
                    "Success", 
                    f"Successfully marked {updated_count} files as 'Finished' in batch '{batch_number}'."
                )

                if (hasattr(self.parent, 'file_urls_helper') and 
                    hasattr(self.parent.file_urls_helper, '_selected_batch_number') and
                    self.parent.file_urls_helper._selected_batch_number == batch_number):

                    self.parent.file_urls_helper.load_file_urls_for_batch(
                        self._selected_client_id, batch_number, client_name
                    )

                if (hasattr(self.parent, 'files_helper') and 
                    hasattr(self.parent.files_helper, '_selected_client_id') and
                    self.parent.files_helper._selected_client_id == self._selected_client_id):

                    if hasattr(self.parent.files_helper, 'fetch_files_page_and_summary'):
                        self.parent.files_helper.fetch_files_page_and_summary()

                self.update_batch_table()
            else:
                QMessageBox.information(self.parent, "No Updates", "No files were updated.")
                
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"An error occurred while marking files as finished:\n{str(e)}")
            print(f"Error in on_batch_mark_finished: {e}")
            print(f"Error in on_batch_mark_finished: {e}")
