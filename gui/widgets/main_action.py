from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFrame, QLabel, QComboBox, QHBoxLayout,
    QCheckBox, QPushButton, QApplication
)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtCore import Qt, QEvent, QThread, Signal, Slot
import qtawesome as qta
import sys
import os
import random
import datetime
from pathlib import Path
import re

from .name_field import NameFieldWidget
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from helpers.show_statusbar_helper import show_statusbar_message

def get_available_disks():
    disks = []
    if sys.platform == "win32":
        import string
        import ctypes
        from ctypes import windll, create_unicode_buffer

        def get_volume_label(drive_letter):
            volume_name_buffer = create_unicode_buffer(1024)
            file_system_name_buffer = create_unicode_buffer(1024)
            serial_number = ctypes.c_ulong()
            max_component_length = ctypes.c_ulong()
            file_system_flags = ctypes.c_ulong()
            rc = windll.kernel32.GetVolumeInformationW(
                f"{drive_letter}:\\",
                volume_name_buffer,
                ctypes.sizeof(volume_name_buffer),
                ctypes.byref(serial_number),
                ctypes.byref(max_component_length),
                ctypes.byref(file_system_flags),
                file_system_name_buffer,
                ctypes.sizeof(file_system_name_buffer)
            )
            if rc:
                return volume_name_buffer.value
            return ""

        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                if letter != "C":
                    label = get_volume_label(letter)
                    if label:
                        disks.append(f"{letter}:\\ ({label})")
                    else:
                        disks.append(f"{letter}:\\")
            bitmask >>= 1
    else:
        disks.append("/")
    return disks

def extract_disk_path(disk_label):
    if sys.platform == "win32":
        return disk_label.split(" ")[0]
    return disk_label

def get_first_level_folders(disk_path):
    try:
        items = os.listdir(disk_path)
        folders = [
            item for item in items
            if os.path.isdir(os.path.join(disk_path, item))
            and item != "$RECYCLE.BIN"
            and not item.startswith(".")
        ]
        folders.sort(key=lambda x: x.lower())
        return folders
    except Exception:
        return []

def sanitize_folder_name(name):
    forbidden = '<>:"/\\|?*'
    sanitized = name.replace(" ", "_")
    sanitized = "".join(c for c in sanitized if c not in forbidden)
    return sanitized

def sanitize_category_subcategory(name):
    sanitized = name.replace(" ", "_")
    sanitized = re.sub(r'[^A-Za-z0-9_]', '', sanitized)
    return sanitized

def get_unique_sanitized_categories(db_manager):
    categories = db_manager.get_all_categories()
    sanitized_map = {}
    for c in categories:
        key = sanitize_category_subcategory(c)
        if key not in sanitized_map:
            sanitized_map[key] = []
        sanitized_map[key].append(c)
    return list(sanitized_map.keys()), sanitized_map

def get_all_subcategories_for_sanitized(db_manager, sanitized_category, sanitized_map):
    subcategories = set()
    for orig_cat in sanitized_map.get(sanitized_category, []):
        subs = db_manager.get_subcategories_by_category(orig_cat)
        for s in subs:
            subcategories.add(sanitize_category_subcategory(s))
    return sorted(subcategories)

class DiskScanThread(QThread):
    disks_found = Signal(list)
    def run(self):
        disks = get_available_disks()
        self.disks_found.emit(disks)

class MainActionDock(QDockWidget):
    def __init__(self, config_manager, parent=None, db_manager=None):
        super().__init__("Project Creator", parent)
        self.setWindowIcon(qta.icon("fa6s.circle-plus"))
        self.config_manager = config_manager
        self.db_manager = db_manager
        
        container = QWidget(self)
        main_vlayout = QVBoxLayout(container)

        main_layout = QHBoxLayout()

        frame_left = QFrame(container)
        frame_left.setFrameShape(QFrame.StyledPanel)
        frame_left_layout = QVBoxLayout(frame_left)

        disk_header = QHBoxLayout()
        disk_header_icon = QLabel()
        disk_header_icon.setPixmap(qta.icon("fa6s.hard-drive", color="#666").pixmap(16, 16))
        disk_header_label = QLabel("Disk & Folder")
        disk_header_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        disk_header.addWidget(disk_header_icon)
        disk_header.addWidget(disk_header_label)
        disk_header.addStretch()
        frame_left_layout.addLayout(disk_header)

        disk_row = QHBoxLayout()
        disk_icon = QLabel()
        disk_icon.setPixmap(qta.icon("fa6s.hard-drive", color="#FF9800").pixmap(16, 16))
        label_disk = QLabel("Disk")
        combo_disk = QComboBox(frame_left)
        combo_disk.setMinimumWidth(180)
        combo_disk.addItem("Scanning...")
        disk_row.addWidget(disk_icon)
        disk_row.addWidget(label_disk)
        disk_row.addWidget(combo_disk)
        frame_left_layout.addLayout(disk_row)

        folder_row = QHBoxLayout()
        folder_icon = QLabel()
        folder_icon.setPixmap(qta.icon("fa6s.folder", color="#2196F3").pixmap(16, 16))
        label_folder = QLabel("Root")
        combo_folder = QComboBox(frame_left)
        combo_folder.setEnabled(False)
        combo_folder.setMinimumWidth(180)
        folder_row.addWidget(folder_icon)
        folder_row.addWidget(label_folder)
        folder_row.addWidget(combo_folder)
        frame_left_layout.addLayout(folder_row)

        disk_folder_label = QLabel("-", frame_left)
        disk_folder_label.setStyleSheet("color: #1976d2; font-size: 12px; margin-top: 4px;")
        frame_left_layout.addWidget(disk_folder_label)

        def adjust_folder_width():
            combo_folder.setMinimumWidth(combo_disk.width())

        combo_disk.resizeEvent = lambda event: (adjust_folder_width(), QComboBox.resizeEvent(combo_disk, event))
        adjust_folder_width()

        frame_left.setLayout(frame_left_layout)
        main_layout.addWidget(frame_left)

        frame_middle = QFrame(container)
        frame_middle.setFrameShape(QFrame.StyledPanel)
        frame_middle_layout = QVBoxLayout(frame_middle)

        category_header = QHBoxLayout()
        category_header_icon = QLabel()
        category_header_icon.setPixmap(qta.icon("fa6s.folder-tree", color="#666").pixmap(16, 16))
        category_header_label = QLabel("Category & Subcategory")
        category_header_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        category_header.addWidget(category_header_icon)
        category_header.addWidget(category_header_label)
        category_header.addStretch()
        frame_middle_layout.addLayout(category_header)

        category_row = QHBoxLayout()
        category_icon = QLabel()
        category_icon.setPixmap(qta.icon("fa6s.folder-tree", color="#9C27B0").pixmap(16, 16))
        label_category = QLabel("Category")
        combo_category = QComboBox(frame_middle)
        combo_category.setEditable(True)
        combo_category.setMinimumWidth(150)
        combo_category.setMaximumWidth(150)
        combo_category.addItem("")

        category_row.addWidget(category_icon)
        category_row.addWidget(label_category)
        category_row.addWidget(combo_category)
        frame_middle_layout.addLayout(category_row)

        subcategory_row = QHBoxLayout()
        subcategory_icon = QLabel()
        subcategory_icon.setPixmap(qta.icon("fa6s.folder-open", color="#4CAF50").pixmap(16, 16))
        label_subcategory = QLabel("Sub")
        combo_subcategory = QComboBox(frame_middle)
        combo_subcategory.setEditable(True)
        combo_subcategory.setEnabled(False)
        combo_subcategory.setMinimumWidth(150)
        combo_subcategory.setMaximumWidth(150)
        combo_subcategory.addItem("")

        subcategory_row.addWidget(subcategory_icon)
        subcategory_row.addWidget(label_subcategory)
        subcategory_row.addWidget(combo_subcategory)
        frame_middle_layout.addLayout(subcategory_row)

        cat_subcat_label = QLabel("-", frame_middle)
        cat_subcat_label.setStyleSheet("color: #1976d2; font-size: 12px; margin-top: 4px;")
        frame_middle_layout.addWidget(cat_subcat_label)

        frame_middle.setLayout(frame_middle_layout)
        main_layout.addWidget(frame_middle)

        frame_far_right = QFrame(container)
        frame_far_right.setFrameShape(QFrame.StyledPanel)
        frame_far_right_layout = QVBoxLayout(frame_far_right)

        template_header = QHBoxLayout()
        template_header_icon = QLabel()
        template_header_icon.setPixmap(qta.icon("fa6s.file-lines", color="#666").pixmap(16, 16))
        template_header_label = QLabel("Template & Theme")
        template_header_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        template_header.addWidget(template_header_icon)
        template_header.addWidget(template_header_label)
        template_header.addStretch()
        frame_far_right_layout.addLayout(template_header)

        template_row = QHBoxLayout()
        template_icon = QLabel()
        template_icon.setPixmap(qta.icon("fa6s.file-lines", color="#FF5722").pixmap(16, 16))
        combo_template = QComboBox(frame_far_right)
        combo_template.addItem("No Template")
        template_row.addWidget(template_icon)
        template_row.addWidget(combo_template)
        frame_far_right_layout.addLayout(template_row)

        color_row = QHBoxLayout()
        theme_icon = QLabel()
        theme_icon.setPixmap(qta.icon("fa6s.palette", color="#E91E63").pixmap(16, 16))
        color_picker_btn = QPushButton(frame_far_right)
        color_picker_btn.setFixedSize(20, 20)
        color_picker_btn.setIcon(qta.icon("fa6s.eye-dropper"))
        color_picker_btn.setStyleSheet("background-color: #cccccc; border: 1px solid #888;")
        color_row.addWidget(theme_icon)
        color_row.addWidget(color_picker_btn)
        color_hex_label = QLabel("#cccccc", frame_far_right)
        color_hex_label.setStyleSheet("color: #1976d2; font-size: 12px; margin-left: 8px;")
        color_row.addWidget(color_hex_label)
        frame_far_right_layout.addLayout(color_row)

        # Add label for Template\Color display
        template_color_label = QLabel("-", frame_far_right)
        template_color_label.setStyleSheet("color: #1976d2; font-size: 12px; margin-top: 4px;")
        frame_far_right_layout.addWidget(template_color_label)

        self._color_picker_btn = color_picker_btn
        self._color_hex_label = color_hex_label
        self._template_color_label = template_color_label

        def set_random_color_from_cursor():
            hue = random.randint(0, 359)
            s = 0.7
            v = 0.9
            color = QColor()
            color.setHsvF(hue / 359.0, s, v)
            color_picker_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            color_hex_label.setText(color.name())
            update_template_color_label()

        def update_template_color_label():
            template_text = combo_template.currentText()
            color_text = color_hex_label.text()
            if template_text and template_text != "No Template":
                template_color_label.setText(f"{template_text}\\{color_text}")
            elif template_text:
                template_color_label.setText(f"{template_text}")
            elif color_text:
                template_color_label.setText(f"\\{color_text}")
            else:
                template_color_label.setText("-")

        container.setMouseTracking(True)
        frame_far_right.setMouseTracking(True)
        color_picker_btn.setMouseTracking(True)

        def mouse_move_event(event):
            set_random_color_from_cursor()

        container.mouseMoveEvent = mouse_move_event
        frame_far_right.mouseMoveEvent = mouse_move_event
        color_picker_btn.mouseMoveEvent = mouse_move_event

        combo_template.currentIndexChanged.connect(update_template_color_label)

        frame_far_right.setLayout(frame_far_right_layout)
        main_layout.addWidget(frame_far_right)

        frame_right = QFrame(container)
        frame_right.setFrameShape(QFrame.StyledPanel)
        frame_right_layout = QVBoxLayout(frame_right)
        
        options_header = QHBoxLayout()
        options_icon = QLabel()
        options_icon.setPixmap(qta.icon("fa6s.gear", color="#666").pixmap(16, 16))
        options_title = QLabel("Options")
        options_title.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        options_header.addWidget(options_icon)
        options_header.addWidget(options_title)
        options_header.addStretch()
        frame_right_layout.addLayout(options_header)
        
        date_check = QCheckBox("Date", frame_right)
        date_check.setIcon(qta.icon("fa6s.calendar"))
        markdown_check = QCheckBox("Markdown", frame_right)
        markdown_check.setIcon(qta.icon("fa6b.markdown"))
        open_explorer_check = QCheckBox("Open Explorer", frame_right)
        open_explorer_check.setIcon(qta.icon("fa6s.folder-open"))
        
        try:
            date_check.setChecked(self.config_manager.get("action_options.date"))
            markdown_check.setChecked(self.config_manager.get("action_options.markdown"))
            open_explorer_check.setChecked(self.config_manager.get("action_options.open_explorer"))
        except KeyError:
            date_check.setChecked(False)
            markdown_check.setChecked(False)
            open_explorer_check.setChecked(False)
        
        frame_right_layout.addWidget(date_check)
        frame_right_layout.addWidget(markdown_check)
        frame_right_layout.addWidget(open_explorer_check)
        # Add label for open explorer status
        self.open_explorer_status_label = QLabel("", frame_right)
        self.open_explorer_status_label.setStyleSheet("color: #1976d2; font-size: 12px;")
        frame_right_layout.addWidget(self.open_explorer_status_label)
        frame_right.setLayout(frame_right_layout)
        main_layout.addWidget(frame_right)

        main_vlayout.addLayout(main_layout)

        name_field_widget = NameFieldWidget(container)
        name_field_widget.set_db_manager(self.db_manager)
        name_field_widget.set_config_manager(self.config_manager)
        main_vlayout.addWidget(name_field_widget)

        try:
            name_field_widget.sanitize_check.setChecked(self.config_manager.get("action_options.sanitize_name"))
        except KeyError:
            name_field_widget.sanitize_check.setChecked(False)

        container.setLayout(main_vlayout)
        self.setWidget(container)

        self._combo_disk = combo_disk
        self._combo_folder = combo_folder
        self._combo_category = combo_category
        self._combo_subcategory = combo_subcategory
        self._adjust_folder_width = adjust_folder_width
        self._combo_template = combo_template
        self._name_field_widget = name_field_widget
        self._color_hex_label = color_hex_label
        self._template_color_label = template_color_label

        def load_templates():
            try:
                self.db_manager.connect()
                templates = self.db_manager.get_all_templates()
                combo_template.clear()
                combo_template.addItem("No Template")
                for template in templates:
                    combo_template.addItem(template['name'])
                    combo_template.setItemData(combo_template.count() - 1, template['id'])
                show_statusbar_message(self, "Templates loaded")
            except Exception as e:
                print(f"Error loading templates: {e}")
                show_statusbar_message(self, f"Error loading templates: {e}")
            finally:
                self.db_manager.close()

        def update_disk_folder_label():
            disk_label = combo_disk.currentText()
            folder_label = combo_folder.currentText() if combo_folder.isEnabled() and combo_folder.currentIndex() >= 0 else ""
            if disk_label and folder_label:
                disk_folder_label.setText(f"{disk_label}\\{folder_label}")
            elif disk_label:
                disk_folder_label.setText(f"{disk_label}")
            elif folder_label:
                disk_folder_label.setText(f"\\{folder_label}")
            else:
                disk_folder_label.setText("-")

        def update_name_field_label():
            disk_label = combo_disk.currentText()
            folder_label = combo_folder.currentText() if combo_folder.isEnabled() and combo_folder.currentIndex() >= 0 else ""
            category_text = combo_category.currentText().strip()
            subcategory_text = combo_subcategory.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            subcategory_text = sanitize_category_subcategory(subcategory_text)
            if category_text and subcategory_text:
                cat_subcat_label.setText(f"{category_text}\\{subcategory_text}")
            elif category_text:
                cat_subcat_label.setText(f"{category_text}")
            elif subcategory_text:
                cat_subcat_label.setText(f"\\{subcategory_text}")
            else:
                cat_subcat_label.setText("-")
            update_disk_folder_label()
            update_template_color_label()
            date_path = ""
            if date_check.isChecked():
                today = datetime.date.today()
                month_name = today.strftime("%B")
                date_path = f"{today.year}\\{month_name}\\{today.day:02}"
            name_input = name_field_widget.line_edit.text()
            sanitize = name_field_widget.sanitize_check.isChecked()
            if sanitize:
                name_input = sanitize_folder_name(name_input)
            name_field_widget.set_disk_and_folder_with_date_category(
                disk_label, folder_label, category_text, subcategory_text, date_path, name_input
            )
            show_statusbar_message(self, f"Path updated: disk={disk_label}, folder={folder_label}, category={category_text}, subcategory={subcategory_text}, date={date_path}, name={name_input}")

        def load_categories():
            try:
                self.db_manager.connect()
                unique_cats, self._sanitized_cat_map = get_unique_sanitized_categories(self.db_manager)
                combo_category.clear()
                combo_category.addItem("")
                combo_category.addItems(unique_cats)
                show_statusbar_message(self, "Categories loaded")
            except Exception as e:
                print(f"Error loading categories: {e}")
                show_statusbar_message(self, f"Error loading categories: {e}")
            finally:
                self.db_manager.close()

        def load_subcategories(category_name):
            sanitized_cat = sanitize_category_subcategory(category_name)
            combo_subcategory.clear()
            combo_subcategory.addItem("")
            if not sanitized_cat or not hasattr(self, "_sanitized_cat_map"):
                combo_subcategory.setEnabled(False)
                show_statusbar_message(self, "No category selected for subcategory")
                return
            try:
                self.db_manager.connect()
                subcategories = get_all_subcategories_for_sanitized(self.db_manager, sanitized_cat, self._sanitized_cat_map)
                combo_subcategory.addItems(subcategories)
                combo_subcategory.setEnabled(True)
                show_statusbar_message(self, f"Subcategories loaded for category: {sanitized_cat}")
            except Exception as e:
                print(f"Error loading subcategories: {e}")
                combo_subcategory.setEnabled(False)
                show_statusbar_message(self, f"Error loading subcategories: {e}")
            finally:
                self.db_manager.close()

        def on_disk_changed(index):
            if index < 0:
                combo_folder.clear()
                combo_folder.setEnabled(False)
                update_name_field_label()
                update_disk_folder_label()
                show_statusbar_message(self, "No disk selected")
                return
            disk_label = combo_disk.currentText()
            disk_path = extract_disk_path(disk_label)
            folders = get_first_level_folders(disk_path)
            combo_folder.clear()
            if folders:
                combo_folder.addItems(folders)
                combo_folder.setEnabled(True)
                show_statusbar_message(self, f"Disk changed: {disk_label}, folders loaded")
            else:
                combo_folder.setEnabled(False)
                show_statusbar_message(self, f"Disk changed: {disk_label}, no folders found")
            adjust_folder_width()
            update_name_field_label()
            update_disk_folder_label()

        def on_folder_changed(index):
            update_name_field_label()
            update_disk_folder_label()
            folder_label = combo_folder.currentText()
            show_statusbar_message(self, f"Folder changed: {folder_label}")

        def on_category_changed():
            category_text = combo_category.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            if category_text and combo_category.findText(category_text) >= 0:
                load_subcategories(category_text)
            update_name_field_label()
            show_statusbar_message(self, f"Category changed: {category_text}")

        def on_subcategory_changed():
            subcategory_text = combo_subcategory.currentText().strip()
            subcategory_text = sanitize_category_subcategory(subcategory_text)
            update_name_field_label()
            show_statusbar_message(self, f"Subcategory changed: {subcategory_text}")

        def on_category_enter():
            category_text = combo_category.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            if not category_text:
                update_name_field_label()
                combo_subcategory.setFocus()
                show_statusbar_message(self, "Category entry empty")
                return
            try:
                self.db_manager.connect()
                category_id = self.db_manager.get_or_create_category(category_text)
                self.db_manager.close()
                load_categories()
                new_index = combo_category.findText(category_text)
                if new_index >= 0:
                    combo_category.setCurrentIndex(new_index)
                show_statusbar_message(self, f"Category ensured/created: {category_text}")
            except Exception as e:
                print(f"Error ensuring category: {e}")
                if self.db_manager.connection:
                    self.db_manager.close()
                show_statusbar_message(self, f"Error ensuring category: {e}")
            load_subcategories(category_text)
            update_name_field_label()
            combo_subcategory.setFocus()

        def on_subcategory_enter():
            category_text = combo_category.currentText().strip()
            subcategory_text = combo_subcategory.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            subcategory_text = sanitize_category_subcategory(subcategory_text)
            if not category_text or not subcategory_text:
                update_name_field_label()
                name_field_widget.line_edit.setFocus()
                show_statusbar_message(self, "Subcategory entry empty")
                return
            try:
                self.db_manager.connect()
                category_id = self.db_manager.get_or_create_category(category_text)
                subcategory_id = self.db_manager.get_or_create_subcategory(category_id, subcategory_text)
                self.db_manager.close()
                load_subcategories(category_text)
                new_index = combo_subcategory.findText(subcategory_text)
                if new_index >= 0:
                    combo_subcategory.setCurrentIndex(new_index)
                show_statusbar_message(self, f"Subcategory ensured/created: {subcategory_text}")
            except Exception as e:
                print(f"Error ensuring subcategory: {e}")
                if self.db_manager.connection:
                    self.db_manager.close()
                show_statusbar_message(self, f"Error ensuring subcategory: {e}")
            update_name_field_label()
            name_field_widget.line_edit.setFocus()

        def on_date_check_changed(state):
            self.config_manager.set("action_options.date", date_check.isChecked())
            update_name_field_label()
            show_statusbar_message(self, f"Date option changed: {date_check.isChecked()}")

        def on_markdown_check_changed(state):
            self.config_manager.set("action_options.markdown", markdown_check.isChecked())
            show_statusbar_message(self, f"Markdown option changed: {markdown_check.isChecked()}")

        def on_open_explorer_check_changed(state):
            self.config_manager.set("action_options.open_explorer", open_explorer_check.isChecked())
            update_open_explorer_status_label()
            show_statusbar_message(self, f"Open Explorer option changed: {open_explorer_check.isChecked()}")

        def update_open_explorer_status_label():
            if not open_explorer_check.isChecked():
                self.open_explorer_status_label.setText("Auto open explorer disabled")
            else:
                self.open_explorer_status_label.setText("")

        def on_name_input_changed(text):
            update_name_field_label()
            show_statusbar_message(self, f"Name input changed: {text}")

        def on_sanitize_check_changed(state):
            self.config_manager.set("action_options.sanitize_name", name_field_widget.sanitize_check.isChecked())
            update_name_field_label()
            show_statusbar_message(self, f"Sanitize name option changed: {name_field_widget.sanitize_check.isChecked()}")

        def on_template_changed(index):
            if index == 0:
                name_field_widget.set_selected_template(None)
                show_statusbar_message(self, "Template cleared")
            else:
                template_id = combo_template.itemData(index)
                name_field_widget.set_selected_template(template_id)
                show_statusbar_message(self, f"Template selected: {combo_template.currentText()} (ID: {template_id})")
            update_template_color_label()

        combo_disk.currentIndexChanged.connect(on_disk_changed)
        combo_folder.currentIndexChanged.connect(on_folder_changed)
        combo_category.currentTextChanged.connect(on_category_changed)
        combo_category.lineEdit().returnPressed.connect(on_category_enter)
        combo_subcategory.currentTextChanged.connect(on_subcategory_changed)
        combo_subcategory.lineEdit().returnPressed.connect(on_subcategory_enter)
        combo_template.currentIndexChanged.connect(on_template_changed)

        date_check.stateChanged.connect(on_date_check_changed)
        markdown_check.stateChanged.connect(on_markdown_check_changed)
        open_explorer_check.stateChanged.connect(on_open_explorer_check_changed)
        name_field_widget.line_edit.textChanged.connect(on_name_input_changed)
        name_field_widget.sanitize_check.stateChanged.connect(on_sanitize_check_changed)

        self._disk_thread = DiskScanThread()
        self._disk_thread.disks_found.connect(self._on_disks_ready)
        self._disk_thread.start()

        self._on_disk_changed = on_disk_changed
        
        load_categories()
        load_templates()
        update_open_explorer_status_label()

        def refresh_color_label():
            style = color_picker_btn.styleSheet()
            if "background-color:" in style:
                color_start = style.find("background-color:") + len("background-color:")
                color_end = style.find(";", color_start)
                if color_end == -1:
                    color_end = style.find("}", color_start)
                color = style[color_start:color_end].strip()
                color_hex_label.setText(color)

        color_picker_btn.installEventFilter(self)
        def color_btn_event_filter(obj, event):
            if obj is color_picker_btn and event.type() == QEvent.Paint:
                refresh_color_label()
            return False
        color_picker_btn.eventFilter = color_btn_event_filter

    @Slot(list)
    def _on_disks_ready(self, disks):
        self._combo_disk.clear()
        if disks:
            self._combo_disk.addItems(disks)
            self._combo_disk.setEnabled(True)
            self._adjust_folder_width()
            self._combo_disk.setCurrentIndex(0)
            self._on_disk_changed(0)
        else:
            self._combo_disk.addItem("Scanning...")
            self._combo_disk.setEnabled(False)
            self._combo_folder.clear()
            self._combo_folder.setEnabled(False)
            self._on_disk_changed(0)

    def get_current_color_hex(self):
        return self._color_hex_label.text()