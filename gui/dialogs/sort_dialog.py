from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
import qtawesome as qta
from helpers.show_statusbar_helper import show_statusbar_message

class SortDialog(QDialog):
    def __init__(self, status_options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sort Table")
        self.setWindowIcon(qta.icon("fa6s.arrow-down-wide-short"))
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)

        # Sort field selection
        field_row = QHBoxLayout()
        field_row.addWidget(QLabel("Sort by:"))
        self.field_combo = QComboBox()
        self.sort_fields = [
            ("Date", "date"),
            ("Name", "name"),
            ("Root", "root"),
            ("Path", "path"),
            ("Status", "status"),
            ("Category", "category"),
            ("Subcategory", "subcategory"),
            ("Batch Number", "batch_number"),
        ]
        for label, _ in self.sort_fields:
            self.field_combo.addItem(label)
        field_row.addWidget(self.field_combo)
        layout.addLayout(field_row)

        # Status filter (only enabled if Status is selected)
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All")
        self.status_options = list(status_options) if status_options else []
        for status in self.status_options:
            self.status_combo.addItem(status)
        self.status_combo.setEnabled(False)
        status_row.addWidget(self.status_combo)
        layout.addLayout(status_row)

        # Client filter (only enabled if Batch Number is selected)
        client_row = QHBoxLayout()
        client_row.addWidget(QLabel("Client:"))
        self.client_combo = QComboBox()
        self.client_combo.setEnabled(False)
        self.client_list = []
        self.client_id_map = {}
        self.db_manager = None
        if parent and hasattr(parent, "parent") and hasattr(parent.parent(), "db_manager"):
            self.db_manager = parent.parent().db_manager
        elif parent and hasattr(parent, "db_manager"):
            self.db_manager = parent.db_manager
        if self.db_manager:
            self.client_list = self.db_manager.get_all_clients_simple()
            self.client_combo.addItem("")
            for client in self.client_list:
                self.client_combo.addItem(client["client_name"], client["id"])
                self.client_id_map[client["id"]] = client["client_name"]
        client_row.addWidget(self.client_combo)
        layout.addLayout(client_row)

        # Batch list filter (only enabled if client selected)
        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("Batch:"))
        self.batch_combo = QComboBox()
        self.batch_combo.setEnabled(False)
        batch_row.addWidget(self.batch_combo)
        layout.addLayout(batch_row)

        # Order selection
        order_row = QHBoxLayout()
        order_row.addWidget(QLabel("Order:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Ascending", "Descending"])
        self.order_combo.setCurrentIndex(1)
        order_row.addWidget(self.order_combo)
        layout.addLayout(order_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        self._on_field_changed(0)
        self._update_ok_button_state()

    def _on_field_changed(self, idx):
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        self.status_combo.setEnabled(field == "status")
        is_batch = field == "batch_number"
        self.client_combo.setEnabled(is_batch)
        self.batch_combo.setEnabled(is_batch and self.client_combo.currentData() is not None)
        if not is_batch:
            self.client_combo.setCurrentIndex(0)
            self.batch_combo.clear()
            self.batch_combo.setEnabled(False)
        self._update_ok_button_state()

    def _on_client_changed(self, idx):
        client_id = self.client_combo.currentData()
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        if field == "batch_number" and client_id:
            self.batch_combo.setEnabled(True)
            if self.db_manager:
                batch_list = self.db_manager.get_batch_numbers_by_client(client_id)
                self.batch_combo.clear()
                self.batch_combo.addItem("")
                for batch in batch_list:
                    self.batch_combo.addItem(batch)
        else:
            self.batch_combo.clear()
            self.batch_combo.setEnabled(False)
        self._update_ok_button_state()

    def _on_batch_changed(self, idx):
        self._update_ok_button_state()

    def _update_ok_button_state(self):
        from PySide6.QtWidgets import QDialogButtonBox
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(client_id and batch_number))
        else:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_accept(self):
        field_idx = self.field_combo.currentIndex()
        field = self.sort_fields[field_idx][1]
        order = "asc" if self.order_combo.currentIndex() == 0 else "desc"
        status_value = None
        client_id = None
        batch_number = None
        if field == "status" and self.status_combo.currentIndex() > 0:
            status_value = self.status_options[self.status_combo.currentIndex() - 1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
        show_statusbar_message(
            self,
            f"Sort dialog accepted: field={field}, order={order}, status={status_value if status_value else 'All'}, client_id={client_id if client_id else '-'}, batch={batch_number if batch_number else '-'}"
        )
        self.accept()

    def get_sort_option(self, status_options):
        field_idx = self.field_combo.currentIndex()
        field = self.sort_fields[field_idx][1]
        order = "asc" if self.order_combo.currentIndex() == 0 else "desc"
        status_value = None
        client_id = None
        batch_number = None
        if field == "status" and self.status_combo.currentIndex() > 0:
            status_value = self.status_options[self.status_combo.currentIndex() - 1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
        return field, order, status_value, client_id, batch_number

    @staticmethod
    def sort_data(data, field, order, status_value=None, client_id=None, batch_number=None):
        reverse = order == "desc"
        if field == "status" and status_value:
            def status_sort(row):
                return 0 if row.get("status") == status_value else 1
            return sorted(data, key=status_sort, reverse=reverse)
        elif field == "batch_number" and client_id and batch_number:
            def batch_sort(row):
                return 0 if (row.get("client_id") == client_id and row.get("batch_number") == batch_number) else 1
            return sorted(data, key=batch_sort, reverse=reverse)
        else:
            def get_val(row):
                val = row.get(field)
                if val is None:
                    return ""
                return val
            return sorted(data, key=get_val, reverse=reverse)
