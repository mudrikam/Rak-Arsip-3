from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QLabel, QComboBox, QSpinBox,
    QMessageBox, QMenu, QDateTimeEdit, QCheckBox
)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt, QDateTime, QTimer, QThread, Signal, QObject
import qtawesome as qta
from datetime import datetime, timedelta

class SyncDriveWorker(QObject):
    finished = Signal()
    message = Signal(str)
    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog

    def run(self):
        try:
            drive_service, sheets_service = self.dialog.get_google_services(require_sheets=True)
            if not drive_service or not sheets_service:
                self.message.emit("Google Drive/Sheets service not available.")
                return

            self.dialog.ensure_batch_folder_exist()
            rak_arsip_folder_id = self.dialog._rak_arsip_folder_id
            batch_folder_id = self.dialog._batch_folder_id

            if not rak_arsip_folder_id or not batch_folder_id:
                self.message.emit("Rak_Arsip_Database or BATCH folder not found or failed to create.")
                return

            self.message.emit("Checking for Batch Queue spreadsheet in BATCH folder...")
            results = drive_service.files().list(
                q=f"name = 'Batch Queue' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{batch_folder_id}' in parents and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            spreadsheets = results.get('files', [])
            if spreadsheets:
                spreadsheet_id = spreadsheets[0]['id']
                self.message.emit(f"Batch Queue spreadsheet already exists: {spreadsheets[0]['name']}")
                self.dialog.update_batch_queue_spreadsheet(spreadsheet_id)
                self.message.emit("Batch Queue spreadsheet updated with latest data.")
            else:
                self.message.emit("Batch Queue spreadsheet not found, creating...")
                spreadsheet_id = self.dialog.create_batch_queue_spreadsheet()
                if spreadsheet_id:
                    self.message.emit(f"Batch Queue spreadsheet created with ID: {spreadsheet_id}")
                else:
                    self.message.emit("Failed to create Batch Queue spreadsheet.")
        except Exception as e:
            self.message.emit(f"Sync to Drive error: {e}")
        finally:
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
        self._rak_arsip_folder_id = None
        self._batch_folder_id = None
        self._drive_service = None
        self._sheets_service = None
        self._credentials = None
        self._sync_blink_timer = None
        self._sync_blink_state = False
        self._sync_thread = None
        self._sync_worker = None
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
        row.addWidget(QLabel("Sort by:"))
        row.addWidget(self.batch_sort_combo)
        row.addWidget(self.batch_sort_order_combo)
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

        self.batch_sync_drive_btn = QPushButton(qta.icon("fa6s.cloud-arrow-up"), "Sync to Drive")
        pagination_layout.addWidget(self.batch_sync_drive_btn)

        layout.addLayout(pagination_layout)

        # STATISTICS ROW
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

        self.batch_refresh_btn.clicked.connect(self.load_batch_data)
        self.batch_search_edit.textChanged.connect(self.update_batch_table)
        self.batch_sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        self.batch_sort_order_combo.currentIndexChanged.connect(self.on_sort_changed)
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
        self.batch_sync_drive_btn.clicked.connect(self.on_sync_drive_clicked)

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
        hide_finished = self.hide_finished_checkbox.isChecked()
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
        if hide_finished:
            filtered = [row for row in filtered if str(row[2]).strip().lower() != "finished"]
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

        self.batch_table.setRowCount(len(page_data))
        for row_idx, (client_name, batch_number, note, file_count, created_at, client_id) in enumerate(page_data):
            client_item = QTableWidgetItem(str(client_name))
            batch_item = QTableWidgetItem(str(batch_number))
            note_item = QTableWidgetItem(str(note))
            count_item = QTableWidgetItem(str(file_count))
            created_item = QTableWidgetItem(str(created_at) if created_at else "")
            if str(note).strip().lower() == "finished":
                green = QColor("#43a047")
                green.setAlpha(80)
                for item in (client_item, batch_item, note_item, count_item, created_item):
                    item.setBackground(green)
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
            if str(row[2]).strip().lower() != "finished":
                queue_batches.append(row)
                queue_files += int(row[3]) if row[3] else 0
        self.stats_total_files_label.setText(f"Total Batches: {total_batch} ({total_files} files)")
        self.stats_batch_queue_label.setText(f"Batch Queue: {len(queue_batches)} ({queue_files} files)")

        hide_finished = self.hide_finished_checkbox.isChecked()
        if hide_finished:
            filtered_rows = [row for row in self._batch_data_all if str(row[2]).strip().lower() != "finished"]
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

    def on_hide_finished_changed(self, state):
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

            if self._drive_service and (not require_sheets or self._sheets_service):
                return self._drive_service, self._sheets_service

            creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "credentials_config.json")
            if not os.path.exists(creds_path):
                print(f"Credentials file not found: {creds_path}")
                return None, None

            scopes = ["https://www.googleapis.com/auth/drive"]
            if require_sheets:
                scopes.append("https://www.googleapis.com/auth/spreadsheets")
            credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
            drive_service = build('drive', 'v3', credentials=credentials)
            sheets_service = None
            if require_sheets:
                sheets_service = build('sheets', 'v4', credentials=credentials)
            self._drive_service = drive_service
            self._sheets_service = sheets_service
            self._credentials = credentials
            return drive_service, sheets_service
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
        header = [
            "Batch Number", "File Count", "Created At"
        ]
        data = []
        for row in self._batch_data_all:
            note = row[2]
            if str(note).strip().lower() == "finished":
                continue
            batch_number = row[1]
            file_count = row[3]
            created_at = row[4]
            created_at_ago = time_ago(created_at)
            data.append((batch_number, file_count, created_at_ago, created_at))
        # Sort ascending by created_at (oldest at top)
        data.sort(key=lambda x: x[3] if x[3] else "", reverse=False)
        data = [[d[0], d[1], d[2], d[3]] for d in data]
        today_str = datetime.now().strftime("%Y-%m-%d")
        return header, data, today_str

    def write_batch_queue_sheet_content(self, sheets_service, spreadsheet_id, header, data, today_str):
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="USER_ENTERED",
            body={"values": [["DESAINIA STUDIO BATCH QUEUE"]]
        }).execute()
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A2",
            valueInputOption="USER_ENTERED",
            body={"values": [[today_str]]}
        ).execute()
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A5",
            valueInputOption="USER_ENTERED",
            body={"values": [header] + [row[:3] for row in data]}
        ).execute()
        self.add_color_legend(sheets_service, spreadsheet_id)

    def add_color_legend(self, sheets_service, spreadsheet_id):
        color_steps = [
            {"red": 0.992, "green": 0.733, "blue": 0.733},  # merah (oldest)
            {"red": 0.949, "green": 0.949, "blue": 0.733},
            {"red": 0.827, "green": 0.949, "blue": 0.733},
            {"red": 0.733, "green": 0.949, "blue": 0.949},
            {"red": 0.733, "green": 0.827, "blue": 0.949},
            {"red": 0.882, "green": 0.733, "blue": 0.949},  # ungu (newest)
        ]
        legend_labels = [
            "Active task (highest priority, oldest in queue)",
            "Critical task (very high priority)",
            "Ongoing task (moderate priority)",
            "Backlog task (moderate-low priority)",
            "Incoming batch (just added)",
            "New batch (newest, lowest priority)",
        ]
        legend_values = [["", desc] for desc in legend_labels]
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="E5",
            valueInputOption="USER_ENTERED",
            body={"values": legend_values}
        ).execute()
        total_queue, total_file_queue = self._get_total_queue_and_files()
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="E11",
            valueInputOption="USER_ENTERED",
            body={"values": [["Total Queue", total_queue]]}
        ).execute()
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="E12",
            valueInputOption="USER_ENTERED",
            body={"values": [["Total File Queue", total_file_queue]]}
        ).execute()
        requests = []
        for i, color in enumerate(color_steps):
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 4 + i,
                        "endRowIndex": 5 + i,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
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
            if str(note).strip().lower() != "finished":
                total_queue += 1
                try:
                    total_file_queue += int(row[3]) if row[3] else 0
                except Exception:
                    pass
        return total_queue, total_file_queue

    def apply_batch_queue_sheet_formatting(self, sheets_service, spreadsheet_id):
        from datetime import datetime
        header, data, _ = self.get_batch_queue_data_and_header()
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "fontSize": 16,
                                "bold": True
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat"
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 1,
                        "endRowIndex": 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment"
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 4,
                        "endRowIndex": 5,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0, "green": 0, "blue": 0},
                            "textFormat": {
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment"
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 5,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat.horizontalAlignment"
                }
            }
        ]
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
            created_at_str = row[3]
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
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 5 + idx,
                            "endRowIndex": 6 + idx,
                            "startColumnIndex": 0,
                            "endColumnIndex": 3
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })
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

    def update_batch_queue_spreadsheet(self, spreadsheet_id):
        try:
            sheets_service = self._sheets_service
            if not sheets_service:
                return False

            header, data, today_str = self.get_batch_queue_data_and_header()
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range="A6:C1000"
            ).execute()
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
        self._sync_thread.start()

    def _on_sync_drive_finished(self):
        self.stop_sync_btn_blink()

    def _on_sync_drive_message(self, msg):
        print(msg)

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