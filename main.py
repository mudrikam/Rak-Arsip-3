from PySide6.QtWidgets import QApplication
from gui.windows.main_window import MainWindow
import sys
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(BASEDIR)
    window.show()
    sys.exit(app.exec())
