from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from helpers.database_setup_helper import DatabaseSetupHelper


class DatabaseSetupDialog(QDialog):
    def __init__(self, basedir, db_manager_factory=None, parent=None, first_launch=False):
        super().__init__(parent)
        self.basedir = basedir
        self.db_manager_factory = db_manager_factory
        self.first_launch = first_launch
        self.helper = DatabaseSetupHelper(basedir)
        self._last_test_success = False

        self.setWindowTitle("Database Setup")
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())
        self.setModal(True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(420, 0)

        self._build_ui()
        self._load_current_values()
        self._update_cancel_availability()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Configure a PostgreSQL connection for local installs, Supabase, or other PostgreSQL-compatible services."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItem("Local PostgreSQL", "local")
        self.connection_type_combo.addItem("Supabase", "supabase")
        self.connection_type_combo.addItem("Custom", "custom")
        self.connection_type_combo.currentIndexChanged.connect(self._apply_selected_preset)
        form_layout.addRow(self._make_label("Connection Type", "fa6s.server"), self.connection_type_combo)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("localhost or db.project.supabase.co")
        form_layout.addRow(self._make_label("Host", "fa6s.network-wired"), self._create_paste_field(self.host_edit))

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("5432")
        form_layout.addRow(self._make_label("Port", "fa6s.plug"), self._create_paste_field(self.port_edit))

        self.database_edit = QLineEdit()
        form_layout.addRow(self._make_label("Database Name", "fa6s.database"), self._create_paste_field(self.database_edit))

        self.username_edit = QLineEdit()
        form_layout.addRow(self._make_label("Username", "fa6s.user"), self._create_paste_field(self.username_edit))

        password_widget = QWidget()
        password_layout = QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(6)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_paste_btn = self._create_paste_button(self.password_edit)
        self.password_toggle_btn = QPushButton(qta.icon("fa6s.eye"), "")
        self.password_toggle_btn.setCheckable(True)
        self.password_toggle_btn.setFixedWidth(32)
        self.password_toggle_btn.clicked.connect(self._toggle_password_visibility)
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.password_paste_btn)
        password_layout.addWidget(self.password_toggle_btn)
        form_layout.addRow(self._make_label("Password", "fa6s.key"), password_widget)

        self.sslmode_combo = QComboBox()
        for mode in self.helper.SSL_MODES:
            self.sslmode_combo.addItem(mode)
        form_layout.addRow(self._make_label("SSL Mode", "fa6s.lock"), self.sslmode_combo)

        layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.test_button = QPushButton(qta.icon("fa6s.plug-circle-check"), "Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_row.addWidget(self.test_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            parent=self,
        )
        save_button = self.button_box.button(QDialogButtonBox.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        if save_button is not None:
            save_button.setText("Save Connection")
            save_button.setIcon(qta.icon("fa6s.floppy-disk"))
        if cancel_button is not None:
            cancel_button.setIcon(qta.icon("fa6s.xmark"))
        self.button_box.accepted.connect(self.save_connection)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _make_label(self, text, icon_name):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addStretch()
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name).pixmap(16, 16))
        row.addWidget(icon)
        row.addWidget(QLabel(text))
        return container

    def _create_paste_field(self, line_edit):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(line_edit)
        row.addWidget(self._create_paste_button(line_edit))
        return container

    def _create_paste_button(self, target_widget):
        button = QPushButton(qta.icon("fa6s.paste"), "")
        button.setToolTip("Paste from clipboard")
        button.setFixedWidth(32)
        button.clicked.connect(lambda: self._paste_into_widget(target_widget))
        return button

    def _paste_into_widget(self, target_widget):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            target_widget.setText(text.strip())

    def _load_current_values(self):
        current = self.helper.get_current_config()
        connection_type = self.helper.infer_connection_type(current)
        index = self.connection_type_combo.findData(connection_type)
        if index >= 0:
            self.connection_type_combo.setCurrentIndex(index)
        self._fill_fields(current)
        if self.first_launch:
            self.status_label.setText("Database configuration is required before the application can be used.")

    def _fill_fields(self, values):
        self.host_edit.setText(values.get("host", ""))
        self.port_edit.setText(str(values.get("port", "5432")))
        self.database_edit.setText(values.get("database", ""))
        self.username_edit.setText(values.get("username", ""))
        self.password_edit.setText(values.get("password", ""))
        sslmode = values.get("sslmode", "prefer")
        ssl_index = self.sslmode_combo.findText(sslmode)
        self.sslmode_combo.setCurrentIndex(ssl_index if ssl_index >= 0 else self.sslmode_combo.findText("prefer"))
        self._last_test_success = False

    def _apply_selected_preset(self):
        current_type = self.connection_type_combo.currentData()
        current_values = self._collect_form_values()
        preset = self.helper.get_preset_values(current_type)

        merged = {
            "host": preset["host"] or current_values["host"],
            "port": preset["port"] or current_values["port"],
            "database": preset["database"] or current_values["database"],
            "username": preset["username"] or current_values["username"],
            "password": current_values["password"],
            "sslmode": preset["sslmode"] or current_values["sslmode"],
        }
        if current_type == "custom":
            merged["host"] = current_values["host"]
            merged["database"] = current_values["database"]
            merged["username"] = current_values["username"]
            merged["port"] = current_values["port"]
            merged["sslmode"] = current_values["sslmode"]
        self._fill_fields(merged)
        if current_type == "supabase":
            self.status_label.setText("Supabase preset selected. SSL mode will use 'require'.")
            self.status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        elif self.first_launch:
            self.status_label.setText("Database configuration is required before the application can be used.")
            self.status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        else:
            self.status_label.setText("")

    def _update_cancel_availability(self):
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setEnabled(not self.first_launch)
            cancel_button.setVisible(not self.first_launch)

    def _toggle_password_visibility(self):
        if self.password_toggle_btn.isChecked():
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_toggle_btn.setIcon(qta.icon("fa6s.eye-slash"))
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_toggle_btn.setIcon(qta.icon("fa6s.eye"))

    def _collect_form_values(self):
        return {
            "host": self.host_edit.text().strip(),
            "port": self.port_edit.text().strip(),
            "database": self.database_edit.text().strip(),
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "sslmode": self.sslmode_combo.currentText(),
        }

    def test_connection(self):
        config = self._collect_form_values()
        success, message = self.helper.test_connection(config)
        self._last_test_success = success
        if success:
            details = f"{config['host']}:{config['port']} / {config['database']} / sslmode={config['sslmode']}"
            self.status_label.setText(f"Connection successful. {details}")
            self.status_label.setStyleSheet("color: #43a047; font-weight: bold;")
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def save_connection(self):
        config = self._collect_form_values()
        errors = self.helper.validate_config(config)
        if errors:
            QMessageBox.warning(self, "Validation Failed", "\n".join(errors))
            self.status_label.setText("Input validation failed.")
            self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            return

        if not self._last_test_success:
            success, message = self.helper.test_connection(config)
            if not success:
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                QMessageBox.critical(self, "Connection Failed", message)
                return

        connection_type = self.connection_type_combo.currentData()
        self.helper.save_config(config, connection_type)

        if self.db_manager_factory is not None:
            try:
                db_manager = self.db_manager_factory()
                db_manager.connection_helper.ensure_database_exists()
                db_manager.backup_helper.auto_backup_database_hourly()
                db_manager.backup_helper.setup_auto_backup_timer()
            except Exception as exc:
                message = self.helper.format_connection_error(exc, config)
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                QMessageBox.critical(self, "Database Setup Failed", message)
                return

        details = f"Connection saved to .env: {config['host']}:{config['port']} / {config['database']} / sslmode={config['sslmode']}"
        self.status_label.setText(details)
        self.status_label.setStyleSheet("color: #43a047; font-weight: bold;")
        QMessageBox.information(self, "Database Connection Saved", details)
        self.accept()

    @staticmethod
    def open_dialog(basedir, db_manager_factory=None, parent=None, first_launch=False):
        dialog = DatabaseSetupDialog(
            basedir=basedir,
            db_manager_factory=db_manager_factory,
            parent=parent,
            first_launch=first_launch,
        )
        return dialog.exec()
