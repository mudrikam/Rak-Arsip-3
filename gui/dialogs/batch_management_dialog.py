from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QLabel, QComboBox, QSpinBox,
    QMessageBox, QMenu, QDateTimeEdit
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QDateTime
import qtawesome as qta

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
        self.init_ui()
        self.load_batch_data()

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
        layout.addLayout(pagination_layout)

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

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

    def load_batch_data(self):
        if not self.db_manager:
            self._batch_data_all = []
            self.update_batch_table()
            return
        # Ambil data batch lengkap (dengan client_name)
        batch_rows = self.db_manager.get_all_batches()
        batch_data = []
        for row in batch_rows:
            file_count = self.db_manager.count_file_client_batch_by_batch_number(row["batch_number"])
            batch_data.append((
                row["client_name"], row["batch_number"], row["note"], file_count, row["created_at"], row["client_id"]
            ))
        self._batch_data_all = batch_data
        self._batch_page = 1
        self.update_batch_table()

    def update_batch_table(self):
        search_text = self.batch_search_edit.text().strip().lower()
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
            self.batch_table.setItem(row_idx, 0, QTableWidgetItem(str(client_name)))
            self.batch_table.setItem(row_idx, 1, QTableWidgetItem(str(batch_number)))
            self.batch_table.setItem(row_idx, 2, QTableWidgetItem(str(note)))
            self.batch_table.setItem(row_idx, 3, QTableWidgetItem(str(file_count)))
            self.batch_table.setItem(row_idx, 4, QTableWidgetItem(str(created_at) if created_at else ""))

        self.batch_page_label.setText(f"Page {self._batch_page}/{self._batch_total_pages}")
        self.batch_prev_btn.setEnabled(self._batch_page > 1)
        self.batch_next_btn.setEnabled(self._batch_page < self._batch_total_pages)
        self.batch_page_spinner.blockSignals(True)
        self.batch_page_spinner.setMaximum(self._batch_total_pages)
        self.batch_page_spinner.setValue(self._batch_page)
        self.batch_page_spinner.blockSignals(False)

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
