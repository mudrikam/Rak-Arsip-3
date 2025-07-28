from PySide6.QtWidgets import QDialog, QVBoxLayout

class ClientDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Data")
        layout = QVBoxLayout(self)
