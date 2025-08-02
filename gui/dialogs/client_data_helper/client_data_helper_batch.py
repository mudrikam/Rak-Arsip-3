from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
import qtawesome as qta

# BatchEditDialog will be imported when needed to avoid circular imports

class ClientDataBatchHelper:
    """Helper class for Batch List tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # Data storage
        self._batch_data_all = []
        self._batch_data_filtered = []
        self._selected_client_id = None
    
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
        row.addStretch()
        
        # Action buttons
        self.batch_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Batch")
        self.batch_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Batch")
        self.batch_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Batch")
        row.addWidget(self.batch_add_btn)
        row.addWidget(self.batch_edit_btn)
        row.addWidget(self.batch_delete_btn)
        tab_layout.addLayout(row)
        
        # Batch table
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
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.layer-group"), "Batch List")
        
        # Connect signals
        self.batch_add_btn.clicked.connect(self.on_batch_add)
        self.batch_edit_btn.clicked.connect(self.on_batch_edit)
        self.batch_delete_btn.clicked.connect(self.on_batch_delete)
        self.batch_table.cellDoubleClicked.connect(self.on_batch_edit)
        self.batch_table.cellClicked.connect(self.on_batch_row_clicked)
        self.batch_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.batch_table.customContextMenuRequested.connect(self.show_batch_context_menu)
        self.batch_search_edit.textChanged.connect(self.on_batch_search_changed)
    
    def show_batch_context_menu(self, pos):
        """Show context menu for batch table"""
        index = self.batch_table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        menu = QMenu(self.batch_table)
        icon_edit = qta.icon("fa6s.pen-to-square")
        icon_delete = qta.icon("fa6s.trash")
        
        action_edit = QAction(icon_edit, "Edit Batch", self.parent)
        action_delete = QAction(icon_delete, "Delete Batch", self.parent)
        
        def do_edit():
            self.batch_table.selectRow(row)
            self.on_batch_edit()
        
        def do_delete():
            self.batch_table.selectRow(row)
            self.on_batch_delete()
        
        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.exec(self.batch_table.viewport().mapToGlobal(pos))
    
    def load_batch_list_for_client(self, client_id):
        """Load batch list for selected client"""
        self._selected_client_id = client_id
        batch_numbers = self.db_helper.get_batch_numbers_by_client(client_id)
        batch_data = []
        
        for batch_number in batch_numbers:
            note, _ = self.db_helper.get_batch_list_note_and_client(batch_number)
            file_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
            batch_data.append((batch_number, note, file_count))
        
        self._batch_data_all = batch_data
        self.update_batch_table()
    
    def on_batch_search_changed(self):
        """Handle batch search text change"""
        self.update_batch_table()
    
    def update_batch_table(self):
        """Update the batch table with filtered data"""
        search_text = self.batch_search_edit.text().strip().lower()
        
        if search_text:
            self._batch_data_filtered = [
                (batch_number, note, file_count)
                for batch_number, note, file_count in self._batch_data_all
                if search_text in str(batch_number).lower() or search_text in str(note).lower()
            ]
        else:
            self._batch_data_filtered = list(self._batch_data_all)
        
        self.batch_table.setRowCount(len(self._batch_data_filtered))
        for row_idx, (batch_number, note, file_count) in enumerate(self._batch_data_filtered):
            self.batch_table.setItem(row_idx, 0, QTableWidgetItem(str(batch_number)))
            self.batch_table.setItem(row_idx, 1, QTableWidgetItem(str(note)))
            self.batch_table.setItem(row_idx, 2, QTableWidgetItem(str(file_count)))
    
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
        
        # Get data from filtered list
        batch_number = self.batch_table.item(row, 0).text()
        note = self.batch_table.item(row, 1).text()
        
        # Import the dialog to avoid circular imports
        from ..client_data_dialog import BatchEditDialog
        
        dialog = BatchEditDialog(
            batch_number, note, self._selected_client_id, None, 
            parent=self.parent, show_client_combo=False
        )
        
        if dialog.exec() == QDialog.Accepted:
            new_batch_number, new_note, client_id = dialog.get_values()
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
        
        batch_number = self.batch_table.item(row, 0).text()
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
    
    def on_batch_row_clicked(self, row, col):
        """Handle batch row click - load file URLs for selected batch"""
        if row >= len(self._batch_data_filtered):
            return
        
        batch_number = self._batch_data_filtered[row][0]
        client_name = self.parent._selected_client_name
        
        # Load file URLs for this batch
        if hasattr(self.parent, '_load_file_urls_for_batch'):
            self.parent._load_file_urls_for_batch(self._selected_client_id, batch_number, client_name)
