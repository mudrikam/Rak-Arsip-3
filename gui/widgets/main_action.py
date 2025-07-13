from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFrame, QLabel, QComboBox, QHBoxLayout,
    QCheckBox, QPushButton
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
        folders = [item for item in items if os.path.isdir(os.path.join(disk_path, item))]
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

class DiskScanThread(QThread):
    disks_found = Signal(list)
    def run(self):
        disks = get_available_disks()
        self.disks_found.emit(disks)

class MainActionDock(QDockWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__("Main Action", parent)
        self.config_manager = config_manager
        
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        db_config_manager = ConfigManager(str(db_config_path))
        self.db_manager = DatabaseManager(db_config_manager, self.config_manager)
        
        container = QWidget(self)
        main_vlayout = QVBoxLayout(container)

        main_layout = QHBoxLayout()
        frame_left = QFrame(container)
        frame_left.setFrameShape(QFrame.StyledPanel)
        frame_left_layout = QVBoxLayout(frame_left)

        disk_row = QHBoxLayout()
        label_disk = QLabel("Disk", frame_left)
        combo_disk = QComboBox(frame_left)
        combo_disk.setMinimumWidth(180)
        combo_disk.addItem("Scanning...")
        disk_row.addWidget(label_disk)
        disk_row.addWidget(combo_disk)
        frame_left_layout.addLayout(disk_row)

        folder_row = QHBoxLayout()
        label_folder = QLabel("Folder", frame_left)
        combo_folder = QComboBox(frame_left)
        combo_folder.setEnabled(False)
        combo_folder.setMinimumWidth(180)
        folder_row.addWidget(label_folder)
        folder_row.addWidget(combo_folder)
        frame_left_layout.addLayout(folder_row)

        def adjust_folder_width():
            combo_folder.setMinimumWidth(combo_disk.width())

        combo_disk.resizeEvent = lambda event: (adjust_folder_width(), QComboBox.resizeEvent(combo_disk, event))
        adjust_folder_width()

        frame_left.setLayout(frame_left_layout)
        main_layout.addWidget(frame_left)

        frame_middle = QFrame(container)
        frame_middle.setFrameShape(QFrame.StyledPanel)
        frame_middle_layout = QVBoxLayout(frame_middle)

        category_row = QHBoxLayout()
        label_category = QLabel("Category", frame_middle)
        combo_category = QComboBox(frame_middle)
        combo_category.setEditable(True)
        combo_category.setMinimumWidth(150)
        combo_category.addItem("")
        category_row.addWidget(label_category)
        category_row.addWidget(combo_category)
        frame_middle_layout.addLayout(category_row)

        subcategory_row = QHBoxLayout()
        label_subcategory = QLabel("Sub", frame_middle)
        combo_subcategory = QComboBox(frame_middle)
        combo_subcategory.setEditable(True)
        combo_subcategory.setEnabled(False)
        combo_subcategory.setMinimumWidth(150)
        combo_subcategory.addItem("")
        subcategory_row.addWidget(label_subcategory)
        subcategory_row.addWidget(combo_subcategory)
        frame_middle_layout.addLayout(subcategory_row)

        frame_middle.setLayout(frame_middle_layout)
        main_layout.addWidget(frame_middle)

        frame_right = QFrame(container)
        frame_right.setFrameShape(QFrame.StyledPanel)
        frame_right_layout = QVBoxLayout(frame_right)
        date_check = QCheckBox("Date", frame_right)
        markdown_check = QCheckBox("Markdown", frame_right)
        open_explorer_check = QCheckBox("Open Explorer", frame_right)
        
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
        frame_right.setLayout(frame_right_layout)
        main_layout.addWidget(frame_right)

        frame_far_right = QFrame(container)
        frame_far_right.setFrameShape(QFrame.StyledPanel)
        frame_far_right_layout = QVBoxLayout(frame_far_right)

        template_row = QHBoxLayout()
        label_template = QLabel("Template", frame_far_right)
        combo_template = QComboBox(frame_far_right)
        combo_template.addItems(["Template 1", "Template 2", "Template 3"])
        template_row.addWidget(label_template)
        template_row.addWidget(combo_template)
        frame_far_right_layout.addLayout(template_row)

        color_row = QHBoxLayout()
        label_theme = QLabel("Theme", frame_far_right)
        color_picker_btn = QPushButton(frame_far_right)
        color_picker_btn.setFixedSize(20, 20)
        color_picker_btn.setIcon(qta.icon("fa6s.eye-dropper"))
        color_picker_btn.setStyleSheet("background-color: #cccccc; border: 1px solid #888;")
        color_row.addWidget(label_theme)
        color_row.addWidget(color_picker_btn)
        frame_far_right_layout.addLayout(color_row)

        def set_random_color_from_cursor():
            hue = random.randint(0, 359)
            s = 0.7
            v = 0.9
            color = QColor()
            color.setHsvF(hue / 359.0, s, v)
            color_picker_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")

        container.setMouseTracking(True)
        frame_far_right.setMouseTracking(True)
        color_picker_btn.setMouseTracking(True)

        def mouse_move_event(event):
            set_random_color_from_cursor()

        container.mouseMoveEvent = mouse_move_event
        frame_far_right.mouseMoveEvent = mouse_move_event
        color_picker_btn.mouseMoveEvent = mouse_move_event

        frame_far_right.setLayout(frame_far_right_layout)
        main_layout.addWidget(frame_far_right)

        main_vlayout.addLayout(main_layout)

        name_field_widget = NameFieldWidget(container)
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
        self._name_field_widget = name_field_widget
        self._date_check = date_check
        self._markdown_check = markdown_check
        self._open_explorer_check = open_explorer_check

        def update_name_field_label():
            disk_label = combo_disk.currentText()
            folder_label = combo_folder.currentText() if combo_folder.isEnabled() and combo_folder.currentIndex() >= 0 else ""
            category_text = combo_category.currentText().strip()
            subcategory_text = combo_subcategory.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            subcategory_text = sanitize_category_subcategory(subcategory_text)
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

        def load_categories():
            try:
                self.db_manager.connect()
                categories = self.db_manager.get_all_categories()
                categories = [sanitize_category_subcategory(c) for c in categories]
                combo_category.clear()
                combo_category.addItem("")
                combo_category.addItems(categories)
            except Exception as e:
                print(f"Error loading categories: {e}")
            finally:
                self.db_manager.close()

        def load_subcategories(category_name):
            category_name = sanitize_category_subcategory(category_name)
            combo_subcategory.clear()
            combo_subcategory.addItem("")
            if not category_name:
                combo_subcategory.setEnabled(False)
                return
            
            try:
                self.db_manager.connect()
                subcategories = self.db_manager.get_subcategories_by_category(category_name)
                subcategories = [sanitize_category_subcategory(s) for s in subcategories]
                combo_subcategory.addItems(subcategories)
                combo_subcategory.setEnabled(True)
            except Exception as e:
                print(f"Error loading subcategories: {e}")
                combo_subcategory.setEnabled(False)
            finally:
                self.db_manager.close()

        def on_disk_changed(index):
            if index < 0:
                combo_folder.clear()
                combo_folder.setEnabled(False)
                update_name_field_label()
                return
            disk_label = combo_disk.currentText()
            disk_path = extract_disk_path(disk_label)
            folders = get_first_level_folders(disk_path)
            combo_folder.clear()
            if folders:
                combo_folder.addItems(folders)
                combo_folder.setEnabled(True)
            else:
                combo_folder.setEnabled(False)
            adjust_folder_width()
            update_name_field_label()

        def on_folder_changed(index):
            update_name_field_label()

        def on_category_changed():
            category_text = combo_category.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            if category_text and combo_category.findText(category_text) >= 0:
                load_subcategories(category_text)
            update_name_field_label()

        def on_category_enter():
            category_text = combo_category.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            if not category_text:
                update_name_field_label()
                combo_subcategory.setFocus()
                return
            try:
                self.db_manager.connect()
                category_id = self.db_manager.get_or_create_category(category_text)
                self.db_manager.close()
                load_categories()
                new_index = combo_category.findText(category_text)
                if new_index >= 0:
                    combo_category.setCurrentIndex(new_index)
            except Exception as e:
                print(f"Error ensuring category: {e}")
                if self.db_manager.connection:
                    self.db_manager.close()
            load_subcategories(category_text)
            update_name_field_label()
            combo_subcategory.setFocus()

        def on_subcategory_changed():
            subcategory_text = combo_subcategory.currentText().strip()
            subcategory_text = sanitize_category_subcategory(subcategory_text)
            update_name_field_label()

        def on_subcategory_enter():
            category_text = combo_category.currentText().strip()
            subcategory_text = combo_subcategory.currentText().strip()
            category_text = sanitize_category_subcategory(category_text)
            subcategory_text = sanitize_category_subcategory(subcategory_text)
            if not category_text or not subcategory_text:
                update_name_field_label()
                name_field_widget.line_edit.setFocus()
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
            except Exception as e:
                print(f"Error ensuring subcategory: {e}")
                if self.db_manager.connection:
                    self.db_manager.close()
            update_name_field_label()
            name_field_widget.line_edit.setFocus()

        def on_date_check_changed(state):
            self.config_manager.set("action_options.date", date_check.isChecked())
            update_name_field_label()

        def on_markdown_check_changed(state):
            self.config_manager.set("action_options.markdown", markdown_check.isChecked())

        def on_open_explorer_check_changed(state):
            self.config_manager.set("action_options.open_explorer", open_explorer_check.isChecked())

        def on_name_input_changed(text):
            update_name_field_label()

        def on_sanitize_check_changed(state):
            self.config_manager.set("action_options.sanitize_name", name_field_widget.sanitize_check.isChecked())
            update_name_field_label()

        combo_disk.currentIndexChanged.connect(on_disk_changed)
        combo_folder.currentIndexChanged.connect(on_folder_changed)
        combo_category.currentTextChanged.connect(on_category_changed)
        combo_category.lineEdit().returnPressed.connect(on_category_enter)
        combo_subcategory.currentTextChanged.connect(on_subcategory_changed)
        combo_subcategory.lineEdit().returnPressed.connect(on_subcategory_enter)

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