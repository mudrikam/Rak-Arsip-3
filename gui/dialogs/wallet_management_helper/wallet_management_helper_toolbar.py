from PySide6.QtWidgets import QToolBar, QWidget, QHBoxLayout
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
import qtawesome as qta


class WalletToolbar(QWidget):
    add_clicked = Signal()
    edit_clicked = Signal()
    delete_clicked = Signal()
    refresh_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.toolbar = QToolBar()
        
        self.add_action = QAction(qta.icon('fa6s.plus'), "Add", self)
        self.add_action.triggered.connect(self.add_clicked.emit)
        self.toolbar.addAction(self.add_action)
        
        self.edit_action = QAction(qta.icon('fa6s.pen-to-square'), "Edit", self)
        self.edit_action.triggered.connect(self.edit_clicked.emit)
        self.toolbar.addAction(self.edit_action)
        
        self.delete_action = QAction(qta.icon('fa6s.trash'), "Delete", self)
        self.delete_action.triggered.connect(self.delete_clicked.emit)
        self.toolbar.addAction(self.delete_action)
        
        self.toolbar.addSeparator()
        
        self.refresh_action = QAction(qta.icon('fa6s.arrows-rotate'), "Refresh", self)
        self.refresh_action.triggered.connect(self.refresh_clicked.emit)
        self.toolbar.addAction(self.refresh_action)
        
        layout.addWidget(self.toolbar)
        layout.addStretch()
        
        self.setLayout(layout)
