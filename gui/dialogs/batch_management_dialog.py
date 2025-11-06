from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QLabel, QComboBox, QSpinBox,
    QMessageBox, QMenu, QDateTimeEdit, QCheckBox
)
from PySide6.QtGui import QAction, QColor, QDesktopServices
from PySide6.QtCore import Qt, QDateTime, QTimer, QThread, Signal, QObject, QUrl
import qtawesome as qta
from datetime import datetime, timedelta
import logging

class SyncDriveWorker(QObject):
    finished = Signal()
    message = Signal(str)
    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog

    def run(self):
        try:
            logging.debug("SyncDriveWorker: Starting sync process.")
            drive_service, sheets_service = self.dialog.get_google_services(require_sheets=True)
            if not drive_service or not sheets_service:
                msg = "Google Drive/Sheets service not available."
                logging.error(msg)
                self.message.emit(msg)
                return

            self.dialog.ensure_batch_folder_exist()
            rak_arsip_folder_id = self.dialog._rak_arsip_folder_id
            batch_folder_id = self.dialog._batch_folder_id

            if not rak_arsip_folder_id or not batch_folder_id:
                msg = "Rak_Arsip_Database or BATCH folder not found or failed to create."
                logging.error(msg)
                self.message.emit(msg)
                return

            self.message.emit("Checking for Batch Queue spreadsheet in BATCH folder...")
            logging.debug("SyncDriveWorker: Checking for Batch Queue spreadsheet in BATCH folder...")
            try:
                results = drive_service.files().list(
                    q=f"name = 'Batch Queue' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{batch_folder_id}' in parents and trashed = false",
                    fields="files(id, name)",
                    pageSize=5
                ).execute()
            except Exception as e:
                logging.error(f"Drive API error: {e}")
                self.message.emit(f"Drive API error: {e}")
                return

            spreadsheets = results.get('files', [])
            if spreadsheets:
                spreadsheet_id = spreadsheets[0]['id']
                msg = f"Batch Queue spreadsheet already exists: {spreadsheets[0]['name']}"
                logging.info(msg)
                self.message.emit(msg)
                self.dialog._batch_queue_spreadsheet_id = spreadsheet_id
                try:
                    self.dialog.update_batch_queue_spreadsheet(spreadsheet_id)
                    self.message.emit("Batch Queue spreadsheet updated with latest data.")
                    logging.info("Batch Queue spreadsheet updated with latest data.")
                except Exception as e:
                    logging.error(f"Failed to update Batch Queue spreadsheet: {e}")
                    self.message.emit(f"Failed to update Batch Queue spreadsheet: {e}")
            else:
                self.message.emit("Batch Queue spreadsheet not found, creating...")
                logging.info("Batch Queue spreadsheet not found, creating...")
                try:
                    spreadsheet_id = self.dialog.create_batch_queue_spreadsheet()
                except Exception as e:
                    logging.error(f"Error creating batch queue spreadsheet: {e}")
                    self.message.emit(f"Error creating batch queue spreadsheet: {e}")
                    spreadsheet_id = None
                if spreadsheet_id:
                    self.dialog._batch_queue_spreadsheet_id = spreadsheet_id
                    msg = f"Batch Queue spreadsheet created with ID: {spreadsheet_id}"
                    logging.info(msg)
                    self.message.emit(msg)
                else:
                    msg = "Failed to create Batch Queue spreadsheet."
                    logging.error(msg)
                    self.message.emit(msg)
        except Exception as e:
            logging.error(f"Sync to Drive error: {e}", exc_info=True)
            self.message.emit(f"Sync to Drive error: {e}")
        finally:
            logging.debug("SyncDriveWorker: Sync process finished.")
            self.finished.emit()

class BatchManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Management")
        self.resize(900, 600)
        self.db_manager = self._get_db_manager()
        self._batch_data_all = []
        self._batch_data_filtered = []
        self._batch_sort_field = "Created At"
        self._batch_sort_order = "Ascending"
        self._batch_page = 1
        self._batch_rows_per_page = 20
        self._batch_total_pages = 1
        self._hide_finished = False
        self._hide_hold = False
        self._rak_arsip_folder_id = None
        self._batch_folder_id = None
        self._drive_service = None
        self._sheets_service = None
        self._credentials = None
        self._sync_blink_timer = None
        self._sync_blink_state = False
        self._sync_thread = None
        self._sync_worker = None
        self._batch_queue_spreadsheet_id = None
        self.init_ui()
        self.load_batch_data()
        QTimer.singleShot(0, self.on_sync_drive_clicked)

    def _get_db_manager(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, "db_manager"):
                return parent.db_manager
            parent = parent.parent() if hasattr(parent, "parent") else None
        return None

    def init_ui(self):
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.batch_search_edit = QLineEdit()
        self.batch_search_edit.setPlaceholderText("Search batch number or note...")
        self.batch_search_edit.setMinimumHeight(32)
        self.batch_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.batch_search_edit, 1)

        self.batch_sort_combo = QComboBox()
        self.batch_sort_combo.addItems(["Client Name", "Batch Number", "Note", "File Count", "Created At"])
        self.batch_sort_combo.setCurrentText("Created At")
        self.batch_sort_order_combo = QComboBox()
        self.batch_sort_order_combo.addItems(["Ascending", "Descending"])
        self.batch_sort_order_combo.setCurrentText("Ascending")
        
        # Status filter
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["All Status", "Finished", "Hold", "In Progress", "Review", "Urgent", "Low Priority", "Custom", "Empty"])
        self.status_filter_combo.setCurrentText("All Status")
        
        row.addWidget(QLabel("Sort by:"))
        row.addWidget(self.batch_sort_combo)
        row.addWidget(self.batch_sort_order_combo)
        row.addWidget(QLabel("Filter:"))
        row.addWidget(self.status_filter_combo)
        row.addStretch()

        self.batch_refresh_btn = QPushButton(qta.icon("fa6s.arrows-rotate"), "Refresh")
        self.batch_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Batch")
        self.batch_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Batch")
        self.batch_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Batch")
        row.addWidget(self.batch_refresh_btn)
        row.addWidget(self.batch_add_btn)
        row.addWidget(self.batch_edit_btn)
        row.addWidget(self.batch_delete_btn)
        layout.addLayout(row)

        self.batch_table = QTableWidget(self)
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels([
            "Client Name", "Batch Number", "Note", "File Count", "Created At"
        ])
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setSelectionMode(QTableWidget.SingleSelection)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.batch_table.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.batch_table)

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
        self.batch_rows_per_page_combo.setCurrentText("20")
        pagination_layout.addWidget(self.batch_prev_btn)
        pagination_layout.addWidget(self.batch_next_btn)
        pagination_layout.addWidget(QLabel("Page:"))
        pagination_layout.addWidget(self.batch_page_spinner)
        pagination_layout.addWidget(self.batch_page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(QLabel("Rows per page:"))
        pagination_layout.addWidget(self.batch_rows_per_page_combo)

        self.hide_finished_checkbox = QCheckBox("Hide Finished")
        self.hide_finished_checkbox.setChecked(False)
        pagination_layout.addWidget(self.hide_finished_checkbox)

        self.hide_hold_checkbox = QCheckBox("Hide Hold")
        self.hide_hold_checkbox.setChecked(False)
        pagination_layout.addWidget(self.hide_hold_checkbox)

        self.batch_sync_drive_btn = QPushButton(qta.icon("fa6s.cloud-arrow-up"), "Sync to Drive")
        pagination_layout.addWidget(self.batch_sync_drive_btn)

        self.batch_globe_btn = QPushButton(qta.icon("fa6s.globe"), "")
        self.batch_globe_btn.setToolTip("Open Batch Queue Sheet in browser")
        self.batch_globe_btn.setFixedWidth(32)
        self.batch_globe_btn.clicked.connect(self.on_open_batch_queue_sheet)
        pagination_layout.addWidget(self.batch_globe_btn)

        layout.addLayout(pagination_layout)

        stats_layout = QHBoxLayout()
        self.stats_total_files_label = QLabel("Total Files: 0")
        self.stats_batch_queue_label = QLabel("Batch Queue: 0 batch (0 files)")
        self.stats_oldest_label = QLabel("Oldest: -")
        self.stats_newest_label = QLabel("Newest: -")
        stats_layout.addWidget(self.stats_total_files_label)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.stats_batch_queue_label)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.stats_oldest_label)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.stats_newest_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Color legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Status Colors:"))
        
        # Create color legend items
        color_items = [
            ("Finished", "#43a047"),
            ("Hold", "#ff9800"), 
            ("In Progress", "#2196f3"),
            ("Review", "#9c27b0"),
            ("Urgent", "#f44336"),
            ("Low Priority", "#9e9e9e"),
            ("Custom", "#00bcd4")
        ]
        
        for status, color_hex in color_items:
            color_label = QLabel("●")
            color_label.setStyleSheet(f"color: {color_hex}; font-size: 14px; font-weight: bold;")
            text_label = QLabel(status)
            text_label.setStyleSheet("font-size: 10px;")
            legend_layout.addWidget(color_label)
            legend_layout.addWidget(text_label)
            legend_layout.addSpacing(10)
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        self.batch_refresh_btn.clicked.connect(self.load_batch_data)
        self.batch_search_edit.textChanged.connect(self.update_batch_table)
        self.batch_sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        self.batch_sort_order_combo.currentIndexChanged.connect(self.on_sort_changed)
        self.status_filter_combo.currentIndexChanged.connect(self.on_status_filter_changed)
        self.batch_prev_btn.clicked.connect(self.on_prev_page)
        self.batch_next_btn.clicked.connect(self.on_next_page)
        self.batch_rows_per_page_combo.currentIndexChanged.connect(self.on_rows_per_page_changed)
        self.batch_page_spinner.valueChanged.connect(self.on_page_spinner_changed)
        self.batch_add_btn.clicked.connect(self.on_batch_add)
        self.batch_edit_btn.clicked.connect(self.on_batch_edit)
        self.batch_delete_btn.clicked.connect(self.on_batch_delete)
        self.batch_table.cellDoubleClicked.connect(self.on_batch_edit)
        self.batch_table.customContextMenuRequested.connect(self.show_batch_context_menu)
        self.hide_finished_checkbox.stateChanged.connect(self.on_hide_finished_changed)
        self.hide_hold_checkbox.stateChanged.connect(self.on_hide_hold_changed)
        self.batch_sync_drive_btn.clicked.connect(self.on_sync_drive_clicked)

    def on_open_batch_queue_sheet(self):
        spreadsheet_id = getattr(self, "_batch_queue_spreadsheet_id", None)
        if spreadsheet_id:
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            QDesktopServices.openUrl(QUrl(url))
        else:
            print("Batch Queue spreadsheet ID not available.")

    def load_batch_data(self):
        batch_rows = self.db_manager.get_all_batches() if self.db_manager else []
        batch_data = []
        for row in batch_rows:
            file_count = self.db_manager.count_file_client_batch_by_batch_number(row["batch_number"])
            batch_data.append((
                row["client_name"], row["batch_number"], row["note"], file_count, row["created_at"], row["client_id"]
            ))
        self._batch_data_all = batch_data
        self._batch_page = 1
        self.update_batch_table()
        self.update_stats_row()

    def update_batch_table(self):
        search_text = self.batch_search_edit.text().strip().lower()
        status_filter = self.status_filter_combo.currentText()
        hide_finished = self.hide_finished_checkbox.isChecked()
        hide_hold = self.hide_hold_checkbox.isChecked()
        
        if search_text:
            filtered = [
                (client_name, batch_number, note, file_count, created_at, client_id)
                for client_name, batch_number, note, file_count, created_at, client_id in self._batch_data_all
                if search_text in str(client_name).lower()
                or search_text in str(batch_number).lower()
                or search_text in str(note).lower()
            ]
        else:
            filtered = list(self._batch_data_all)
            
        # Apply status filter first
        if status_filter != "All Status":
            if status_filter == "Empty":
                filtered = [row for row in filtered if not str(row[2]).strip()]
            elif status_filter == "Custom":
                predefined_statuses = ["finished", "hold", "in progress", "progress", "review", "urgent", "low priority", "low"]
                filtered = [row for row in filtered 
                          if str(row[2]).strip().lower() not in predefined_statuses and str(row[2]).strip()]
            else:
                status_lower = status_filter.lower()
                filtered = [row for row in filtered 
                          if status_lower in str(row[2]).strip().lower()]
        
        # Apply hide checkboxes after status filter
        if hide_finished:
            filtered = [row for row in filtered if str(row[2]).strip().lower() != "finished"]
        if hide_hold:
            filtered = [row for row in filtered if "hold" not in str(row[2]).strip().lower()]
            
        self._batch_data_filtered = filtered

        self._apply_batch_sorting()

        total_rows = len(self._batch_data_filtered)
        rows_per_page = int(self.batch_rows_per_page_combo.currentText())
        self._batch_rows_per_page = rows_per_page
        self._batch_total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
        if self._batch_page > self._batch_total_pages:
            self._batch_page = self._batch_total_pages

        start_idx = (self._batch_page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        page_data = self._batch_data_filtered[start_idx:end_idx]

        # Clean up table before filling data
        self.batch_table.clearContents()
        self.batch_table.setRowCount(0)
        self.batch_table.setRowCount(len(page_data))

        for row_idx, (client_name, batch_number, note, file_count, created_at, client_id) in enumerate(page_data):
            client_item = QTableWidgetItem(str(client_name))
            batch_item = QTableWidgetItem(str(batch_number))
            note_item = QTableWidgetItem(str(note))
            count_item = QTableWidgetItem(str(file_count))
            created_item = QTableWidgetItem(str(created_at) if created_at else "")
            
            note_lower = str(note).strip().lower()
            color = None
            
            if note_lower == "finished":
                # Green color for finished
                color = QColor("#43a047")
            elif "hold" in note_lower:
                # Orange/amber color for hold
                color = QColor("#ff9800")
            elif "in progress" in note_lower or "progress" in note_lower:
                # Blue color for in progress
                color = QColor("#2196f3")
            elif "review" in note_lower:
                # Purple color for review
                color = QColor("#9c27b0")
            elif "urgent" in note_lower:
                # Red color for urgent
                color = QColor("#f44336")
            elif "low priority" in note_lower or "low" in note_lower:
                # Gray color for low priority
                color = QColor("#9e9e9e")
            elif note_lower and note_lower != "":
                # Light blue for other custom notes
                color = QColor("#00bcd4")
            
            if color:
                color.setAlpha(80)
                for item in (client_item, batch_item, note_item, count_item, created_item):
                    item.setBackground(color)
                    
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
        self.update_stats_row()

    def update_stats_row(self):
        total_files = 0
        total_batch = len(self._batch_data_all)
        queue_batches = []
        queue_files = 0
        for row in self._batch_data_all:
            total_files += int(row[3]) if row[3] else 0
            note_lower = str(row[2]).strip().lower()
            if note_lower != "finished" and "hold" not in note_lower:
                queue_batches.append(row)
                queue_files += int(row[3]) if row[3] else 0
        self.stats_total_files_label.setText(f"Total Batches: {total_batch} ({total_files} files)")
        self.stats_batch_queue_label.setText(f"Batch Queue: {len(queue_batches)} ({queue_files} files)")

        # Use both filter dropdown and checkboxes for stats
        hide_finished = self.hide_finished_checkbox.isChecked()
        hide_hold = self.hide_hold_checkbox.isChecked()
        status_filter = self.status_filter_combo.currentText()
        
        if status_filter != "All Status":
            # Use filtered data from current filter
            filtered_rows = self._batch_data_filtered if hasattr(self, '_batch_data_filtered') else self._batch_data_all
        else:
            # Apply checkbox filters when no specific status filter is active
            if hide_finished and hide_hold:
                filtered_rows = [row for row in self._batch_data_all 
                               if str(row[2]).strip().lower() != "finished" 
                               and "hold" not in str(row[2]).strip().lower()]
            elif hide_finished:
                filtered_rows = [row for row in self._batch_data_all if str(row[2]).strip().lower() != "finished"]
            elif hide_hold:
                filtered_rows = [row for row in self._batch_data_all if "hold" not in str(row[2]).strip().lower()]
            else:
                filtered_rows = self._batch_data_all
                
        created_dates = [row[4] for row in filtered_rows if row[4]]
        if created_dates:
            oldest_date = min(created_dates)
            newest_date = max(created_dates)
            oldest_text = time_ago(oldest_date)
            newest_text = time_ago(newest_date)
        else:
            oldest_text = "-"
            newest_text = "-"
        self.stats_oldest_label.setText(f"Oldest: {oldest_text}")
        self.stats_newest_label.setText(f"Newest: {newest_text}")

    def _apply_batch_sorting(self):
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

    def on_sort_changed(self):
        self._batch_sort_field = self.batch_sort_combo.currentText()
        self._batch_sort_order = self.batch_sort_order_combo.currentText()
        self._batch_page = 1
        self.update_batch_table()

    def on_prev_page(self):
        if self._batch_page > 1:
            self._batch_page -= 1
            self.update_batch_table()

    def on_next_page(self):
        if self._batch_page < self._batch_total_pages:
            self._batch_page += 1
            self.update_batch_table()

    def on_rows_per_page_changed(self):
        self._batch_rows_per_page = int(self.batch_rows_per_page_combo.currentText())
        self._batch_page = 1
        self.update_batch_table()

    def on_page_spinner_changed(self, value):
        if value != self._batch_page:
            self._batch_page = value
            self.update_batch_table()

    def on_status_filter_changed(self, index):
        self.update_batch_table()

    def on_hide_finished_changed(self, state):
        self.update_batch_table()

    def on_hide_hold_changed(self, state):
        self.update_batch_table()

    def get_selected_row_data(self):
        row = self.batch_table.currentRow()
        if row < 0 or row >= self.batch_table.rowCount():
            return None
        client_name = self.batch_table.item(row, 0).text()
        batch_number = self.batch_table.item(row, 1).text()
        note = self.batch_table.item(row, 2).text()
        file_count = self.batch_table.item(row, 3).text()
        created_at = self.batch_table.item(row, 4).text()
        client_id = None
        for data in self._batch_data_filtered:
            if data[0] == client_name and data[1] == batch_number:
                client_id = data[5]
                break
        return (client_name, batch_number, note, file_count, created_at, client_id)

    def on_batch_add(self):
        from gui.dialogs.client_data_dialog import BatchEditDialog
        clients = self.db_manager.get_all_clients_simple() if self.db_manager else []
        if not clients:
            QMessageBox.warning(self, "No Client", "No client found. Please add a client first.")
            return
        dialog = BatchEditDialog(
            parent=self,
            client_id=None,
            show_client_combo=True,
            clients=clients,
            created_at=None
        )
        if dialog.exec() == QDialog.Accepted:
            batch_number, note, client_id, created_at = dialog.get_values()
            if not batch_number:
                QMessageBox.warning(self, "Validation Error", "Batch Number cannot be empty.")
                return
            if not client_id:
                QMessageBox.warning(self, "Validation Error", "Client must be selected.")
                return
            try:
                self.db_manager.batch_manager_helper.add_batch(batch_number, client_id, note, created_at)
                self.load_batch_data()
                QMessageBox.information(self, "Success", "Batch added successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def on_batch_edit(self, *args):
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Batch Selected", "Please select a batch to edit.")
            return
        client_name, batch_number, note, file_count, created_at, client_id = self.get_selected_row_data()
        from gui.dialogs.client_data_dialog import BatchEditDialog
        clients = self.db_manager.get_all_clients_simple() if self.db_manager else []
        dialog = BatchEditDialog(
            batch_number=batch_number,
            note=note,
            client_id=client_id,
            parent=self,
            show_client_combo=True,
            clients=clients,
            created_at=created_at
        )
        if dialog.exec() == QDialog.Accepted:
            new_batch_number, new_note, new_client_id, new_created_at = dialog.get_values()
            if not new_client_id:
                new_client_id = client_id
            if not new_batch_number:
                QMessageBox.warning(self, "Input Error", "Batch number cannot be empty.")
                return
            try:
                self.db_manager.batch_manager_helper.update_batch(
                    batch_number, new_batch_number, new_note, new_client_id, new_created_at
                )
                self.load_batch_data()
                QMessageBox.information(self, "Success", "Batch updated successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def on_batch_delete(self):
        row = self.batch_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Batch Selected", "Please select a batch to delete.")
            return
        client_name, batch_number, note, file_count, created_at, client_id = self.get_selected_row_data()
        affected_count = self.db_manager.count_file_client_batch_by_batch_number(batch_number)
        msg1 = (
            f"Deleting batch number '{batch_number}' will also delete {affected_count} related record(s) in File Client Batch records.\n"
            "This will affect all files/projects using this batch number.\n\n"
            "Do you want to continue?"
        )
        reply1 = QMessageBox.warning(self, "Delete Batch", msg1, QMessageBox.Yes | QMessageBox.No)
        if reply1 != QMessageBox.Yes:
            return
        msg2 = (
            f"Are you sure you want to permanently delete batch number '{batch_number}'?\n"
            "This action cannot be undone."
        )
        reply2 = QMessageBox.warning(self, "Are you sure?", msg2, QMessageBox.Yes | QMessageBox.No)
        if reply2 != QMessageBox.Yes:
            return
        try:
            self.db_manager.delete_batch_and_file_client_batch(batch_number)
            self.load_batch_data()
            QMessageBox.information(self, "Success", "Batch deleted successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def show_batch_context_menu(self, pos):
        index = self.batch_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu(self.batch_table)
        icon_edit = qta.icon("fa6s.pen-to-square")
        icon_delete = qta.icon("fa6s.trash")
        icon_refresh = qta.icon("fa6s.arrows-rotate")
        action_edit = QAction(icon_edit, "Edit Batch", self)
        action_delete = QAction(icon_delete, "Delete Batch", self)
        action_refresh = QAction(icon_refresh, "Refresh", self)
        def do_edit():
            self.batch_table.selectRow(row)
            self.on_batch_edit()
        def do_delete():
            self.batch_table.selectRow(row)
            self.on_batch_delete()
        def do_refresh():
            self.load_batch_data()
        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        action_refresh.triggered.connect(do_refresh)
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.addSeparator()
        menu.addAction(action_refresh)
        menu.exec(self.batch_table.viewport().mapToGlobal(pos))

    def get_google_services(self, require_sheets=False):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            import os
            import datetime

            if self._drive_service and (not require_sheets or self._sheets_service):
                return self._drive_service, self._sheets_service

            creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "credentials_config.json")
            if not os.path.exists(creds_path):
                print(f"Credentials file not found: {creds_path}")
                return None, None

            scopes = ["https://www.googleapis.com/auth/drive"]
            if require_sheets:
                scopes.append("https://www.googleapis.com/auth/spreadsheets")
            
            try:
                credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
                
                # Force refresh credentials to ensure valid token with current timestamp
                import google.auth.transport.requests
                request = google.auth.transport.requests.Request()
                credentials.refresh(request)
                
                drive_service = build('drive', 'v3', credentials=credentials)
                sheets_service = None
                if require_sheets:
                    sheets_service = build('sheets', 'v4', credentials=credentials)
                self._drive_service = drive_service
                self._sheets_service = sheets_service
                self._credentials = credentials
                return drive_service, sheets_service
            except Exception as auth_error:
                print(f"Authentication error: {auth_error}")
                print("Possible causes:")
                print("1. System clock is not synchronized - please sync your system time")
                print("2. Service account credentials may be expired or invalid")
                print("3. Check if credentials_config.json is correct and not corrupted")
                return None, None
                
        except Exception as e:
            print(f"Google API init error: {e}")
            return None, None

    def ensure_batch_folder_exist(self):
        try:
            drive_service, _ = self.get_google_services()
            if not drive_service:
                return

            rak_arsip_folder_id = self._rak_arsip_folder_id
            batch_folder_id = self._batch_folder_id

            if not rak_arsip_folder_id:
                print("Sync to Drive: Checking Rak_Arsip_Database folder...")
                results = drive_service.files().list(
                    q="name = 'Rak_Arsip_Database' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                    fields="files(id)",
                    pageSize=5
                ).execute()
                folders = results.get('files', [])
                if folders:
                    rak_arsip_folder_id = folders[0]['id']
                    self._rak_arsip_folder_id = rak_arsip_folder_id
                    print("Rak_Arsip_Database found.")
                else:
                    print("Rak_Arsip_Database NOT found.")
                    self._rak_arsip_folder_id = None
                    return

            if not batch_folder_id:
                print("Checking for BATCH folder inside Rak_Arsip_Database...")
                batch_results = drive_service.files().list(
                    q=f"name = 'BATCH' and mimeType = 'application/vnd.google-apps.folder' and '{rak_arsip_folder_id}' in parents and trashed = false",
                    fields="files(id)",
                    pageSize=5
                ).execute()
                batch_folders = batch_results.get('files', [])
                if batch_folders:
                    batch_folder_id = batch_folders[0]['id']
                    self._batch_folder_id = batch_folder_id
                    print("BATCH folder found inside Rak_Arsip_Database.")
                else:
                    print("BATCH folder NOT found inside Rak_Arsip_Database.")
                    print("Creating BATCH folder inside Rak_Arsip_Database...")
                    file_metadata = {
                        'name': 'BATCH',
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [rak_arsip_folder_id]
                    }
                    created_folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                    if created_folder and created_folder.get('id'):
                        batch_folder_id = created_folder['id']
                        self._batch_folder_id = batch_folder_id
                        print("BATCH folder created successfully.")
                    else:
                        print("Failed to create BATCH folder.")
                        self._batch_folder_id = None
                        return
            else:
                print("BATCH folder found (cached).")

        except Exception as e:
            print(f"Sync to Drive error: {e}")

    def get_batch_queue_data_and_header(self):
        """Prepare header and data for Batch Queue spreadsheet."""
        from datetime import datetime
        
        data = []
        
        # Get batches with status breakdown
        batches_with_status = self.db_manager.get_all_batches_with_status_counts() if self.db_manager else []
        
        for batch in batches_with_status:
            note = batch.get("note", "")
            note_lower = str(note).strip().lower()
            # Skip batch if note contains "finished" or "hold"
            if note_lower == "finished" or "hold" in note_lower:
                continue
                
            batch_number = batch.get("batch_number", "")
            total_files = batch.get("total_files", 0)
            created_at = batch.get("created_at", "")
            created_at_ago = time_ago(created_at) if created_at else ""
            
            # Status counts
            draft_count = batch.get("draft_count", 0)
            modelling_count = batch.get("modelling_count", 0)
            rendering_count = batch.get("rendering_count", 0)
            photoshop_count = batch.get("photoshop_count", 0)
            need_upload_count = batch.get("need_upload_count", 0)
            pending_count = batch.get("pending_count", 0)
            
            data.append((
                batch_number, total_files, draft_count, modelling_count, 
                rendering_count, photoshop_count, need_upload_count, pending_count,
                created_at_ago, created_at
            ))
            
        # Sort ascending by created_at (oldest at top)
        data.sort(key=lambda x: x[9] if x[9] else "", reverse=False)
        
        # Calculate totals for header
        total_file_count = sum(d[1] for d in data)
        total_draft = sum(d[2] for d in data)
        total_modelling = sum(d[3] for d in data)
        total_rendering = sum(d[4] for d in data)
        total_photoshop = sum(d[5] for d in data)
        total_need_upload = sum(d[6] for d in data)
        total_pending = sum(d[7] for d in data)
        
        # Build header with totals
        header = [
            "Batch Number",
            f"File Count ({total_file_count})",
            f"Draft ({total_draft})",
            f"Modelling ({total_modelling})",
            f"Rendering ({total_rendering})",
            f"Photoshop ({total_photoshop})",
            f"Need Upload ({total_need_upload})",
            f"Pending ({total_pending})",
            "Created At"
        ]
        
        # Remove the raw created_at from data for sheet output
        data = [[d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8]] for d in data]
        
        # Format date: Senin, 10 Oktober 2025 (update terakhir 15:12 WIB)
        now = datetime.now()
        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        month_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                       "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        day_name = day_names[now.weekday()]
        day = now.day
        month_name = month_names[now.month - 1]
        year = now.year
        time_str = now.strftime("%H:%M")
        
        today_str = f"{day_name}, {day} {month_name} {year} (update terakhir {time_str} WIB)"
        return header, data, today_str

    def write_batch_queue_sheet_content(self, sheets_service, spreadsheet_id, header, data, today_str):
        # Row 1: Title
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="USER_ENTERED",
            body={"values": [["DESAINIA STUDIO BATCH QUEUE"]]
        }).execute()
        
        # Row 2: Date
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A2",
            valueInputOption="USER_ENTERED",
            body={"values": [[today_str]]}
        ).execute()
        
        # Row 4-5: Legend (pindah ke sini)
        self.add_color_legend(sheets_service, spreadsheet_id)
        
        # Row 7: Empty row for spacing
        # Row 8: Header
        # Row 9+: Data
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A8",
            valueInputOption="USER_ENTERED",
            body={"values": [header] + data}
        ).execute()

    def add_color_legend(self, sheets_service, spreadsheet_id):
        # Calculate totals
        total_queue, total_file_queue = self._get_total_queue_and_files()
        total_draft_count = self._get_total_draft_count()
        
        # Stats di row 4-6 (vertical layout) - label di kolom A, value di kolom B
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A4",
            valueInputOption="USER_ENTERED",
            body={"values": [
                ["📊 Total Queue", total_queue],
                ["📁 Total Files", total_file_queue],
                ["✏️ Draft Items", total_draft_count]
            ]}
        ).execute()
        
        # Color priority legend di row 4 - kolom D onwards (horizontal)
        color_legend_data = [
            ["🔴 Oldest", "🟡 Old", "🟢 Medium", "🔵 Recent", "🟣 New", "☑️ Newest"]
        ]
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="D4",
            valueInputOption="USER_ENTERED",
            body={"values": color_legend_data}
        ).execute()
        
        # Apply styling
        color_steps = [
            {"red": 0.992, "green": 0.733, "blue": 0.733},  # merah (oldest)
            {"red": 0.949, "green": 0.949, "blue": 0.733},  # kuning
            {"red": 0.827, "green": 0.949, "blue": 0.733},  # hijau muda
            {"red": 0.733, "green": 0.949, "blue": 0.949},  # cyan
            {"red": 0.733, "green": 0.827, "blue": 0.949},  # biru
            {"red": 0.882, "green": 0.733, "blue": 0.949},  # ungu (newest)
        ]
        
        requests = []
        
        # Merge A1:I1 for title
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9
                },
                "mergeType": "MERGE_ALL"
            }
        })
        
        # Merge A2:I2 for date
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9
                },
                "mergeType": "MERGE_ALL"
            }
        })
        
        # Style stats labels (A4:A6) - light gray background, bold, left-aligned
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 3,
                    "endRowIndex": 6,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                        "textFormat": {
                            "bold": True,
                            "fontSize": 10
                        },
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })
        
        # Style stats values (B4:B6) - light gray background, right-aligned
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 3,
                    "endRowIndex": 6,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                        "textFormat": {
                            "bold": False,
                            "fontSize": 10
                        },
                        "horizontalAlignment": "RIGHT",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })
        
        # Apply colors to legend (D4:I4)
        for i, color in enumerate(color_steps):
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 3,
                        "endRowIndex": 4,
                        "startColumnIndex": 3 + i,
                        "endColumnIndex": 4 + i
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                            "textFormat": {
                                "bold": True,
                                "fontSize": 9
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            })
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    def _get_total_queue_and_files(self):
        total_queue = 0
        total_file_queue = 0
        for row in self._batch_data_all:
            note = row[2]
            note_lower = str(note).strip().lower()
            if note_lower != "finished" and "hold" not in note_lower:
                total_queue += 1
                try:
                    total_file_queue += int(row[3]) if row[3] else 0
                except Exception:
                    pass
        return total_queue, total_file_queue

    def _get_total_draft_count(self):
        """Calculate total draft items across all active batches"""
        total_draft_count = 0
        try:
            batches_with_status = self.db_manager.get_all_batches_with_status_counts() if self.db_manager else []
            for batch in batches_with_status:
                note = batch.get("note", "")
                note_lower = str(note).strip().lower()
                # Skip batch if note contains "finished" or "hold"
                if note_lower == "finished" or "hold" in note_lower:
                    continue
                draft_count = batch.get("draft_count", 0)
                total_draft_count += draft_count
        except Exception as e:
            print(f"Error calculating draft count: {e}")
            total_draft_count = 0
        return total_draft_count

    def apply_batch_queue_sheet_formatting(self, sheets_service, spreadsheet_id):
        from datetime import datetime
        header, data, _ = self.get_batch_queue_data_and_header()
        
        requests = [
            # Title (Row 1) - Large, Bold, Center
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                            "textFormat": {
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                "fontSize": 18,
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            },
            # Date (Row 2) - Center, Medium
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 1,
                        "endRowIndex": 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
                            "textFormat": {
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                "fontSize": 11,
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            },
            # Header (Row 8) - Dark background, white text
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 7,
                        "endRowIndex": 8,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
                            "textFormat": {
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                "bold": True,
                                "fontSize": 10
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            },
            # Data rows (Row 9+) - Center aligned
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 8,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "textFormat": {
                                "fontSize": 9
                            }
                        }
                    },
                    "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat)"
                }
            },
            # Batch Number column - Bold
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 8,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                                "fontSize": 9
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat"
                }
            },
            # Set row heights
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": 0,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": 1
                    },
                    "properties": {
                        "pixelSize": 40
                    },
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": 0,
                        "dimension": "ROWS",
                        "startIndex": 3,
                        "endIndex": 6
                    },
                    "properties": {
                        "pixelSize": 30
                    },
                    "fields": "pixelSize"
                }
            },
            # Set column widths - all columns 120px
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": 0,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 9
                    },
                    "properties": {
                        "pixelSize": 120
                    },
                    "fields": "pixelSize"
                }
            }
        ]
        
        # Apply age-based colors to Created At column
        now = datetime.now()
        color_steps = [
            {"red": 0.992, "green": 0.733, "blue": 0.733},  # merah (oldest)
            {"red": 0.949, "green": 0.949, "blue": 0.733},
            {"red": 0.827, "green": 0.949, "blue": 0.733},
            {"red": 0.733, "green": 0.949, "blue": 0.949},
            {"red": 0.733, "green": 0.827, "blue": 0.949},
            {"red": 0.882, "green": 0.733, "blue": 0.949},  # ungu (newest)
        ]
        max_days = 30
        step = 5
        
        for idx, row in enumerate(data):
            # Get created_at from database
            created_at_str = ""
            try:
                batches_with_status = self.db_manager.get_all_batches_with_status_counts()
                for batch in batches_with_status:
                    if batch.get("batch_number") == row[0]:
                        created_at_str = batch.get("created_at", "")
                        break
            except Exception:
                created_at_str = ""
                
            try:
                created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                except Exception:
                    created_at = None
                    
            color = None
            if created_at:
                days_diff = (now - created_at).days
                if days_diff >= max_days:
                    color = color_steps[0]
                else:
                    color_idx = len(color_steps) - 1 - (days_diff // step)
                    if color_idx < 0:
                        color_idx = 0
                    elif color_idx >= len(color_steps):
                        color_idx = len(color_steps) - 1
                    color = color_steps[color_idx]
                    
            if color:
                # Apply color only to Created At column (index 8), starting from row 9 (index 8)
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 8 + idx,
                            "endRowIndex": 9 + idx,
                            "startColumnIndex": 8,
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color,
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 9
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
            
            # Apply light green color to non-zero status columns (Draft, Modelling, Rendering, Photoshop, Need Upload, Pending)
            # Columns: Draft=2, Modelling=3, Rendering=4, Photoshop=5, Need Upload=6, Pending=7
            status_columns = [2, 3, 4, 5, 6, 7]
            light_green = {"red": 0.85, "green": 0.95, "blue": 0.85}
            
            for col_idx in status_columns:
                try:
                    value = row[col_idx]
                    if value and int(value) != 0:
                        requests.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": 0,
                                    "startRowIndex": 8 + idx,
                                    "endRowIndex": 9 + idx,
                                    "startColumnIndex": col_idx,
                                    "endColumnIndex": col_idx + 1
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "backgroundColor": light_green
                                    }
                                },
                                "fields": "userEnteredFormat.backgroundColor"
                            }
                        })
                except (ValueError, TypeError):
                    pass
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        
        self.add_color_legend(sheets_service, spreadsheet_id)

    def create_batch_queue_spreadsheet(self):
        try:
            drive_service, sheets_service = self.get_google_services(require_sheets=True)
            if not drive_service or not sheets_service:
                return None

            rak_arsip_folder_id = self._rak_arsip_folder_id
            batch_folder_id = self._batch_folder_id

            if not rak_arsip_folder_id or not batch_folder_id:
                self.ensure_batch_folder_exist()
                rak_arsip_folder_id = self._rak_arsip_folder_id
                batch_folder_id = self._batch_folder_id

            if not batch_folder_id:
                print("BATCH folder not found, cannot create spreadsheet.")
                return None

            spreadsheet_body = {
                "properties": {
                    "title": "Batch Queue"
                }
            }
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body, fields="spreadsheetId").execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId")
            if not spreadsheet_id:
                print("Failed to create spreadsheet.")
                return None

            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=batch_folder_id,
                removeParents="root",
                fields="id, parents"
            ).execute()

            try:
                header, data, today_str = self.get_batch_queue_data_and_header()
                self.write_batch_queue_sheet_content(sheets_service, spreadsheet_id, header, data, today_str)
                self.apply_batch_queue_sheet_formatting(sheets_service, spreadsheet_id)
            except Exception as e:
                print(f"Failed to set A1/A2/header value or formatting: {e}")

            return spreadsheet_id
        except Exception as e:
            print(f"Error creating batch queue spreadsheet: {e}")
            return None

    def clean_batch_queue_spreadsheet(self, sheets_service, spreadsheet_id):
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range="A1:Z1000"
        ).execute()
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": 0
                        },
                        "fields": "userEnteredFormat"
                    }
                }
            ]}
        ).execute()

    def update_batch_queue_spreadsheet(self, spreadsheet_id):
        try:
            sheets_service = self._sheets_service
            if not sheets_service:
                return False

            header, data, today_str = self.get_batch_queue_data_and_header()
            self.clean_batch_queue_spreadsheet(sheets_service, spreadsheet_id)
            self.write_batch_queue_sheet_content(sheets_service, spreadsheet_id, header, data, today_str)
            self.apply_batch_queue_sheet_formatting(sheets_service, spreadsheet_id)
            return True
        except Exception as e:
            print(f"Failed to update Batch Queue spreadsheet: {e}")
            return False

    def start_sync_btn_blink(self):
        if not self._sync_blink_timer:
            self._sync_blink_state = False
            self._sync_blink_timer = QTimer(self)
            self._sync_blink_timer.timeout.connect(self._toggle_sync_btn_blink)
            self._sync_blink_timer.start(350)

    def stop_sync_btn_blink(self):
        if self._sync_blink_timer:
            self._sync_blink_timer.stop()
            self._sync_blink_timer = None
        self._sync_blink_state = False
        if self.batch_sync_drive_btn:
            self.batch_sync_drive_btn.setStyleSheet("")

    def _toggle_sync_btn_blink(self):
        self._sync_blink_state = not self._sync_blink_state
        if self.batch_sync_drive_btn:
            if self._sync_blink_state:
                self.batch_sync_drive_btn.setStyleSheet("background-color: rgba(255, 207, 36, 0.4);")
            else:
                self.batch_sync_drive_btn.setStyleSheet("")

    def on_sync_drive_clicked(self):
        # Check if thread exists and is still running
        if self._sync_thread is not None:
            try:
                if self._sync_thread.isRunning():
                    logging.warning("Sync already in progress, skipping new sync request.")
                    return
            except RuntimeError:
                # Thread object was deleted, reset reference
                self._sync_thread = None
                self._sync_worker = None
        
        self.start_sync_btn_blink()
        self._sync_thread = QThread()
        self._sync_worker = SyncDriveWorker(self)
        self._sync_worker.moveToThread(self._sync_thread)
        self._sync_thread.started.connect(self._sync_worker.run)
        self._sync_worker.finished.connect(self._on_sync_drive_finished)
        self._sync_worker.message.connect(self._on_sync_drive_message)
        self._sync_worker.finished.connect(self._sync_thread.quit)
        self._sync_worker.finished.connect(self._sync_worker.deleteLater)
        self._sync_thread.finished.connect(self._sync_thread.deleteLater)
        self._sync_thread.finished.connect(self._on_thread_cleanup)
        self._sync_thread.start()
        logging.debug("BatchManagementDialog: Sync thread started.")

    def _on_sync_drive_finished(self):
        self.stop_sync_btn_blink()
        logging.debug("BatchManagementDialog: Sync thread finished.")

    def _on_thread_cleanup(self):
        self._sync_thread = None
        self._sync_worker = None
        logging.debug("BatchManagementDialog: Thread cleanup completed.")

    def _on_sync_drive_message(self, msg):
        print(msg)
        logging.info(f"SyncDriveWorker message: {msg}")

def time_ago(dt_str):
    """Convert datetime string to 'x days ago' style."""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        except Exception:
            return dt_str
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 30 * 86400:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 365 * 86400:
        months = int(seconds // (30 * 86400))
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds // (365 * 86400))
        return f"{years} year{'s' if years > 1 else ''} ago"