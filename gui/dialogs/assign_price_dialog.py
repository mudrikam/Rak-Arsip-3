from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QWidget, QMessageBox, QInputDialog, QSizePolicy
from PySide6.QtCore import Qt, QObject, QEvent
import qtawesome as qta

class AssignPriceDialog(QDialog):
    def __init__(self, file_record, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Price")
        self.setMinimumWidth(500)
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.item_label = QLabel(file_record.get("name", ""))
        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("Enter price")
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["IDR", "USD"])
        self.currency_combo.setCurrentText("IDR")
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Enter note (optional)")
        file_id = file_record["id"]
        price, currency, note = db_manager.get_item_price_detail(file_id)
        try:
            price_float = float(price)
            if price_float.is_integer():
                price_display = str(int(price_float))
            else:
                price_display = str(price_float)
        except Exception:
            price_display = price
        self.price_edit.setText(price_display)
        self.currency_combo.setCurrentText(currency)
        self.note_edit.setText(note)
        form_layout.addRow(QLabel("Item Name:"), self.item_label)
        form_layout.addRow(QLabel("Price:"), self.price_edit)
        form_layout.addRow(QLabel("Currency:"), self.currency_combo)
        form_layout.addRow(QLabel("Note:"), self.note_edit)

        # Dropdown klien (urut A-Z)
        self.client_combo = QComboBox()
        clients = db_manager.get_all_clients()
        clients_sorted = sorted(clients, key=lambda c: c["client_name"].lower())
        self.client_combo.addItem("")
        for client in clients_sorted:
            self.client_combo.addItem(client["client_name"], client["id"])
        assigned_client_id = db_manager.get_assigned_client_id_for_file(file_id)
        if assigned_client_id:
            for idx in range(self.client_combo.count()):
                if self.client_combo.itemData(idx) == assigned_client_id:
                    self.client_combo.setCurrentIndex(idx)
                    break
        form_layout.addRow(QLabel("Client:"), self.client_combo)

        # Batch number dropdown + input + plus button
        batch_row = QHBoxLayout()
        self.batch_combo = QComboBox()
        self.batch_combo.setEditable(True)
        self.batch_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_record = file_record
        self.db_manager = db_manager
        self._parent = parent
        self._refresh_batch_combo()
        batch_row.addWidget(self.batch_combo)
        self.add_batch_btn = QPushButton()
        self.add_batch_btn.setIcon(qta.icon("fa6s.plus"))
        self.add_batch_btn.setFixedWidth(40)
        self.add_batch_btn.setToolTip("Add new batch number")
        batch_row.addWidget(self.add_batch_btn)
        self.edit_batch_btn = QPushButton()
        self.edit_batch_btn.setIcon(qta.icon("fa6s.pen"))
        self.edit_batch_btn.setFixedWidth(40)
        self.edit_batch_btn.setToolTip("Edit batch list (number, client, note)")
        batch_row.addWidget(self.edit_batch_btn)
        self.delete_batch_btn = QPushButton()
        self.delete_batch_btn.setIcon(qta.icon("fa6s.trash"))
        self.delete_batch_btn.setFixedWidth(40)
        self.delete_batch_btn.setToolTip("Delete batch number")
        batch_row.addWidget(self.delete_batch_btn)
        batch_row.addStretch()
        form_layout.addRow(QLabel("Batch Number:"), batch_row)

        # Set batch_combo to assigned batch if exists
        self._set_assigned_batch_combo()

        main_layout.addLayout(form_layout)

        earnings_label = QLabel("Earnings Share:")
        main_layout.addWidget(earnings_label)
        self.earnings_table = QTableWidget()
        self.earnings_table.setColumnCount(4)
        self.earnings_table.setHorizontalHeaderLabels([
            "Username", "Full Name", f"({self._get_operational_percentage()}% Opr)", "Note"
        ])
        self.earnings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.earnings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.earnings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.earnings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.earnings_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.earnings_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.earnings_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        main_layout.addWidget(self.earnings_table)

        add_row = QHBoxLayout()
        self.team_combo = QComboBox()
        teams = db_manager.get_all_teams()
        teams_sorted = sorted(teams, key=lambda t: t["username"].lower())
        self.team_combo.addItems([team["username"] for team in teams_sorted])
        add_row.addWidget(self.team_combo)
        self.add_team_btn = QPushButton()
        self.add_team_btn.setIcon(qta.icon("fa6s.plus"))
        self.add_team_btn.setFixedWidth(40)
        self.add_team_btn.setToolTip("Add team member to earnings")
        add_row.addWidget(self.add_team_btn)
        self.remove_team_btn = QPushButton()
        self.remove_team_btn.setIcon(qta.icon("fa6s.minus"))
        self.remove_team_btn.setFixedWidth(40)
        self.remove_team_btn.setToolTip("Remove selected team member from earnings")
        add_row.addWidget(self.remove_team_btn)
        self.edit_note_btn = QPushButton()
        self.edit_note_btn.setIcon(qta.icon("fa6s.pen"))
        self.edit_note_btn.setFixedWidth(40)
        self.edit_note_btn.setToolTip("Edit note for selected team member")
        add_row.addWidget(self.edit_note_btn)
        add_row.addStretch()
        main_layout.addLayout(add_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        self.add_team_btn.clicked.connect(self._on_add_team)
        self.remove_team_btn.clicked.connect(self._on_remove_selected_team)
        self.edit_note_btn.clicked.connect(self._on_edit_note)
        # Only save price on focus out, not on every textChanged
        self.price_edit.installEventFilter(self)
        self.currency_combo.currentTextChanged.connect(self._on_price_changed)
        self.note_edit.textChanged.connect(self._on_note_changed)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        self.add_batch_btn.clicked.connect(self._on_add_batch)
        self.edit_batch_btn.clicked.connect(self._on_edit_batch)
        self.delete_batch_btn.clicked.connect(self._on_delete_batch)
        self._last_client_id = self.client_combo.currentData()
        self.refresh_earnings_table()

    def eventFilter(self, obj, event):
        if obj == self.price_edit and event.type() == QEvent.FocusOut:
            self._on_price_changed()
        return super().eventFilter(obj, event)

    def _refresh_batch_combo(self):
        self.batch_combo.clear()
        batch_list = self.db_manager.get_all_batch_numbers()
        self.batch_combo.addItem("")
        for batch in batch_list:
            self.batch_combo.addItem(batch)

    def _set_assigned_batch_combo(self):
        file_id = self.file_record["id"]
        client_id = self.client_combo.currentData()
        batch_number = self.db_manager.get_assigned_batch_number(file_id, client_id)
        if batch_number:
            idx = self.batch_combo.findText(batch_number)
            if idx >= 0:
                self.batch_combo.setCurrentIndex(idx)
            else:
                self.batch_combo.addItem(batch_number)
                self.batch_combo.setCurrentText(batch_number)
        else:
            self.batch_combo.setCurrentIndex(0)

    def _on_add_batch(self):
        batch_number = self.batch_combo.currentText().strip()
        if not batch_number:
            QMessageBox.warning(self, "Input Error", "Batch number cannot be empty.")
            return
        if batch_number in [self.batch_combo.itemText(i) for i in range(self.batch_combo.count())]:
            QMessageBox.information(self, "Info", "Batch number already exists.")
            return
        clients = self.db_manager.get_all_clients()
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Client for Batch")
        layout = QFormLayout(dialog)
        client_combo = QComboBox(dialog)
        for client in clients:
            client_combo.addItem(client["client_name"], client["id"])
        layout.addRow("Assign Batch to Client:", client_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        def on_accept():
            client_id = client_combo.currentData()
            if not client_id:
                QMessageBox.warning(dialog, "Input Error", "Please select a client.")
                return
            self.db_manager.add_batch_number(batch_number, client_id=client_id)
            self._refresh_batch_combo()
            idx = self.batch_combo.findText(batch_number)
            if idx >= 0:
                self.batch_combo.setCurrentIndex(idx)
            dialog.accept()
        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(dialog.reject)
        dialog.exec()

    def _on_edit_batch(self):
        batch_number = self.batch_combo.currentText().strip()
        if not batch_number:
            QMessageBox.warning(self, "Input Error", "Batch number cannot be empty.")
            return
        clients = self.db_manager.get_all_clients()
        batch_note, batch_client_id = self.db_manager.get_batch_list_note_and_client(batch_number)
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Batch List")
        layout = QFormLayout(dialog)
        batch_number_edit = QLineEdit(batch_number)
        note_edit = QLineEdit(batch_note)
        client_combo = QComboBox(dialog)
        for client in clients:
            client_combo.addItem(client["client_name"], client["id"])
        if batch_client_id:
            idx = client_combo.findData(batch_client_id)
            if idx >= 0:
                client_combo.setCurrentIndex(idx)
        layout.addRow("Batch Number:", batch_number_edit)
        layout.addRow("Batch Note:", note_edit)
        layout.addRow("Assign Batch to Client:", client_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        def on_accept():
            new_batch_number = batch_number_edit.text().strip()
            new_note = note_edit.text()
            new_client_id = client_combo.currentData()
            if not new_batch_number:
                QMessageBox.warning(dialog, "Input Error", "Batch number cannot be empty.")
                return
            if not new_client_id:
                QMessageBox.warning(dialog, "Input Error", "Please select a client.")
                return
            if new_batch_number != batch_number:
                self.db_manager.update_batch_number_and_note_and_client(batch_number, new_batch_number, new_note, new_client_id)
            else:
                self.db_manager.update_batch_list_note_and_client(batch_number, new_note, new_client_id)
            self._refresh_batch_combo()
            idx = self.batch_combo.findText(new_batch_number)
            if idx >= 0:
                self.batch_combo.setCurrentIndex(idx)
            dialog.accept()
        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(dialog.reject)
        dialog.exec()

    def _on_delete_batch(self):
        batch_number = self.batch_combo.currentText().strip()
        if not batch_number:
            QMessageBox.warning(self, "Input Error", "Batch number cannot be empty.")
            return
        affected_count = self.db_manager.count_file_client_batch_by_batch_number(batch_number)
        msg1 = (
            f"Deleting batch number '{batch_number}' will also delete {affected_count} related record(s) in File Client Batch records.\n"
            "This will affect all files/projects using this batch number.\n\n"
            "Do you want to continue?"
        )
        reply1 = QMessageBox.warning(self, "Delete Batch", msg1, QMessageBox.Yes | QMessageBox.No)
        if reply1 == QMessageBox.Yes:
            msg2 = (
                f"Are you sure you want to permanently delete batch number '{batch_number}'?\n"
                "This action cannot be undone."
            )
            reply2 = QMessageBox.warning(self, "Are you sure?", msg2, QMessageBox.Yes | QMessageBox.No)
            if reply2 == QMessageBox.Yes:
                self.db_manager.delete_batch_and_file_client_batch(batch_number)
                self._refresh_batch_combo()
                self.batch_combo.setCurrentIndex(0)

    def _get_operational_percentage(self):
        return int(self._parent.config_manager.get("operational_percentage"))

    def refresh_earnings_table(self):
        file_id = self.file_record["id"]
        earnings = self.db_manager.get_earnings_by_file_id(file_id)
        self.earnings_table.setRowCount(len(earnings))
        price, currency, _ = self.db_manager.get_item_price_detail(file_id)
        for row_idx, earning in enumerate(earnings):
            item_username = QTableWidgetItem(earning["username"])
            item_fullname = QTableWidgetItem(earning["full_name"])
            try:
                amount_float = float(earning["amount"])
                amount_str = f"{int(amount_float):,}".replace(",", ".")
            except Exception:
                amount_str = str(earning["amount"])
            item_share = QTableWidgetItem(f"{currency} {amount_str}")
            item_note = QTableWidgetItem(str(earning.get("note", "")))
            self.earnings_table.setItem(row_idx, 0, item_username)
            self.earnings_table.setItem(row_idx, 1, item_fullname)
            self.earnings_table.setItem(row_idx, 2, item_share)
            self.earnings_table.setItem(row_idx, 3, item_note)

    def _get_current_operational_percentage(self):
        file_id = self.file_record["id"]
        earnings = self.db_manager.get_earnings_by_file_id(file_id)
        price, _, _ = self.db_manager.get_item_price_detail(file_id)
        if not earnings or not price or len(earnings) == 0:
            return None
        price_float = float(price)
        n = len(earnings)
        share_amount = float(earnings[0]["amount"])
        used_percentage = round((1 - (share_amount * n / price_float)) * 100)
        return used_percentage

    def _verify_operational_percentage(self):
        current_percent = self._get_current_operational_percentage()
        operational_percentage = self._get_operational_percentage()
        if current_percent is not None and current_percent != operational_percentage:
            reply = QMessageBox.warning(
                self,
                "Operational Percentage Changed",
                f"Current operational percentage ({current_percent}%) is different from config ({operational_percentage}%).\n"
                "Updating will apply the new operational percentage to all earnings for this record.\nContinue?",
                QMessageBox.Yes | QMessageBox.No
            )
            return reply == QMessageBox.Yes
        return True

    def _on_add_team(self):
        if not self._verify_operational_percentage():
            return
        username = self.team_combo.currentText()
        file_id = self.file_record["id"]
        note = ""
        operational_percentage = self._get_operational_percentage()
        self.db_manager.assign_earning_with_percentage(file_id, username, note, operational_percentage)
        self.refresh_earnings_table()

    def _on_remove_selected_team(self):
        selected_row = self.earnings_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a team member to remove.")
            return
        file_id = self.file_record["id"]
        earnings = self.db_manager.get_earnings_by_file_id(file_id)
        if selected_row >= len(earnings):
            QMessageBox.warning(self, "Invalid Selection", "Selected row is invalid.")
            return
        earning_id = earnings[selected_row]["id"]
        if not self._verify_operational_percentage():
            return
        self.db_manager.remove_earning(earning_id, file_id)
        self.refresh_earnings_table()

    def _on_edit_note(self):
        selected_row = self.earnings_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a team member to edit note.")
            return
        file_id = self.file_record["id"]
        earnings = self.db_manager.get_earnings_by_file_id(file_id)
        if selected_row >= len(earnings):
            QMessageBox.warning(self, "Invalid Selection", "Selected row is invalid.")
            return
        earning_id = earnings[selected_row]["id"]
        current_note = earnings[selected_row].get("note", "")
        new_note, ok = QInputDialog.getText(self, "Edit Note", "Enter note for this team member:", QLineEdit.Normal, current_note)
        if ok:
            self.db_manager.update_earning_note(earning_id, new_note)
            self.refresh_earnings_table()

    def _on_price_changed(self):
        price = self.price_edit.text().strip()
        currency = self.currency_combo.currentText()
        note = self.note_edit.text().strip()
        file_id = self.file_record["id"]
        operational_percentage = self._get_operational_percentage()
        if price:
            if not self._verify_operational_percentage():
                return
            self.db_manager.assign_price(file_id, price, currency, note)
            self.db_manager.update_earnings_shares_with_percentage(file_id, operational_percentage)
            self.refresh_earnings_table()

    def _on_note_changed(self):
        price = self.price_edit.text().strip()
        currency = self.currency_combo.currentText()
        note = self.note_edit.text().strip()
        file_id = self.file_record["id"]
        self.db_manager.assign_price(file_id, price, currency, note)

    def _on_client_changed(self):
        client_id = self.client_combo.currentData()
        file_id = self.file_record["id"]
        item_price_id = self.db_manager.get_item_price_id(file_id)
        # update file_client_price relation
        self.db_manager.update_file_client_relation(file_id, item_price_id, client_id)
        # update file_client_batch client_id if batch exists for old client
        old_client_id = self._last_client_id
        if old_client_id and client_id and old_client_id != client_id:
            self.db_manager.update_file_client_batch_client(file_id, old_client_id, client_id)
        self._last_client_id = client_id
        batch_number = self.batch_combo.currentText().strip()
        self._set_assigned_batch_combo()

    def _on_accept(self):
        price = self.price_edit.text().strip()
        currency = self.currency_combo.currentText()
        note = self.note_edit.text().strip()
        file_id = self.file_record["id"]
        self.db_manager.assign_price(file_id, price, currency, note)
        client_id = self.client_combo.currentData()
        item_price_id = self.db_manager.get_item_price_id(file_id)
        old_client_id = self._last_client_id
        self.db_manager.update_file_client_relation(file_id, item_price_id, client_id)
        # update file_client_batch client_id if batch exists for old client
        if old_client_id and client_id and old_client_id != client_id:
            self.db_manager.update_file_client_batch_client(file_id, old_client_id, client_id)
        self._last_client_id = client_id
        batch_number = self.batch_combo.currentText().strip()
        batch_list = [self.batch_combo.itemText(i) for i in range(self.batch_combo.count())]
        if batch_number and client_id and batch_number in batch_list:
            self.db_manager.assign_file_client_batch(file_id, client_id, batch_number)
        self.accept()