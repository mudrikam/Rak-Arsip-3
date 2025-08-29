import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from gui.windows.main_window import MainWindow

BASEDIR = os.path.abspath(os.path.dirname(__file__))

log_path = os.path.join(BASEDIR, "rakarsip.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    filename=log_path,
    filemode="a"
)

if __name__ == "__main__":
    try:
        logging.info("Application started.")
        app = QApplication(sys.argv)
        window = MainWindow(BASEDIR)
        window.show()
        exit_code = app.exec()
        logging.info(f"Application exited with code {exit_code}.")
        sys.exit(exit_code)
    except Exception as e:
        logging.exception("Unhandled exception caused application to exit.")
        sys.exit(1)
