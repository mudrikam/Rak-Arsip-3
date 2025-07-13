from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QFrame, QLabel, QComboBox, QHBoxLayout
import sys
import os

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

class MainActionDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Main Action", parent)
        container = QWidget(self)
        layout = QVBoxLayout(container)
        frame = QFrame(container)
        frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QVBoxLayout(frame)

        # Disk selector row
        disk_row = QHBoxLayout()
        label_disk = QLabel("Disk", frame)
        combo_disk = QComboBox(frame)
        disks = get_available_disks()
        combo_disk.addItems(disks)
        disk_row.addWidget(label_disk)
        disk_row.addWidget(combo_disk)
        frame_layout.addLayout(disk_row)

        # Folder selector row
        folder_row = QHBoxLayout()
        label_folder = QLabel("Folder", frame)
        combo_folder = QComboBox(frame)
        combo_folder.setEnabled(False)
        folder_row.addWidget(label_folder)
        folder_row.addWidget(combo_folder)
        frame_layout.addLayout(folder_row)

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

        combo_disk.currentIndexChanged.connect(on_disk_changed)

        frame.setLayout(frame_layout)
        layout.addWidget(frame)
        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)
