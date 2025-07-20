import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QApplication, QMenu
from PySide6.QtGui import QPixmap, QCursor, QMouseEvent, QGuiApplication, QDesktopServices, QAction, QDrag
from PySide6.QtCore import Qt, QPoint, QEvent, QRect, QMimeData, QUrl
import qtawesome as qta
from pathlib import Path
import textwrap
import subprocess
from helpers.show_statusbar_helper import show_statusbar_message

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

        self._tooltip_image_label = QLabel(self)
        self._tooltip_image_label.setWindowFlags(Qt.ToolTip)
        self._tooltip_image_label.setAlignment(Qt.AlignCenter)
        self._tooltip_image_label.setStyleSheet("background: white; border: 1px solid #888;")
        self._tooltip_image_label.hide()
        self._tooltip_pixmap = None

        date_row = QHBoxLayout()
        self.date_icon = QLabel()
        self.date_icon.setPixmap(qta.icon("fa6s.calendar", color="#666").pixmap(16, 16))
        self.date_icon.setCursor(Qt.PointingHandCursor)
        self.date_label = QLabel("-", container)
        self.date_label.setCursor(Qt.PointingHandCursor)
        date_row.addWidget(self.date_icon)
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
        self.cat_icon = QLabel()
        self.cat_icon.setPixmap(qta.icon("fa6s.folder-tree", color="#666").pixmap(16, 16))
        self.cat_icon.setCursor(Qt.PointingHandCursor)
        self.cat_combined_label = QLabel("-", container)
        self.cat_combined_label.setCursor(Qt.PointingHandCursor)
        cat_row.addWidget(self.cat_icon)
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
        self.name_label.mousePressEvent = self._on_name_label_mouse_event
        self.date_icon.mousePressEvent = self._on_date_icon_clicked
        self.date_label.mousePressEvent = self._on_date_icon_clicked
        self.cat_icon.mousePressEvent = self._on_cat_icon_clicked
        self.cat_combined_label.mousePressEvent = self._on_cat_icon_clicked

        self.image_label.installEventFilter(self)
        self.image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self._show_image_context_menu)
        self._last_image_path = None
        self._drag_start_pos = None

    def eventFilter(self, obj, event):
        if obj is self.image_label:
            if event.type() == QEvent.Enter:
                if self._tooltip_pixmap:
                    self._show_image_tooltip()
            elif event.type() == QEvent.Leave:
                self._hide_image_tooltip()
            elif event.type() == QEvent.MouseMove:
                if self._tooltip_image_label.isVisible():
                    self._move_image_tooltip()
                if self._drag_start_pos and self._last_image_path and os.path.isfile(self._last_image_path):
                    if (event.pos() - self._drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                        self._hide_image_tooltip()
                        self._start_image_drag()
                        self._drag_start_pos = None
            elif event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._drag_start_pos = event.pos()
            elif event.type() == QEvent.MouseButtonRelease:
                self._drag_start_pos = None
            elif event.type() == QEvent.MouseButtonDblClick:
                if self._last_image_path and os.path.isfile(self._last_image_path):
                    self._open_image_file()
                    return True
        return super().eventFilter(obj, event)

    def _open_image_file(self):
        if not self._last_image_path or not os.path.isfile(self._last_image_path):
            return
        if sys.platform == "win32":
            os.startfile(self._last_image_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self._last_image_path])
        else:
            subprocess.Popen(["xdg-open", self._last_image_path])
        show_statusbar_message(self, "Image opened")

    def _start_image_drag(self):
        if not self._last_image_path or not os.path.isfile(self._last_image_path):
            return
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self._last_image_path)])
        drag = QDrag(self.image_label)
        drag.setMimeData(mime_data)
        pixmap = QPixmap(self._last_image_path)
        if not pixmap.isNull():
            drag.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.exec(Qt.CopyAction)

    def _show_image_tooltip(self):
        if self._tooltip_pixmap:
            cursor_pos = QCursor.pos()
            tooltip_size = self._tooltip_pixmap.size()
            screen = QGuiApplication.screenAt(cursor_pos)
            if screen is not None:
                screen_geom = screen.geometry()
            else:
                screen_geom = QGuiApplication.primaryScreen().geometry()
            x = cursor_pos.x() + 20
            y = cursor_pos.y() + 20
            if x + tooltip_size.width() > screen_geom.right():
                x = cursor_pos.x() - tooltip_size.width() - 20
                if x < screen_geom.left():
                    x = screen_geom.left()
            if y + tooltip_size.height() > screen_geom.bottom():
                y = cursor_pos.y() - tooltip_size.height() - 20
                if y < screen_geom.top():
                    y = screen_geom.top()
            self._tooltip_image_label.setPixmap(self._tooltip_pixmap)
            self._tooltip_image_label.resize(self._tooltip_pixmap.size())
            self._tooltip_image_label.move(QPoint(x, y))
            self._tooltip_image_label.show()

    def _move_image_tooltip(self):
        cursor_pos = QCursor.pos()
        tooltip_size = self._tooltip_image_label.size()
        screen = QGuiApplication.screenAt(cursor_pos)
        if screen is not None:
            screen_geom = screen.geometry()
        else:
            screen_geom = QGuiApplication.primaryScreen().geometry()
        x = cursor_pos.x() + 20
        y = cursor_pos.y() + 20
        if x + tooltip_size.width() > screen_geom.right():
            x = cursor_pos.x() - tooltip_size.width() - 20
            if x < screen_geom.left():
                x = screen_geom.left()
        if y + tooltip_size.height() > screen_geom.bottom():
            y = cursor_pos.y() - tooltip_size.height() - 20
            if y < screen_geom.top():
                y = screen_geom.top()
        self._tooltip_image_label.move(QPoint(x, y))

    def _hide_image_tooltip(self):
        self._tooltip_image_label.hide()

    def _show_image_context_menu(self, pos):
        if not self._last_image_path or not os.path.isfile(self._last_image_path):
            return
        menu = QMenu(self.image_label)
        icon_copy = qta.icon("fa6s.copy")
        icon_open = qta.icon("fa6s.image")
        icon_explorer = qta.icon("fa6s.folder-open")
        action_copy = QAction(icon_copy, "Copy Image", self)
        action_open = QAction(icon_open, "Open Image", self)
        action_show_in_explorer = QAction(icon_explorer, "Show in Explorer", self)
        menu.addAction(action_copy)
        menu.addAction(action_open)
        menu.addAction(action_show_in_explorer)

        def do_copy_image():
            pixmap = QPixmap(self._last_image_path)
            if not pixmap.isNull():
                QApplication.clipboard().setPixmap(pixmap)
                show_statusbar_message(self, "Image copied to clipboard")

        def do_open_image():
            self._open_image_file()

        def do_show_in_explorer():
            folder = os.path.dirname(self._last_image_path)
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{self._last_image_path}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            show_statusbar_message(self, "Image location opened")

        action_copy.triggered.connect(do_copy_image)
        action_open.triggered.connect(do_open_image)
        action_show_in_explorer.triggered.connect(do_show_in_explorer)
        menu.exec(self.image_label.mapToGlobal(pos))

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
        show_statusbar_message(self, message)

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

    def _on_name_label_mouse_event(self, event):
        if event.type() == QMouseEvent.MouseButtonDblClick:
            if self._current_row_data:
                full_path = self._current_row_data.get('path', '')
                if full_path and Path(full_path).exists():
                    if sys.platform == "win32":
                        subprocess.Popen(f'explorer "{str(full_path)}"')
                    else:
                        subprocess.Popen(["xdg-open", str(full_path)])
                    self._show_statusbar_message(f"Opened path: {full_path}")
                else:
                    self._show_statusbar_message("Path not found")
        elif event.type() == QMouseEvent.MouseButtonPress:
            self._on_name_icon_clicked(event)

    def _on_date_icon_clicked(self, event):
        if self._current_row_data:
            full_path = self._current_row_data.get('path', '')
            date_str = self._current_row_data.get('date', '')
            if full_path and date_str:
                path_obj = Path(full_path)
                parts = list(path_obj.parts)
                date_parts = date_str.split('_')
                if len(date_parts) == 3:
                    day, month, year = date_parts
                    try:
                        year_idx = parts.index(year)
                        month_idx = parts.index(month)
                        day_idx = parts.index(day)
                        if year_idx > month_idx > day_idx:
                            target_parts = parts[:year_idx+1]
                        else:
                            target_parts = parts[:day_idx+1]
                        target_path = Path(*target_parts)
                    except ValueError:
                        try:
                            day_idx = parts.index(day)
                            target_parts = parts[:day_idx+1]
                            target_path = Path(*target_parts)
                        except ValueError:
                            target_path = path_obj.parent
                else:
                    target_path = path_obj.parent
                if target_path.exists():
                    if sys.platform == "win32":
                        subprocess.Popen(f'explorer "{str(target_path)}"')
                    else:
                        subprocess.Popen(["xdg-open", str(target_path)])
                    self._show_statusbar_message(f"Opened folder: {target_path}")
                else:
                    self._show_statusbar_message("Target folder not found")
            else:
                self._show_statusbar_message("No path or date to open")

    def _on_cat_icon_clicked(self, event):
        if self._current_row_data:
            full_path = self._current_row_data.get('path', '')
            category = self._current_row_data.get('category', '')
            subcategory = self._current_row_data.get('subcategory', '')
            if full_path and category:
                path_obj = Path(full_path)
                parts = list(path_obj.parts)
                try:
                    if subcategory and subcategory != "-":
                        sub_idx = parts.index(subcategory)
                        target_parts = parts[:sub_idx+1]
                        target_path = Path(*target_parts)
                    else:
                        cat_idx = parts.index(category)
                        target_parts = parts[:cat_idx+1]
                        target_path = Path(*target_parts)
                except ValueError:
                    target_path = path_obj.parent
                if target_path.exists():
                    if sys.platform == "win32":
                        subprocess.Popen(f'explorer \"{str(target_path)}\"')
                    else:
                        subprocess.Popen(["xdg-open", str(target_path)])
                    self._show_statusbar_message(f"Opened folder: {target_path}")
                else:
                    self._show_statusbar_message("Target folder not found")
            else:
                self._show_statusbar_message("No category/subcategory to open")

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
                tooltip_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._tooltip_pixmap = tooltip_pixmap
                self._last_image_path = image_path
            else:
                self.set_no_preview()
        except Exception:
            self.set_no_preview()

    def set_no_preview(self):
        self.image_label.clear()
        self.image_label.setText("No Preview")
        self._tooltip_pixmap = None
        self._tooltip_image_label.hide()