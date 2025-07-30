from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox, QWidget, QLineEdit
import qtawesome as qta
from helpers.show_statusbar_helper import show_statusbar_message

class SortDialog(QDialog):
    def __init__(self, status_options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sort Table")
        self.setWindowIcon(qta.icon("fa6s.arrow-down-wide-short"))
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)

        field_row = QHBoxLayout()
        field_row.setContentsMargins(0, 0, 0, 0)
        field_row.setSpacing(0)
        field_row.addWidget(QLabel("Sort by:"))
        self.field_combo = QComboBox()
        self.sort_fields = [
            ("Date", "date"),
            ("Name", "name"),
            ("Root", "root"),
            ("Path", "path"),
            ("Status", "status"),
            ("Category", "category"),
            ("Batch Number", "batch_number"),
        ]
        for label, _ in self.sort_fields:
            self.field_combo.addItem(label)
        field_row.addWidget(self.field_combo)
        layout.addLayout(field_row)

        self.status_row = QHBoxLayout()
        self.status_row.setContentsMargins(0, 0, 0, 0)
        self.status_row.setSpacing(0)
        self.status_row.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All")
        self.status_options = list(status_options) if status_options else []
        for status in self.status_options:
            self.status_combo.addItem(status)
        self.status_combo.setEnabled(False)
        self.status_row.addWidget(self.status_combo)
        self.status_row_widget = QWidget()
        self.status_row_widget.setLayout(self.status_row)
        self.status_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_row_widget)

        self.root_row = QHBoxLayout()
        self.root_row.setContentsMargins(0, 0, 0, 0)
        self.root_row.setSpacing(0)
        self.root_row.addWidget(QLabel("Root:"))
        self.root_combo = QComboBox()
        self.root_combo.setEnabled(False)
        self.root_row.addWidget(self.root_combo)
        self.root_row_widget = QWidget()
        self.root_row_widget.setLayout(self.root_row)
        self.root_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.root_row_widget)

        self.client_row = QHBoxLayout()
        self.client_row.setContentsMargins(0, 0, 0, 0)
        self.client_row.setSpacing(0)
        self.client_row.addWidget(QLabel("Client:"))
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
        self.client_row.addWidget(self.client_combo)
        self.client_row_widget = QWidget()
        self.client_row_widget.setLayout(self.client_row)
        self.client_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.client_row_widget)

        self.batch_row = QHBoxLayout()
        self.batch_row.setContentsMargins(0, 0, 0, 0)
        self.batch_row.setSpacing(0)
        self.batch_row.addWidget(QLabel("Batch:"))
        self.batch_combo = QComboBox()
        self.batch_combo.setEnabled(False)
        self.batch_row.addWidget(self.batch_combo)
        self.batch_row_widget = QWidget()
        self.batch_row_widget.setLayout(self.batch_row)
        self.batch_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.batch_row_widget)

        # --- Category & Subcategory filter ---
        self.category_row = QHBoxLayout()
        self.category_row.setContentsMargins(0, 0, 0, 0)
        self.category_row.setSpacing(0)
        self.category_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setEnabled(False)
        self.category_list = []
        self.category_combo.addItem("")
        if self.db_manager:
            self.category_list = self.db_manager.get_all_categories()
            for cat in self.category_list:
                self.category_combo.addItem(cat)
        self.category_row.addWidget(self.category_combo)
        self.category_row_widget = QWidget()
        self.category_row_widget.setLayout(self.category_row)
        self.category_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.category_row_widget)

        self.subcategory_row = QHBoxLayout()
        self.subcategory_row.setContentsMargins(0, 0, 0, 0)
        self.subcategory_row.setSpacing(0)
        self.subcategory_row.addWidget(QLabel("Subcategory:"))
        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(True)
        self.subcategory_combo.setEnabled(False)
        self.subcategory_combo.addItem("")
        self.subcategory_row.addWidget(self.subcategory_combo)
        self.subcategory_row_widget = QWidget()
        self.subcategory_row_widget.setLayout(self.subcategory_row)
        self.subcategory_row_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.subcategory_row_widget)

        order_row = QHBoxLayout()
        order_row.setContentsMargins(0, 0, 0, 0)
        order_row.setSpacing(0)
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
        self.root_combo.currentIndexChanged.connect(self._on_root_changed)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self._on_field_changed(0)
        self._update_ok_button_state()

    def _on_field_changed(self, idx):
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        self.status_combo.setEnabled(field == "status")
        self.status_row_widget.setVisible(field == "status")
        is_batch = field == "batch_number"
        self.client_combo.setEnabled(is_batch)
        self.client_row_widget.setVisible(is_batch)
        self.batch_row_widget.setVisible(is_batch)
        self.batch_combo.setEnabled(is_batch and self.client_combo.currentData() is not None)
        is_root = field == "root"
        self.root_combo.setEnabled(is_root)
        self.root_row_widget.setVisible(is_root)
        is_category = field == "category"
        self.category_combo.setEnabled(is_category)
        self.category_row_widget.setVisible(is_category)
        self.subcategory_combo.setEnabled(is_category and bool(self.category_combo.currentText().strip()))
        self.subcategory_row_widget.setVisible(is_category)
        if is_root and self.db_manager:
            self.root_combo.clear()
            roots = self.db_manager.get_all_roots()
            self.root_combo.addItem("All")
            for root in roots:
                self.root_combo.addItem(root)
        if is_category and self.db_manager:
            self.category_combo.clear()
            self.category_combo.addItem("")
            cats = self.db_manager.get_all_categories()
            for cat in cats:
                self.category_combo.addItem(cat)
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

    def _on_root_changed(self, idx):
        self._update_ok_button_state()

    def _on_category_changed(self, text):
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        if field == "category" and self.db_manager:
            cat = text.strip()
            self.subcategory_combo.clear()
            self.subcategory_combo.addItem("")
            if cat:
                subs = self.db_manager.get_subcategories_by_category(cat)
                for sub in subs:
                    self.subcategory_combo.addItem(sub)
                self.subcategory_combo.setEnabled(True)
            else:
                self.subcategory_combo.setEnabled(False)
        self._update_ok_button_state()

    def _update_ok_button_state(self):
        from PySide6.QtWidgets import QDialogButtonBox
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(client_id and batch_number))
        elif field == "category":
            cat = self.category_combo.currentText().strip()
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(cat))
        else:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_accept(self):
        field_idx = self.field_combo.currentIndex()
        field = self.sort_fields[field_idx][1]
        order = "asc" if self.order_combo.currentIndex() == 0 else "desc"
        status_value = None
        client_id = None
        batch_number = None
        root_value = None
        category_value = None
        subcategory_value = None
        if field == "status" and self.status_combo.currentIndex() > 0:
            status_value = self.status_options[self.status_combo.currentIndex() - 1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
        if field == "root" and self.root_combo.currentIndex() > 0:
            root_value = self.root_combo.currentText()
        if field == "category":
            category_value = self.category_combo.currentText().strip()
            subcategory_value = self.subcategory_combo.currentText().strip()
        show_statusbar_message(
            self,
            f"Sort dialog accepted: field={field}, order={order}, status={status_value if status_value else 'All'}, client_id={client_id if client_id else '-'}, batch={batch_number if batch_number else '-'}, root={root_value if root_value else 'All'}, category={category_value if category_value else '-'}, subcategory={subcategory_value if subcategory_value else '-'}"
        )
        self.accept()

    def get_sort_option(self, status_options):
        field_idx = self.field_combo.currentIndex()
        field = self.sort_fields[field_idx][1]
        order = "asc" if self.order_combo.currentIndex() == 0 else "desc"
        status_value = None
        client_id = None
        batch_number = None
        root_value = None
        category_value = None
        subcategory_value = None
        if field == "status" and self.status_combo.currentIndex() > 0:
            status_value = self.status_options[self.status_combo.currentIndex() - 1]
        if field == "batch_number":
            client_id = self.client_combo.currentData()
            batch_number = self.batch_combo.currentText().strip() if self.batch_combo.currentText().strip() else None
        if field == "root" and self.root_combo.currentIndex() > 0:
            root_value = self.root_combo.currentText()
        if field == "category":
            category_value = self.category_combo.currentText().strip()
            subcategory_value = self.subcategory_combo.currentText().strip()
        return field, order, status_value, client_id, batch_number, root_value, category_value, subcategory_value

    @staticmethod
    def sort_data(data, field, order, status_value=None, client_id=None, batch_number=None, root_value=None, category_value=None):
        reverse = order == "desc"
        if field == "status" and status_value:
            def status_sort(row):
                return 0 if row.get("status") == status_value else 1
            return sorted(data, key=status_sort, reverse=reverse)
        elif field == "batch_number" and client_id and batch_number:
            def batch_sort(row):
                return 0 if (row.get("client_id") == client_id and row.get("batch_number") == batch_number) else 1
            return sorted(data, key=batch_sort, reverse=reverse)
        elif field == "root" and root_value:
            def root_sort(row):
                return 0 if row.get("root") == root_value else 1
            return sorted(data, key=root_sort, reverse=reverse)
        elif field == "category" and category_value:
            def cat_sort(row):
                return 0 if row.get("category") == category_value else 1
            return sorted(data, key=cat_sort, reverse=reverse)
        else:
            def get_val(row):
                val = row.get(field)
                if val is None:
                    return ""
                return val
            return sorted(data, key=get_val, reverse=reverse)
            return sorted(data, key=get_val, reverse=reverse)
