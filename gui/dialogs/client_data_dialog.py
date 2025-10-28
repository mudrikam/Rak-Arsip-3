from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QFormLayout, QLineEdit, QMessageBox, QComboBox, QDialogButtonBox, QMainWindow, QDateTimeEdit
)
from PySide6.QtCore import Qt, QPoint, QDateTime
import qtawesome as qta

# Import helper classes
from .client_data_helper.client_data_helper_database import ClientDataDatabaseHelper
from .client_data_helper.client_data_helper_clients import ClientDataClientsHelper
from .client_data_helper.client_data_helper_details import ClientDataDetailsHelper
from .client_data_helper.client_data_helper_files import ClientDataFilesHelper
from .client_data_helper.client_data_helper_batch import ClientDataBatchHelper
from .client_data_helper.client_data_helper_file_urls import ClientDataFileUrlsHelper
from .client_data_helper.client_data_invoice_helper import ClientDataInvoiceHelper

class BatchEditDialog(QDialog):
    """Dialog for editing batch information"""
    def __init__(self, batch_number="", note="", client_id=None, clients=None, parent=None, show_client_combo=False, created_at=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Batch List" if not show_client_combo else "Add Batch List")
        self.setMinimumWidth(350)
        layout = QFormLayout(self)

        self.client_combo = None
        self._client_id = client_id
        self._show_client_combo = show_client_combo

        if show_client_combo and clients:
            self.client_combo = QComboBox(self)
            for c in clients:
                self.client_combo.addItem(c["client_name"], c["id"])
            if client_id:
                idx = self.client_combo.findData(client_id)
                if idx >= 0:
                    self.client_combo.setCurrentIndex(idx)
            layout.addRow("Assign Batch to Client:", self.client_combo)

        self.batch_number_edit = QLineEdit(batch_number)
        layout.addRow("Batch Number:", self.batch_number_edit)

        self.created_at_edit = QDateTimeEdit(self)
        self.created_at_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.created_at_edit.setCalendarPopup(True)
        if created_at:
            if isinstance(created_at, str):
                dt = QDateTime.fromString(created_at, "yyyy-MM-dd HH:mm:ss")
                if not dt.isValid():
                    dt = QDateTime.currentDateTime()
            elif isinstance(created_at, QDateTime):
                dt = created_at
            else:
                dt = QDateTime.currentDateTime()
            self.created_at_edit.setDateTime(dt)
        else:
            self.created_at_edit.setDateTime(QDateTime.currentDateTime())
        layout.addRow("Created At:", self.created_at_edit)

        # Note ComboBox with editable option
        self.note_combo = QComboBox(self)
        self.note_combo.setEditable(True)
        # Add predefined note options with color coding
        note_options = ["", "Finished", "Hold", "In Progress", "Review", "Urgent", "Low Priority"]
        self.note_combo.addItems(note_options)
        
        # Set current note value
        if note:
            # Check if note exists in options
            index = self.note_combo.findText(note)
            if index >= 0:
                self.note_combo.setCurrentIndex(index)
            else:
                # If note is custom, add it and select it
                self.note_combo.addItem(note)
                self.note_combo.setCurrentText(note)
        
        layout.addRow("Note:", self.note_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_values(self):
        created_at_str = self.created_at_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        if self._show_client_combo and self.client_combo:
            return (
                self.batch_number_edit.text().strip(),
                self.note_combo.currentText().strip(),
                self.client_combo.currentData(),
                created_at_str
            )
        else:
            return (
                self.batch_number_edit.text().strip(),
                self.note_combo.currentText().strip(),
                self._client_id,
                created_at_str
            )

def find_main_window(widget):
    """Find the main window from any widget"""
    parent = widget
    while parent is not None:
        if isinstance(parent, QMainWindow):
            return parent
        parent = parent.parent()
    return widget.window()

class ClientDataDialog(QDialog):
    """Optimized Client Data Dialog using helper classes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Data")
        self.setMinimumSize(800, 500)
        
        # Main layout
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)
        
        # Initialize helpers
        self.db_helper = ClientDataDatabaseHelper(self)
        self.clients_helper = ClientDataClientsHelper(self, self.db_helper)
        self.details_helper = ClientDataDetailsHelper(self, self.db_helper)
        self.files_helper = ClientDataFilesHelper(self, self.db_helper)
        self.batch_helper = ClientDataBatchHelper(self, self.db_helper)
        self.file_urls_helper = ClientDataFileUrlsHelper(self, self.db_helper)
        self.invoice_helper = ClientDataInvoiceHelper(self, self.db_helper)
        
        # Shared state variables
        self._selected_client_name = ""
        self._selected_client_id = None
        
        # Initialize all tabs
        self._init_all_tabs()
    
    def _init_all_tabs(self):
        """Initialize all tabs using helpers"""
        self.clients_helper.init_clients_tab(self.tab_widget)
        self.details_helper.init_details_tab(self.tab_widget)
        self.files_helper.init_files_tab(self.tab_widget)
        self.batch_helper.init_batch_list_tab(self.tab_widget)
        self.file_urls_helper.init_file_urls_tab(self.tab_widget)
    
    # Legacy method compatibility - delegate to helpers
    def _load_clients_data(self):
        """Load clients data - delegates to clients helper"""
        self.clients_helper.load_clients_data()
    
    def _update_clients_table(self):
        """Update clients table - delegates to clients helper"""
        self.clients_helper.update_clients_table()
    
    def _on_clients_sort_changed(self):
        """Handle clients sort change - delegates to clients helper"""
        self.clients_helper.on_clients_sort_changed()
    
    def _on_clients_search_changed(self):
        """Handle clients search change - delegates to clients helper"""
        self.clients_helper.on_clients_search_changed()
    
    def _fill_details_form(self, row):
        """Fill details form - delegates to details helper"""
        clients_data = self.clients_helper.get_clients_data()
        self.details_helper.fill_details_form(row, clients_data)
        
        # Update shared state
        if 0 <= row < len(clients_data):
            client = clients_data[row]
            self._selected_client_name = client.get("client_name", "")
            self._selected_client_id = client.get("id", None)
            
            # Load related data
            self.files_helper.load_files_for_client(client["id"], client.get("client_name", ""))
            self.batch_helper.load_batch_list_for_client(client["id"])
            
            # Clear file URLs tab when client changes
            self.file_urls_helper.clear_file_urls_tab()
    
    def _copy_detail_to_clipboard(self, key, btn=None):
        """Copy detail to clipboard - delegates to details helper"""
        self.details_helper.copy_detail_to_clipboard(key, btn)
    
    def _populate_links_table(self, links_str):
        """Populate links table - delegates to details helper"""
        self.details_helper.populate_links_table(links_str)
    
    def _get_links_list(self):
        """Get links list - delegates to details helper"""
        return self.details_helper.get_links_list()
    
    def _add_link(self):
        """Add link - delegates to details helper"""
        self.details_helper.add_link()
    
    def _edit_link(self, idx):
        """Edit link - delegates to details helper"""
        self.details_helper.edit_link(idx)
    
    def _delete_link(self, idx):
        """Delete link - delegates to details helper"""
        self.details_helper.delete_link(idx)
    
    def _on_link_table_cell_clicked(self, row, col):
        """Handle link table cell click - delegates to details helper"""
        self.details_helper.on_link_table_cell_clicked(row, col)
    
    def _add_client_mode(self):
        """Switch to add client mode - delegates to details helper"""
        self.details_helper.add_client_mode()
    
    def _save_client_details(self):
        """Save client details - delegates to details helper"""
        self.details_helper.save_client_details()
    
    def _load_files_for_client(self, client_id):
        """Load files for client - delegates to files helper"""
        client_name = self._selected_client_name
        self.files_helper.load_files_for_client(client_id, client_name)
    
    def _refresh_batch_filter_combo(self):
        """Refresh batch filter combo - delegates to files helper"""
        self.files_helper.refresh_batch_filter_combo()
    
    def _on_files_batch_filter_changed(self, idx):
        """Handle files batch filter change - delegates to files helper"""
        self.files_helper.on_files_batch_filter_changed(idx)
    
    def _on_files_search_changed(self):
        """Handle files search change - delegates to files helper"""
        self.files_helper.on_files_search_changed()
    
    def _on_files_sort_changed(self):
        """Handle files sort change - delegates to files helper"""
        self.files_helper.on_files_sort_changed()
    
    def _files_prev_page(self):
        """Go to previous files page - delegates to files helper"""
        self.files_helper.files_prev_page()
    
    def _files_next_page(self):
        """Go to next files page - delegates to files helper"""
        self.files_helper.files_next_page()
    
    def _files_goto_page(self, value):
        """Go to specific files page - delegates to files helper"""
        self.files_helper.files_goto_page(value)
    
    def _get_global_file_index(self, row_in_page):
        """Get global file index - delegates to files helper"""
        return self.files_helper.get_global_file_index(row_in_page)
    
    def _fetch_files_page_and_summary(self):
        """Fetch files page and summary - delegates to files helper"""
        self.files_helper.fetch_files_page_and_summary()
    
    def _update_files_table(self):
        """Update files table - delegates to files helper"""
        self.files_helper.update_files_table()
    
    def _show_files_context_menu(self, pos):
        """Show files context menu - delegates to files helper"""
        self.files_helper.show_files_context_menu(pos)
    
    def _files_copy_name_shortcut(self):
        """Copy file name shortcut - delegates to files helper"""
        self.files_helper.files_copy_name_shortcut()
    
    def _files_copy_path_shortcut(self):
        """Copy file path shortcut - delegates to files helper"""
        self.files_helper.files_copy_path_shortcut()
    
    def _files_open_explorer_shortcut(self):
        """Open file in explorer shortcut - delegates to files helper"""
        self.files_helper.files_open_explorer_shortcut()
    
    def _on_files_row_double_clicked(self, row_in_page, col):
        """Handle files row double click - delegates to files helper"""
        self.files_helper.on_files_row_double_clicked(row_in_page, col)
    
    def _load_batch_list_for_client(self, client_id):
        """Load batch list for client - delegates to batch helper"""
        self.batch_helper.load_batch_list_for_client(client_id)
    
    def _on_batch_search_changed(self):
        """Handle batch search change - delegates to batch helper"""
        self.batch_helper.on_batch_search_changed()
    
    def _update_batch_table(self):
        """Update batch table - delegates to batch helper"""
        self.batch_helper.update_batch_table()
    
    def _show_batch_context_menu(self, pos):
        """Show batch context menu - delegates to batch helper"""
        self.batch_helper.show_batch_context_menu(pos)
    
    def _on_batch_add(self):
        """Handle batch add - delegates to batch helper"""
        self.batch_helper.on_batch_add()
    
    def _on_batch_edit(self, *args):
        """Handle batch edit - delegates to batch helper"""
        self.batch_helper.on_batch_edit(*args)
    
    def _on_batch_delete(self):
        """Handle batch delete - delegates to batch helper"""
        self.batch_helper.on_batch_delete()
    
    def _load_file_urls_for_batch(self, client_id, batch_number, client_name=""):
        """Load file URLs for batch - delegates to file URLs helper"""
        self.file_urls_helper.load_file_urls_for_batch(client_id, batch_number, client_name)
    
    def _on_file_urls_search_changed(self):
        """Handle file URLs search change - delegates to file URLs helper"""
        self.file_urls_helper.on_file_urls_search_changed()
    
    def _on_file_urls_sort_changed(self):
        """Handle file URLs sort change - delegates to file URLs helper"""
        self.file_urls_helper.on_file_urls_sort_changed()
    
    def _on_file_urls_row_double_clicked(self, row, col):
        """Handle file URLs row double click - delegates to file URLs helper"""
        self.file_urls_helper.on_file_urls_row_double_clicked(row, col)
    
    def _show_file_urls_context_menu(self, pos):
        """Show file URLs context menu - delegates to file URLs helper"""
        self.file_urls_helper.show_file_urls_context_menu(pos)
    
    def _on_client_row_clicked(self, row, col):
        """Handle client row click"""
        self._fill_details_form(row)
    
    def _on_client_row_double_clicked(self, row, col):
        """Handle client row double click"""
        self._fill_details_form(row)
        self.tab_widget.setCurrentIndex(1)
        clients_data = self.clients_helper.get_clients_data()
        if 0 <= row < len(clients_data):
            client = clients_data[row]
            self.files_helper.load_files_for_client(client["id"], client.get("client_name", ""))
            self.batch_helper.load_batch_list_for_client(client["id"])
            self.tab_widget.setCurrentIndex(2)
