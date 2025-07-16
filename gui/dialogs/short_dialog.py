from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
import qtawesome as qta

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

        # Order selection
        order_row = QHBoxLayout()
        order_row.addWidget(QLabel("Order:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Ascending", "Descending"])
        self.order_combo.setCurrentIndex(1)
        order_row.addWidget(self.order_combo)
        layout.addLayout(order_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        self._on_field_changed(0)

    def _on_field_changed(self, idx):
        # Enable status combo only if "Status" is selected
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        self.status_combo.setEnabled(field == "status")

    def get_sort_option(self, status_options):
        field_idx = self.field_combo.currentIndex()
        field = self.sort_fields[field_idx][1]
        order = "asc" if self.order_combo.currentIndex() == 0 else "desc"
        status_value = None
        if field == "status" and self.status_combo.currentIndex() > 0:
            status_value = self.status_options[self.status_combo.currentIndex() - 1]
        return field, order, status_value

    @staticmethod
    def sort_data(data, field, order, status_value=None):
        reverse = order == "desc"
        if field == "status" and status_value:
            def status_sort(row):
                return 0 if row.get("status") == status_value else 1
            return sorted(data, key=status_sort, reverse=reverse)
        else:
            def get_val(row):
                val = row.get(field)
                if val is None:
                    return ""
                return val
            return sorted(data, key=get_val, reverse=reverse)
