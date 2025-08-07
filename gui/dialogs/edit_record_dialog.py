from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
import sys
import os
import re
from pathlib import Path
import shutil
from helpers.markdown_generator import MarkdownGenerator

def sanitize_category_subcategory(name):
    sanitized = name.replace(" ", "_")
    sanitized = re.sub(r'[^A-Za-z0-9_]', '', sanitized)
    return sanitized

def sanitize_name(name):
    sanitized = name.replace(" ", "_")
    sanitized = re.sub(r'[<>:"/\\|?*#&$%@!^()\[\]{};=+`~\']', '', sanitized)
    return sanitized

def get_unique_sanitized_categories(db_manager):
    db_manager.connect()
    categories = db_manager.get_all_categories()
    db_manager.close()
    sanitized_map = {}
    for c in categories:
        key = sanitize_category_subcategory(c)
        if key not in sanitized_map:
            sanitized_map[key] = []
        sanitized_map[key].append(c)
    return list(sanitized_map.keys()), sanitized_map

def get_all_subcategories_for_sanitized(db_manager, sanitized_category, sanitized_map):
    db_manager.connect()
    subcategories = set()
    for orig_cat in sanitized_map.get(sanitized_category, []):
        subs = db_manager.get_subcategories_by_category(orig_cat)
        for s in subs:
            subcategories.add(sanitize_category_subcategory(s))
    db_manager.close()
    return sorted(subcategories)

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

def extract_disk_and_root_from_path(path):
    disk = ""
    root = ""
    if path:
        p = Path(path)
        parts = p.parts
        if sys.platform == "win32":
            if len(parts) >= 2:
                disk = parts[0]
                root = parts[1]
        else:
            if len(parts) >= 2:
                disk = parts[0]
                root = parts[1]
    return disk, root

def extract_disk_path(disk_label):
    if sys.platform == "win32":
        return disk_label.split(" ")[0]
    return disk_label

def get_color_from_main_action(self):
    main_action = self._main_action_dock
    if main_action is None:
        print("Debug: _main_action_dock is not set")
        raise RuntimeError("Color not found in main action color picker")
    if hasattr(main_action, "get_current_color_hex"):
        color = main_action.get_current_color_hex()
        if color and color.startswith("#") and len(color) == 7:
            return color
        print(f"Debug: get_current_color_hex() returned invalid color: {color}")
    else:
        print("Debug: main_action_dock does not have get_current_color_hex")
    raise RuntimeError("Color not found in main action color picker")

class EditRecordDialog(QDialog):
    def __init__(self, record, status_options, db_manager, parent=None, main_action_dock=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Record")
        self.setMinimumWidth(350)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(sanitize_name(record['name']))
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.disk_combo = QComboBox()
        self.disk_combo.setEditable(False)
        disks = []
        if sys.platform == "win32":
            import string
            bitmask = 0
            try:
                import ctypes
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            except Exception:
                bitmask = 0
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    disks.append(f"{letter}:\\")
                bitmask >>= 1
        else:
            disks.append("/")
        self.disk_combo.addItems(disks)
        disk_from_path, root_from_path = extract_disk_and_root_from_path(record.get('path', ''))
        disk_selected = disk_from_path if disk_from_path in disks else disks[0]
        folder_selected = root_from_path
        self.disk_combo.setCurrentText(disk_selected)
        self.root_combo = QComboBox()
        self.root_combo.setEditable(False)
        disk_path = extract_disk_path(self.disk_combo.currentText())
        folders = get_first_level_folders(disk_path)
        if folder_selected and folder_selected not in folders:
            folders.insert(0, folder_selected)
        self.root_combo.addItems(folders)
        if folder_selected:
            self.root_combo.setCurrentText(folder_selected)
        self.disk_combo.currentTextChanged.connect(self._on_disk_changed)
        self.status_combo = QComboBox()
        self.status_combo.addItems(status_options)
        self.status_combo.setCurrentText(record['status'])
        unique_cats, self._sanitized_cat_map = get_unique_sanitized_categories(db_manager)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(False)
        self.category_combo.addItems([""] + unique_cats)
        self.category_combo.setCurrentText(sanitize_category_subcategory(record.get('category') or ""))
        sanitized_cat = sanitize_category_subcategory(record.get('category') or "")
        subcategories = get_all_subcategories_for_sanitized(db_manager, sanitized_cat, self._sanitized_cat_map)
        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(False)
        self.subcategory_combo.addItems([""] + subcategories)
        self.subcategory_combo.setCurrentText(sanitize_category_subcategory(record.get('subcategory') or ""))
        self.date_edit = QLineEdit(record['date'])
        self.date_edit.setEnabled(False)
        self.full_path_edit = QLineEdit(record.get('path', ''))
        self.full_path_edit.setEnabled(False)
        layout.addRow("Date", self.date_edit)
        layout.addRow("Name", self.name_edit)
        layout.addRow("Disk", self.disk_combo)
        layout.addRow("Root", self.root_combo)
        layout.addRow("Status", self.status_combo)
        layout.addRow("Category", self.category_combo)
        layout.addRow("Subcategory", self.subcategory_combo)
        layout.addRow("Full Path", self.full_path_edit)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self._original_path = record.get('path', '')
        self._original_name = record.get('name', '')
        self._original_category = sanitize_category_subcategory(record.get('category') or "")
        self._original_subcategory = sanitize_category_subcategory(record.get('subcategory') or "")
        self._db_manager = db_manager
        self.markdown_generator = MarkdownGenerator()
        self._main_action_dock = main_action_dock

    def _on_name_changed(self, text):
        sanitized = sanitize_name(text)
        if sanitized != text:
            self.name_edit.setText(sanitized)

    def _on_disk_changed(self, text):
        disk_path = extract_disk_path(text)
        folders = get_first_level_folders(disk_path)
        current_root = self.root_combo.currentText()
        self.root_combo.clear()
        self.root_combo.addItems(folders)
        if current_root in folders:
            self.root_combo.setCurrentText(current_root)
        elif folders:
            self.root_combo.setCurrentIndex(0)

    def _on_category_changed(self, text):
        sanitized_cat = sanitize_category_subcategory(text)
        subcategories = get_all_subcategories_for_sanitized(self._db_manager, sanitized_cat, self._sanitized_cat_map)
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("")
        self.subcategory_combo.addItems(subcategories)

    def _on_accept(self):
        import re
        data = self.get_data()
        disk = self.disk_combo.currentText()
        folder = self.root_combo.currentText().strip()
        category = data['category']
        subcategory = data['subcategory']
        date = data['date']
        name = data['name']
        # Normalize date to YYYY_MM_DD
        def normalize_date(date_str):
            # Accepts DD_MM_YYYY, MM_DD_YYYY, YYYY_MM_DD, etc. Returns YYYY_MM_DD
            if not date_str:
                return ""
            # Try to extract 3 numbers
            parts = re.split(r'[_\-]', date_str)
            nums = [p for p in parts if p.isdigit() and len(p) == 4 or (p.isdigit() and len(p) <= 2)]
            if len(nums) == 3:
                # If first is 4 digits, assume YYYY_MM_DD
                if len(nums[0]) == 4:
                    return f"{nums[0]}_{nums[1].zfill(2)}_{nums[2].zfill(2)}"
                # If last is 4 digits, assume DD_MM_YYYY or MM_DD_YYYY
                elif len(nums[2]) == 4:
                    return f"{nums[2]}_{nums[1].zfill(2)}_{nums[0].zfill(2)}"
            # Fallback: just return as is
            return date_str

        date_norm = normalize_date(date)
        path_parts = []
        if disk and not disk.endswith("\\"):
            disk = disk + "\\"
        if disk:
            path_parts.append(disk.rstrip("\\"))
        if folder:
            path_parts.append(folder)
        if category:
            path_parts.append(category)
        if subcategory:
            path_parts.append(subcategory)
        if date_norm:
            path_parts.append(date_norm)
        if name:
            path_parts.append(name)
        new_path = "\\".join(path_parts)
        old_path = self._original_path
        old_name = self._original_name
        if new_path != old_path:
            try:
                self._db_manager.connect()
                if not os.path.exists(new_path):
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.move(old_path, new_path)
                old_md = Path(old_path) / f"{old_name}.md"
                new_md = Path(new_path) / f"{name}.md"
                if old_md.exists():
                    try:
                        os.remove(str(old_md))
                    except Exception:
                        pass
                color = get_color_from_main_action(self)
                self.markdown_generator.create_markdown_file(
                    folder_path=new_path,
                    name=name,
                    root=folder,
                    category=category,
                    subcategory=subcategory,
                    date_path=date_norm,
                    full_path=new_path,
                    color=color
                )
            except Exception as e:
                print(f"Error moving folder or markdown: {e}")
            finally:
                self._db_manager.close()
        self.full_path_edit.setText(new_path)
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "root": self.root_combo.currentText().strip(),
            "status": self.status_combo.currentText(),
            "category": sanitize_category_subcategory(self.category_combo.currentText().strip()),
            "subcategory": sanitize_category_subcategory(self.subcategory_combo.currentText().strip()),
            "date": self.date_edit.text().strip(),
            "full_path": self.full_path_edit.text().strip()
        }