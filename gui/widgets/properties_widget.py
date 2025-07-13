from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
from pathlib import Path
import textwrap

class PropertiesWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
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

        self.date_label = QLabel("Date: -", container)
        layout.addWidget(self.date_label)

        self.name_label = QLabel("Name: -", container)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumWidth(180)
        self.name_label.setMaximumWidth(200)
        layout.addWidget(self.name_label)

        self.status_label = QLabel("Status: -", container)
        layout.addWidget(self.status_label)

        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)
        self.setFixedWidth(220)
        
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.tif']

    def update_properties(self, row_data):
        self.date_label.setText(f"Date: {row_data.get('date', '-')}")
        name = row_data.get('name', '-')
        wrapped_name = self._wrap_long_word(name, 22)
        self.name_label.setText(f"Name: {wrapped_name}")
        
        status = row_data.get('status', '-')
        self.status_label.setText(f"Status: {status}")
        self._apply_status_color(status)
        
        self.load_preview_image(row_data.get('path', ''), row_data.get('name', ''))

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
        """Fast search that stops immediately when any image is found"""
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
                