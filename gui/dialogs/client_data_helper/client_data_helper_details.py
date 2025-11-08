from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QMessageBox, QTextEdit, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QSizePolicy, QApplication, QToolTip
)
from PySide6.QtCore import Qt
import qtawesome as qta
import webbrowser

class ClientDataDetailsHelper:
    """Helper class for Details tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # Form widgets
        self.details_widgets = {}
        self.details_editable = {}
        self.details_copy_buttons = {}
        
        # State variables
        self._selected_client_index = None
        self._add_mode = False
        self._editing_link_index = None
    
    def init_details_tab(self, tab_widget):
        """Initialize the details tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # Form layout
        self.details_layout = QFormLayout()
        tab_layout.addLayout(self.details_layout)
        
        # Create form fields
        fields = [
            ("Name", "client_name", True),
            ("Contact", "contact", True),
            ("Links", "links", True),
            ("Status", "status", True),
            ("Note", "note", True)
        ]
        
        for label, key, editable in fields:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            
            if key == "note":
                w = QTextEdit("")
                row_layout.addWidget(w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            elif key == "links":
                links_widget = self._create_links_widget()
                row_layout.addWidget(links_widget)
                self.details_widgets[key] = self.links_table
                self.details_editable[key] = True
            elif key == "status":
                self.status_combo = QComboBox()
                self.status_combo.addItems(["Active", "Repeat", "Dormant"])
                row_layout.addWidget(self.status_combo)
                self.details_widgets[key] = self.status_combo
                self.details_editable[key] = True
            else:
                w = QLineEdit("")
                row_layout.addWidget(w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            
            # Add copy button for appropriate fields
            if key not in ("links", "status"):
                copy_btn = QPushButton()
                copy_btn.setIcon(qta.icon("fa6s.copy"))
                copy_btn.setFixedWidth(28)
                copy_btn.setFixedHeight(28)
                copy_btn.setToolTip(f"Copy {label}")
                copy_btn.clicked.connect(lambda _, k=key, btn=copy_btn: self.copy_detail_to_clipboard(k, btn))
                row_layout.addWidget(copy_btn)
                self.details_copy_buttons[key] = copy_btn
            
            self.details_layout.addRow(label, row_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(qta.icon("fa6s.floppy-disk"), " Save")
        self.save_button.clicked.connect(self.save_client_details)
        self.add_button = QPushButton(qta.icon("fa6s.user-plus"), " Add Client")
        self.add_button.clicked.connect(self.add_client_mode)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.add_button)
        tab_layout.addLayout(button_layout)
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.id-card"), "Details")
        
        # Initial state
        self.save_button.setEnabled(False)
    
    def _create_links_widget(self):
        """Create the links management widget"""
        links_widget = QWidget()
        links_layout = QVBoxLayout(links_widget)
        links_layout.setContentsMargins(0, 0, 0, 0)
        
        # Entry row
        entry_row = QHBoxLayout()
        self.link_entry = QLineEdit("")
        self.link_entry.setPlaceholderText("Enter link and press Add")
        self.add_link_btn = QPushButton(qta.icon("fa6s.plus"), " Add Link")
        self.add_link_btn.clicked.connect(self.add_link)
        entry_row.addWidget(self.link_entry)
        entry_row.addWidget(self.add_link_btn)
        links_layout.addLayout(entry_row)
        
        # Links table
        self.links_table = QTableWidget()
        self.links_table.setColumnCount(2)
        self.links_table.setHorizontalHeaderLabels(["Link", "Actions"])
        self.links_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.links_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.links_table.setSelectionMode(QTableWidget.SingleSelection)
        self.links_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.links_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        links_layout.addWidget(self.links_table)
        
        self.links_table.cellClicked.connect(self.on_link_table_cell_clicked)
        
        return links_widget
    
    def copy_detail_to_clipboard(self, key, btn=None):
        """Copy detail field to clipboard"""
        widget = self.details_widgets.get(key)
        value = ""
        if key == "note" and isinstance(widget, QTextEdit):
            value = widget.toPlainText()
        elif isinstance(widget, QLineEdit):
            value = widget.text()
        else:
            value = ""
        
        clipboard = self.parent.clipboard() if self.parent and hasattr(self.parent, "clipboard") else None
        if clipboard is None:
            clipboard = QApplication.clipboard()
        clipboard.setText(value)
        
        if btn is not None:
            global_pos = btn.mapToGlobal(btn.rect().bottomRight())
            QToolTip.showText(global_pos, "Copied!", btn)
    
    def fill_details_form(self, row, clients_data):
        """Fill the details form with client data"""
        if 0 <= row < len(clients_data):
            client = clients_data[row]
            self._selected_client_index = row
            self._add_mode = False
            
            for key, widget in self.details_widgets.items():
                if key == "note":
                    widget.setPlainText(str(client.get(key, "")))
                elif key == "links":
                    self.populate_links_table(str(client.get("links", "")))
                elif key == "status":
                    status_val = str(client.get("status", "Active"))
                    idx = self.status_combo.findText(status_val)
                    if idx != -1:
                        self.status_combo.setCurrentIndex(idx)
                    else:
                        self.status_combo.setCurrentIndex(0)
                else:
                    widget.setText(str(client.get(key, "")))
            
            self.save_button.setEnabled(True)
            
            # Set parent's selected client info
            if hasattr(self.parent, '_selected_client_name'):
                self.parent._selected_client_name = client.get("client_name", "")
            if hasattr(self.parent, '_selected_client_id'):
                self.parent._selected_client_id = client.get("id", None)
    
    def populate_links_table(self, links_str):
        """Populate the links table with links"""
        self.links_table.setRowCount(0)
        links = [l for l in links_str.split("|") if l.strip()]
        
        for idx, link in enumerate(links):
            self.links_table.insertRow(idx)
            link_item = QTableWidgetItem(link)
            self.links_table.setItem(idx, 0, link_item)
            
            # Create action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            open_btn = QPushButton()
            open_btn.setIcon(qta.icon("fa6s.up-right-from-square"))
            open_btn.setToolTip("Open link")
            open_btn.clicked.connect(lambda _, url=link: webbrowser.open(url))
            
            edit_btn = QPushButton()
            edit_btn.setIcon(qta.icon("fa6s.pen-to-square"))
            edit_btn.setToolTip("Edit link")
            edit_btn.clicked.connect(lambda _, idx=idx: self.edit_link(idx))
            
            delete_btn = QPushButton()
            delete_btn.setIcon(qta.icon("fa6s.trash"))
            delete_btn.setToolTip("Delete link")
            delete_btn.clicked.connect(lambda _, idx=idx: self.delete_link(idx))
            
            actions_layout.addWidget(open_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.links_table.setCellWidget(idx, 1, actions_widget)
    
    def get_links_list(self):
        """Get list of links from the table"""
        links = []
        for i in range(self.links_table.rowCount()):
            item = self.links_table.item(i, 0)
            if item:
                links.append(item.text())
        return links
    
    def add_link(self):
        """Add or update a link"""
        link_text = self.link_entry.text().strip()
        if not link_text:
            QMessageBox.warning(self.parent, "Validation Error", "Link cannot be empty.")
            return
        
        # Update existing link
        if self._editing_link_index is not None:
            item = self.links_table.item(self._editing_link_index, 0)
            if item:
                item.setText(link_text)
            self._editing_link_index = None
            self.add_link_btn.setText("Add Link")
            self.link_entry.clear()
            return
        
        # Check for duplicates
        for i in range(self.links_table.rowCount()):
            item = self.links_table.item(i, 0)
            if item and item.text() == link_text:
                QMessageBox.warning(self.parent, "Duplicate Link", "Link already exists.")
                return
        
        # Add new link
        row = self.links_table.rowCount()
        self.links_table.insertRow(row)
        link_item = QTableWidgetItem(link_text)
        self.links_table.setItem(row, 0, link_item)
        
        # Create action buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        open_btn = QPushButton()
        open_btn.setIcon(qta.icon("fa6s.up-right-from-square"))
        open_btn.setToolTip("Open link")
        open_btn.clicked.connect(lambda _, url=link_text: webbrowser.open(url))
        
        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa6s.pen-to-square"))
        edit_btn.setToolTip("Edit link")
        edit_btn.clicked.connect(lambda _, idx=row: self.edit_link(idx))
        
        delete_btn = QPushButton()
        delete_btn.setIcon(qta.icon("fa6s.trash"))
        delete_btn.setToolTip("Delete link")
        delete_btn.clicked.connect(lambda _, idx=row: self.delete_link(idx))
        
        actions_layout.addWidget(open_btn)
        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(delete_btn)
        self.links_table.setCellWidget(row, 1, actions_widget)
        
        self.link_entry.clear()
    
    def edit_link(self, idx):
        """Edit a link"""
        item = self.links_table.item(idx, 0)
        if item:
            self.link_entry.setText(item.text())
            self._editing_link_index = idx
            self.add_link_btn.setText("Update Link")
    
    def delete_link(self, idx):
        """Delete a link"""
        reply = QMessageBox.question(
            self.parent, "Delete Link", 
            "Are you sure you want to delete this link?", 
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.links_table.removeRow(idx)
            self._editing_link_index = None
            self.add_link_btn.setText("Add Link")
            self.link_entry.clear()
    
    def on_link_table_cell_clicked(self, row, col):
        """Handle link table cell click"""
        pass
    
    def add_client_mode(self):
        """Switch to add client mode"""
        self._selected_client_index = None
        self._add_mode = True
        
        # Clear all fields
        for key, widget in self.details_widgets.items():
            if key == "note":
                widget.setPlainText("")
            elif key == "links":
                self.links_table.setRowCount(0)
                self.link_entry.clear()
                self._editing_link_index = None
                self.add_link_btn.setText("Add Link")
            elif key == "status":
                self.status_combo.setCurrentIndex(0)
            else:
                widget.setText("")
        
        self.save_button.setEnabled(True)
        self.parent.tab_widget.setCurrentIndex(1)
        
        # Clear other tabs
        if hasattr(self.parent, 'files_helper'):
            self.parent.files_helper.clear_files_tab()
        if hasattr(self.parent, 'batch_helper'):
            self.parent.batch_helper.clear_batch_tab()
    
    def save_client_details(self):
        """Save client details to database"""
        # Collect form data
        updated_data = {}
        for key, widget in self.details_widgets.items():
            if key == "note":
                updated_data[key] = widget.toPlainText()
            elif key == "links":
                links = self.get_links_list()
                updated_data[key] = "|".join(links)
            elif key == "status":
                updated_data[key] = self.status_combo.currentText()
            else:
                updated_data[key] = widget.text()
        
        # Validate
        if not updated_data["client_name"].strip():
            QMessageBox.warning(self.parent, "Validation Error", "Client Name cannot be empty.")
            return
        
        try:
            if self._add_mode:
                # Check for duplicate name
                clients = self.db_helper.get_all_clients()
                existing_names = {client["client_name"] for client in clients}
                if updated_data["client_name"] in existing_names:
                    QMessageBox.warning(
                        self.parent, "Duplicate Client Name", 
                        "Client name already exists. Please choose another name."
                    )
                    return
                
                # Add new client
                self.db_helper.add_client(
                    client_name=updated_data["client_name"],
                    contact=updated_data["contact"],
                    links=updated_data["links"],
                    status=updated_data["status"],
                    note=updated_data["note"]
                )
                
                self._reset_form()
                self.parent.tab_widget.setCurrentIndex(0)
                QMessageBox.information(self.parent, "Success", "Client added successfully.")
                
            else:
                # Update existing client
                if self._selected_client_index is None:
                    QMessageBox.warning(self.parent, "No Client Selected", "Please select a client to update.")
                    return
                
                clients_data = self.parent.clients_helper.get_clients_data()
                if self._selected_client_index >= len(clients_data):
                    QMessageBox.warning(self.parent, "Invalid Selection", "Selected client is no longer valid.")
                    return
                
                client = clients_data[self._selected_client_index]
                old_id = client["id"]
                
                self.db_helper.update_client(
                    client_id=old_id,
                    client_name=updated_data["client_name"],
                    contact=updated_data["contact"],
                    links=updated_data["links"],
                    status=updated_data["status"],
                    note=updated_data["note"]
                )
                
                # Don't reset form for updates - keep selection
                QMessageBox.information(self.parent, "Success", "Client data updated successfully.")
            
            # Refresh clients list
            if hasattr(self.parent, 'clients_helper'):
                # Store current selection before refresh
                current_client_name = updated_data.get("client_name", "")
                self.parent.clients_helper.refresh_data()
                
                # Restore selection after refresh for updates
                if not self._add_mode and current_client_name:
                    self.parent.clients_helper.select_client_by_name(current_client_name)
                
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", str(e))
    
    def _reset_form(self):
        """Reset form to default state"""
        self._selected_client_index = None
        self._add_mode = False
        self.save_button.setEnabled(False)
        
        # Clear form fields
        for key, widget in self.details_widgets.items():
            if key == "note":
                widget.setPlainText("")
            elif key == "links":
                self.links_table.setRowCount(0)
                self.link_entry.clear()
                self._editing_link_index = None
                self.add_link_btn.setText("Add Link")
            elif key == "status":
                self.status_combo.setCurrentIndex(0)
            else:
                widget.setText("")
        
        # Clear other tabs
        if hasattr(self.parent, 'files_helper'):
            self.parent.files_helper.clear_files_tab()
        if hasattr(self.parent, 'batch_helper'):
            self.parent.batch_helper.clear_batch_tab()
