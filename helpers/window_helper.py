from PySide6.QtGui import QIcon
from manager.config_manager import ConfigManager
import os
import sys

if sys.platform == "win32":
    import ctypes

def get_window_config(basedir):
    config_path = os.path.join(basedir, "configs", "window_config.json")
    return ConfigManager(config_path)

def set_app_user_model_id(app_id):
    if sys.platform == "win32" and app_id:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

def set_window_icon(window, icon_path):
    window.setWindowIcon(QIcon(icon_path))
