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

class DiskScanThread(QThread):
    disks_found = Signal(list)
    def run(self):
        disks = get_available_disks()
        self.disks_found.emit(disks)

class MainActionDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Main Action", parent)
        container = QWidget(self)
        main_layout = QHBoxLayout(container)

        # Frame kiri: Disk & Folder
        frame_left = QFrame(container)
        frame_left.setFrameShape(QFrame.StyledPanel)
        frame_left_layout = QVBoxLayout(frame_left)

        disk_row = QHBoxLayout()
        label_disk = QLabel("Disk", frame_left)
        combo_disk = QComboBox(frame_left)
        combo_disk.setMinimumWidth(180)
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

        def on_disk_changed(index):
            if index < 0:
                combo_folder.clear()
                combo_folder.setEnabled(False)
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

        combo_disk.currentIndexChanged.connect(on_disk_changed)

        frame_left.setLayout(frame_left_layout)
        main_layout.addWidget(frame_left)

        # Frame tengah: Category & Sub Category
        frame_middle = QFrame(container)
        frame_middle.setFrameShape(QFrame.StyledPanel)
        frame_middle_layout = QVBoxLayout(frame_middle)

        category_row = QHBoxLayout()
        label_category = QLabel("Category", frame_middle)
        combo_category = QComboBox(frame_middle)
        combo_category.setEnabled(False)
        category_row.addWidget(label_category)
        category_row.addWidget(combo_category)
        frame_middle_layout.addLayout(category_row)

        subcategory_row = QHBoxLayout()
        label_subcategory = QLabel("Sub", frame_middle)
        combo_subcategory = QComboBox(frame_middle)
        combo_subcategory.setEnabled(False)
        subcategory_row.addWidget(label_subcategory)
        subcategory_row.addWidget(combo_subcategory)
        frame_middle_layout.addLayout(subcategory_row)

        frame_middle.setLayout(frame_middle_layout)
        main_layout.addWidget(frame_middle)

        # Frame kanan: Checklist, Date, Markdown, Open Explorer (semua QCheckBox)
        frame_right = QFrame(container)
        frame_right.setFrameShape(QFrame.StyledPanel)
        frame_right_layout = QVBoxLayout(frame_right)
        date_check = QCheckBox("Date", frame_right)
        markdown_check = QCheckBox("Markdown", frame_right)
        open_explorer_check = QCheckBox("Open Explorer", frame_right)
        frame_right_layout.addWidget(date_check)
        frame_right_layout.addWidget(markdown_check)
        frame_right_layout.addWidget(open_explorer_check)
        frame_right.setLayout(frame_right_layout)
        main_layout.addWidget(frame_right)

        # Frame paling kanan: Template dropdown, color picker (qtawesome), no reset
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
            # Random hue, S=0.7, V=0.9
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

        container.setLayout(main_layout)
        self.setWidget(container)

        self._combo_disk = combo_disk
        self._combo_folder = combo_folder
        self._on_disk_changed = on_disk_changed
        self._adjust_folder_width = adjust_folder_width

        self._disk_thread = DiskScanThread()
        self._disk_thread.disks_found.connect(self._on_disks_ready)
        self._disk_thread.start()

    @Slot(list)
    def _on_disks_ready(self, disks):
        self._combo_disk.clear()
        self._combo_disk.addItems(disks)
        self._combo_disk.setEnabled(True)
        self._adjust_folder_width()
        if disks:
            self._combo_disk.setCurrentIndex(0)
            self._on_disk_changed(0)
        else:
            self._combo_folder.clear()
            self._combo_folder.setEnabled(False)
