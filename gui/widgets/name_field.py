from PySide6.QtWidgets import QFrame, QVBoxLayout, QLineEdit, QCheckBox, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal
import qtawesome as qta
import os

class NameFieldWidget(QFrame):
    folder_created = Signal(str, str, str, str, str, str, int)  # date, name, root, path, category, subcategory, template_id
    project_created = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)

        input_row = QHBoxLayout()
        self.line_edit = QLineEdit(self)
        self.line_edit.setMinimumHeight(40)
        self.line_edit.setStyleSheet("font-size: 20px;")
        input_row.addWidget(self.line_edit)

        self.make_btn = QPushButton("Make", self)
        self.make_btn.setIcon(qta.icon("fa6s.play"))
        self.make_btn.setFixedSize(80, 36)
        self.make_btn.setToolTip("Make")
        self.make_btn.setCursor(Qt.PointingHandCursor)
        self.make_btn.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        input_row.addWidget(self.make_btn)

        self.star_btn = QPushButton(self)
        self.star_btn.setIcon(qta.icon("fa6s.star"))
        self.star_btn.setFixedSize(36, 36)
        self.star_btn.setToolTip("Star")
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self.star_btn.setStyleSheet("border: none;")
        input_row.addWidget(self.star_btn)

        layout.addLayout(input_row)

        sanitize_row = QHBoxLayout()
        self.clear_btn = QPushButton(self)
        self.clear_btn.setIcon(qta.icon("fa6s.xmark"))
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setToolTip("Clear")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("border: none;")
        self.sanitize_check = QCheckBox("Sanitize Name", self)
        self.folder_icon_label = QLabel(self)
        self.folder_icon_label.setPixmap(qta.icon("fa6s.folder", color="#1976d2").pixmap(20, 20))
        self.sanitize_label = QLabel("-", self)
        self.sanitize_label.setStyleSheet("color: #1976d2;")
        sanitize_row.addWidget(self.clear_btn)
        sanitize_row.addWidget(self.sanitize_check)
        sanitize_row.addWidget(self.folder_icon_label)
        sanitize_row.addWidget(self.sanitize_label)
        sanitize_row.addStretch()
        layout.addLayout(sanitize_row)
        self.setLayout(layout)

        self._forbidden_chars = '<>:"/\\|?*#&$%@!^()[]{};=+`~\''
        self._current_path_data = None
        self.db_manager = None
        self.selected_template_id = None

        self.line_edit.textChanged.connect(self._on_text_changed)
        self.sanitize_check.stateChanged.connect(self._on_sanitize_check_changed)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.make_btn.clicked.connect(self._on_make_clicked)
        self._block_signal = False

    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        print(f"Database manager set: {self.db_manager is not None}")

    def set_selected_template(self, template_id):
        self.selected_template_id = template_id

    def get_db_manager_from_parent(self):
        current = self.parent()
        while current:
            if hasattr(current, 'db_manager'):
                return current.db_manager
            current = current.parent()
        return None

    def _sanitize_text(self, text):
        sanitized = text.replace(" ", "_")
        sanitized = "".join(c for c in sanitized if c not in self._forbidden_chars)
        return sanitized

    def _on_text_changed(self, text):
        if self.sanitize_check.isChecked() and not self._block_signal:
            sanitized = self._sanitize_text(text)
            if sanitized != text:
                self._block_signal = True
                self.line_edit.setText(sanitized)
                self._block_signal = False

    def _on_sanitize_check_changed(self, state):
        if self.sanitize_check.isChecked():
            text = self.line_edit.text()
            sanitized = self._sanitize_text(text)
            if sanitized != text:
                self._block_signal = True
                self.line_edit.setText(sanitized)
                self._block_signal = False

    def _on_clear_clicked(self):
        self.line_edit.clear()

    def _on_make_clicked(self):
        if not self.db_manager:
            self.db_manager = self.get_db_manager_from_parent()
            
        if not self.db_manager:
            print("Error: Database manager not found in parent hierarchy")
            QMessageBox.warning(self, "Error", "Database manager not set!")
            return
            
        if not self._current_path_data:
            print("Error: Path data not available")
            QMessageBox.warning(self, "Error", "Path data not available!")
            return
            
        name = self.line_edit.text().strip()
        if not name:
            print("Error: No name entered")
            QMessageBox.warning(self, "Error", "Please enter a name!")
            return
            
        path = self.sanitize_label.text()
        if path == "-":
            print("Error: Path not available")
            QMessageBox.warning(self, "Error", "Path not available!")
            return

        print(f"Attempting to create project with path: {path}")
        print(f"Template ID: {self.selected_template_id}")
        print(f"Path data: {self._current_path_data}")

        try:
            self.db_manager.connect()
            
            template_content = None
            if self.selected_template_id:
                template = self.db_manager.get_template_by_id(self.selected_template_id)
                if template:
                    template_content = template['content']
                    print(f"Using template: {template['name']}")
            
            actual_path = self.db_manager.create_folder_structure(path, template_content)
            
            draft_status_id = self.db_manager.get_status_id("Draft")
            if not draft_status_id:
                print("Error: Draft status not found")
                QMessageBox.warning(self, "Error", "Draft status not found in database!")
                return
            
            category_id = None
            subcategory_id = None
            
            if self._current_path_data.get('category'):
                category_id = self.db_manager.get_or_create_category(self._current_path_data['category'])
                
            if self._current_path_data.get('subcategory') and category_id:
                subcategory_id = self.db_manager.get_or_create_subcategory(category_id, self._current_path_data['subcategory'])
            
            file_id = self.db_manager.insert_file(
                date=self._current_path_data.get('date', ''),
                name=name,
                root=self._current_path_data.get('folder', ''),
                path=actual_path,
                status_id=draft_status_id,
                category_id=category_id,
                subcategory_id=subcategory_id,
                template_id=self.selected_template_id
            )
            
            print(f"Created project: ID={file_id}, Path={actual_path}")
            
            self.folder_created.emit(
                self._current_path_data.get('date', ''),
                name,
                self._current_path_data.get('folder', ''),
                actual_path,
                self._current_path_data.get('category', ''),
                self._current_path_data.get('subcategory', ''),
                self.selected_template_id or 0
            )
            
            self.project_created.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            print(f"Error creating project: {e}")
        finally:
            self.db_manager.close()

    def set_disk_and_folder(self, disk, folder):
        disk = (disk or "")
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        if disk and folder:
            if disk.endswith("\\") or disk.endswith("/"):
                path = f"{disk}{folder}"
            else:
                path = f"{disk}\\{folder}"
            self.sanitize_label.setText(path)
        elif disk:
            self.sanitize_label.setText(disk)
        else:
            self.sanitize_label.setText("-")
        
        self._current_path_data = {
            'disk': disk,
            'folder': folder
        }

    def set_disk_and_folder_with_date(self, disk, folder, date_path, name_input):
        disk = (disk or "")
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        path = ""
        if disk and folder:
            if disk.endswith("\\") or disk.endswith("/"):
                path = f"{disk}{folder}"
            else:
                path = f"{disk}\\{folder}"
            if date_path:
                path = f"{path}\\{date_path}"
            if name_input:
                path = f"{path}\\{name_input}"
            self.sanitize_label.setText(path)
        elif disk:
            if date_path:
                path = f"{disk}\\{date_path}"
                if name_input:
                    path = f"{path}\\{name_input}"
                self.sanitize_label.setText(path)
            else:
                self.sanitize_label.setText(disk)
        else:
            self.sanitize_label.setText("-")
            
        self._current_path_data = {
            'disk': disk,
            'folder': folder,
            'date': date_path,
            'name': name_input
        }

    def set_disk_and_folder_with_date_category(self, disk, folder, category, subcategory, date_path, name_input):
        disk = (disk or "")
        if disk and ":\\" in disk:
            disk = disk.split(" ")[0]
        
        path_parts = []
        if disk:
            path_parts.append(disk.rstrip("\\"))
        if folder:
            path_parts.append(folder)
        if category:
            path_parts.append(category)
        if subcategory:
            path_parts.append(subcategory)
        if date_path:
            path_parts.append(date_path)
        if name_input:
            path_parts.append(name_input)
        
        if path_parts:
            path = "\\".join(path_parts)
            self.sanitize_label.setText(path)
        else:
            self.sanitize_label.setText("-")
            
        self._current_path_data = {
            'disk': disk,
            'folder': folder,
            'category': category,
            'subcategory': subcategory,
            'date': date_path,
            'name': name_input
        }
