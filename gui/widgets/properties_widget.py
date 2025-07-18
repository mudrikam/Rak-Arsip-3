from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QCursor
import qtawesome as qta
import os
from pathlib import Path
import textwrap

class PropertiesWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Project Properties", parent)
        self.setWindowIcon(qta.icon("fa6s.circle-info"))
        self.parent_window = parent
        container = QWidget(self)
        layout = QVBoxLayout(container)

        self.image_frame = QFrame(container)
        self.image_frame.setFixedSize(180, 180)
        self.image_label = QLabel(self.image_frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setGeometry(0, 0, 180, 180)
        self.image_label.setText("No Preview")
        layout.addWidget(self.image_frame)

        date_row = QHBoxLayout()
        date_icon = QLabel()
        date_icon.setPixmap(qta.icon("fa6s.calendar", color="#666").pixmap(16, 16))
        self.date_label = QLabel("-", container)
        date_row.addWidget(date_icon)
        date_row.addWidget(self.date_label)
        date_row.addStretch()
        layout.addLayout(date_row)

        root_row = QHBoxLayout()
        self.root_icon = QLabel()
        self.root_icon.setPixmap(qta.icon("fa6s.folder", color="#666").pixmap(16, 16))
        self.root_icon.setCursor(Qt.PointingHandCursor)
        self.root_label = QLabel("-", container)
        self.root_label.setCursor(Qt.PointingHandCursor)
        root_row.addWidget(self.root_icon)
        root_row.addWidget(self.root_label)
        root_row.addStretch()
        layout.addLayout(root_row)

        name_row = QHBoxLayout()
        self.name_icon = QLabel()
        self.name_icon.setPixmap(qta.icon("fa6s.file-lines", color="#666").pixmap(16, 16))
        self.name_icon.setCursor(Qt.PointingHandCursor)
        self.name_label = QLabel("-", container)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumWidth(180)
        self.name_label.setMaximumWidth(200)
        self.name_label.setCursor(Qt.PointingHandCursor)
        name_row.addWidget(self.name_icon)
        name_row.addWidget(self.name_label)
        name_row.addStretch()
        layout.addLayout(name_row)

        cat_row = QHBoxLayout()
        cat_icon = QLabel()
        cat_icon.setPixmap(qta.icon("fa6s.folder-tree", color="#666").pixmap(16, 16))
        self.cat_combined_label = QLabel("-", container)
        cat_row.addWidget(cat_icon)
        cat_row.addWidget(self.cat_combined_label)
        cat_row.addStretch()
        layout.addLayout(cat_row)

        status_row = QHBoxLayout()
        status_icon = QLabel()
        status_icon.setPixmap(qta.icon("fa6s.circle-info", color="#666").pixmap(16, 16))
        self.status_label = QLabel("-", container)
        status_row.addWidget(status_icon)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)
        self.setFixedWidth(200)
        
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.tif']

        self._current_row_data = None
        self.root_icon.mousePressEvent = self._on_root_icon_clicked
        self.root_label.mousePressEvent = self._on_root_icon_clicked
        self.name_icon.mousePressEvent = self._on_name_icon_clicked
        self.name_label.mousePressEvent = self._on_name_icon_clicked

    def update_properties(self, row_data):
        self._current_row_data = row_data
        self.date_label.setText(f"{row_data.get('date', '-')}")
        root = row_data.get('root', '-')
        self.root_label.setText(f"{root}")
        name = row_data.get('name', '-')
        wrapped_name = self._wrap_long_word(name, 22)
        self.name_label.setText(f"{wrapped_name}")
        category = row_data.get('category', '-')
        subcategory = row_data.get('subcategory', '-')
        if category and subcategory and category != "-" and subcategory != "-":
            self.cat_combined_label.setText(f"{category}/{subcategory}")
        elif category and category != "-":
            self.cat_combined_label.setText(f"{category}")
        elif subcategory and subcategory != "-":
            self.cat_combined_label.setText(f"/{subcategory}")
        else:
            self.cat_combined_label.setText("-")
        status = row_data.get('status', '-')
        self.status_label.setText(f"{status}")
        self._apply_status_color(status)
        self.load_preview_image(row_data.get('path', ''), row_data.get('name', ''))

    def _show_statusbar_message(self, message):
        main_window = self.parent_window
        if hasattr(main_window, "statusBar"):
            statusbar = main_window.statusBar()
            if statusbar:
                statusbar.showMessage(message, 2000)

    def _on_root_icon_clicked(self, event):
        if self._current_row_data:
            path = self._current_row_data.get('path', '')
            if path:
                QApplication.clipboard().setText(str(path))
                self._show_statusbar_message(f"Path copied: {path}")
            else:
                self._show_statusbar_message("No path to copy")

    def _on_name_icon_clicked(self, event):
        if self._current_row_data:
            name = self._current_row_data.get('name', '')
            if name:
                QApplication.clipboard().setText(str(name))
                self._show_statusbar_message(f"Name copied: {name}")
            else:
                self._show_statusbar_message("No name to copy")

    def _apply_status_color(self, status):
        if hasattr(self.parent_window, 'config_manager'):
            try:
                status_config = self.parent_window.config_manager.get("status_options")
                if status in status_config:
                    config = status_config[status]
                    color = config.get("color", "")
                    font_weight = config.get("font_weight", "normal")
                    self.status_label.setStyleSheet(f"color: {color}; font-weight: {font_weight};")
                else:
                    self.status_label.setStyleSheet("")
            except:
                self.status_label.setStyleSheet("")
        else:
            self.status_label.setStyleSheet("")

    def _wrap_long_word(self, text, width):
        if not text:
            return ""
        if " " in text:
            return text
        return "\n".join(textwrap.wrap(text, width=width))

    def _find_first_image_fast(self, directory, file_name, max_depth=3, current_depth=0):
        if current_depth > max_depth:
            return None
        
        try:
            items = list(directory.iterdir())
            
            for item in items:
                if item.is_file() and item.suffix.lower() in self.supported_formats:
                    if item.stem.lower() == file_name.lower():
                        return item
                    else:
                        return item
            
            for item in items:
                if item.is_dir():
                    result = self._find_first_image_fast(item, file_name, max_depth, current_depth + 1)
                    if result:
                        return result
                        
        except PermissionError:
            pass
        except Exception:
            pass
        
        return None

    def load_preview_image(self, file_path, file_name):
        try:
            if not file_path:
                self.set_no_preview()
                return
            
            path_obj = Path(file_path)
            
            if path_obj.is_file():
                directory = path_obj.parent
            elif path_obj.is_dir():
                directory = path_obj
            else:
                directory = path_obj
            
            if not directory.exists():
                self.set_no_preview()
                return
            
            image_file = self._find_first_image_fast(directory, file_name)
            
            if image_file:
                self.display_image(str(image_file))
            else:
                self.set_no_preview()
                
        except Exception:
            self.set_no_preview()

    def display_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(178, 178, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
            else:
                self.set_no_preview()
        except Exception:
            self.set_no_preview()

    def set_no_preview(self):
        self.image_label.clear()
        self.image_label.setText("No Preview")