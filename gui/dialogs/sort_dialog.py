from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox, QWidget, QLineEdit
from PySide6.QtCore import Qt
import qtawesome as qta
from helpers.show_statusbar_helper import show_statusbar_message

class SortDialog(QDialog):
    def __init__(self, status_options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sort Table")
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())
        
        main_layout = QVBoxLayout(self)
        main_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        def create_icon_label(text, icon_name):
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(6)
            h_layout.addStretch()
            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_name).pixmap(16, 16))
            h_layout.addWidget(icon_lbl)
            text_lbl = QLabel(text)
            h_layout.addWidget(text_lbl)
            return container
        
        self.field_combo = QComboBox()
        self.field_combo.setMinimumWidth(200)
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
        form_layout.addRow(create_icon_label("Sort by:", "fa6s.arrow-down-wide-short"), self.field_combo)
        
        self.status_combo = QComboBox()
        self.status_combo.setMinimumWidth(200)
        self.status_combo.addItem("All")
        self.status_options = list(status_options) if status_options else []
        for status in self.status_options:
            self.status_combo.addItem(status)
        self.status_combo.setEnabled(False)
        self.status_label = create_icon_label("Status:", "fa6s.filter")
        self.status_row_index = form_layout.rowCount()
        form_layout.addRow(self.status_label, self.status_combo)
        
        self.root_combo = QComboBox()
        self.root_combo.setMinimumWidth(200)
        self.root_combo.setEnabled(False)
        self.root_label = create_icon_label("Root:", "fa6s.code-branch")
        self.root_row_index = form_layout.rowCount()
        form_layout.addRow(self.root_label, self.root_combo)
        
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(200)
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
        self.client_label = create_icon_label("Client:", "fa6s.user")
        self.client_row_index = form_layout.rowCount()
        form_layout.addRow(self.client_label, self.client_combo)
        
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumWidth(200)
        self.batch_combo.setEnabled(False)
        self.batch_label = create_icon_label("Batch:", "fa6s.box")
        self.batch_row_index = form_layout.rowCount()
        form_layout.addRow(self.batch_label, self.batch_combo)
        
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self.category_combo.setEditable(True)
        self.category_combo.setEnabled(False)
        self.category_list = []
        self.category_combo.addItem("")
        if self.db_manager:
            self.category_list = self.db_manager.get_all_categories()
            for cat in self.category_list:
                self.category_combo.addItem(cat)
        self.category_label = create_icon_label("Category:", "fa6s.folder")
        self.category_row_index = form_layout.rowCount()
        form_layout.addRow(self.category_label, self.category_combo)
        
        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setMinimumWidth(200)
        self.subcategory_combo.setEditable(True)
        self.subcategory_combo.setEnabled(False)
        self.subcategory_combo.addItem("")
        self.subcategory_label = create_icon_label("SubCat:", "fa6s.folder-open")
        self.subcategory_row_index = form_layout.rowCount()
        form_layout.addRow(self.subcategory_label, self.subcategory_combo)
        
        self.order_combo = QComboBox()
        self.order_combo.setMinimumWidth(200)
        self.order_combo.addItems(["Ascending", "Descending"])
        self.order_combo.setCurrentIndex(1)
        form_layout.addRow(create_icon_label("Order:", "fa6s.sort"), self.order_combo)
        
        main_layout.addLayout(form_layout)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        ok_btn = self.button_box.button(QDialogButtonBox.Ok)
        cancel_btn = self.button_box.button(QDialogButtonBox.Cancel)
        if ok_btn is not None:
            ok_btn.setIcon(qta.icon("fa6s.floppy-disk"))
        if cancel_btn is not None:
            cancel_btn.setIcon(qta.icon("fa6s.xmark"))

        self.setLayout(main_layout)

        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        self.root_combo.currentIndexChanged.connect(self._on_root_changed)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self._on_field_changed(0)
        self._update_ok_button_state()

    def _on_field_changed(self, idx):
        field = self.sort_fields[self.field_combo.currentIndex()][1]
        
        is_status = field == "status"
        self.status_combo.setEnabled(is_status)
        self.status_label.setVisible(is_status)
        self.status_combo.setVisible(is_status)
        
        is_batch = field == "batch_number"
        self.client_combo.setEnabled(is_batch)
        self.client_label.setVisible(is_batch)
        self.client_combo.setVisible(is_batch)
        self.batch_label.setVisible(is_batch)
        self.batch_combo.setVisible(is_batch)
        self.batch_combo.setEnabled(is_batch and self.client_combo.currentData() is not None)
        
        is_root = field == "root"
        self.root_combo.setEnabled(is_root)
        self.root_label.setVisible(is_root)
        self.root_combo.setVisible(is_root)
        
        is_category = field == "category"
        self.category_combo.setEnabled(is_category)
        self.category_label.setVisible(is_category)
        self.category_combo.setVisible(is_category)
        self.subcategory_combo.setEnabled(is_category and bool(self.category_combo.currentText().strip()))
        self.subcategory_label.setVisible(is_category)
        self.subcategory_combo.setVisible(is_category)
        
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
        self.adjustSize()

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
                    if isinstance(batch, tuple):
                        batch_number = batch[0]
                    else:
                        batch_number = batch
                    self.batch_combo.addItem(str(batch_number))
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
