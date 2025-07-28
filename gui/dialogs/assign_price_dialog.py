from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QWidget, QMessageBox
from PySide6.QtCore import Qt
import qtawesome as qta

class AssignPriceDialog(QDialog):
    def __init__(self, file_record, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Price")
        self.setMinimumWidth(300)
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

        main_layout.addLayout(form_layout)

        self.file_record = file_record
        self.db_manager = db_manager
        self._parent = parent

        earnings_label = QLabel("Earnings (username, share):")
        main_layout.addWidget(earnings_label)
        self.earnings_table = QTableWidget()
        self.earnings_table.setColumnCount(3)
        self.earnings_table.setHorizontalHeaderLabels([
            "Username", "Full Name", f"({self._get_operational_percentage()}% Opr)"
        ])
        self.earnings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.earnings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.earnings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.earnings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.earnings_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.earnings_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
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
        add_row.addStretch()
        main_layout.addLayout(add_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        self.add_team_btn.clicked.connect(self._on_add_team)
        self.remove_team_btn.clicked.connect(self._on_remove_selected_team)
        self.price_edit.textChanged.connect(self._on_price_changed)
        self.currency_combo.currentTextChanged.connect(self._on_price_changed)
        self.note_edit.textChanged.connect(self._on_note_changed)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        self.refresh_earnings_table()

    def _get_operational_percentage(self):
        return int(self._parent.config_manager.get("operational_percentage"))

    def refresh_earnings_table(self):
        file_id = self.file_record["id"]
        earnings = self.db_manager.get_earnings_by_file_id(file_id)
        self.earnings_table.setRowCount(len(earnings))
        for row_idx, earning in enumerate(earnings):
            item_username = QTableWidgetItem(earning["username"])
            item_fullname = QTableWidgetItem(earning["full_name"])
            currency = earning.get("currency", None)
            if not currency:
                price, currency, _ = self.db_manager.get_item_price_detail(file_id)
            try:
                amount_float = float(earning["amount"])
                amount_str = f"{int(amount_float):,}".replace(",", ".")
            except Exception:
                amount_str = str(earning["amount"])
            item_share = QTableWidgetItem(f"{currency} {amount_str}")
            self.earnings_table.setItem(row_idx, 0, item_username)
            self.earnings_table.setItem(row_idx, 1, item_fullname)
            self.earnings_table.setItem(row_idx, 2, item_share)

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
        client_index = self.client_combo.currentIndex()
        client_id = self.client_combo.currentData()
        file_id = self.file_record["id"]
        item_price_id = self.db_manager.get_item_price_id(file_id)
        if client_id and item_price_id:
            self.db_manager.assign_file_client_price(file_id, item_price_id, client_id)

    def _on_accept(self):
        self._parent.refresh_table()
        self.accept()