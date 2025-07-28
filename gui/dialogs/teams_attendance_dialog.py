from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel

class TeamsAttendanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Teams Attendance")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        label = QLabel("Attendance dialog is under construction.", self)
        layout.addWidget(label)
