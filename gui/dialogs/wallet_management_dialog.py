from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from gui.dialogs.wallet_management_helper.wallet_management_helper_sidebar import WalletSidebar
from gui.dialogs.wallet_management_helper.wallet_management_helper_central import WalletCentral


class WalletManagementDialog(QDialog):
    def __init__(self, parent=None, db_manager=None, basedir=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.basedir = basedir
        self.setWindowTitle("Wallet Management")
        self.setModal(True)
        self.setMinimumSize(900, 400)
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        

        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.sidebar = WalletSidebar(self)
        self.sidebar.section_changed.connect(self.on_section_changed)
        content_layout.addWidget(self.sidebar)
        
        self.central = WalletCentral(db_manager=self.db_manager, basedir=self.basedir, parent=self)
        content_layout.addWidget(self.central, 1)
        
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
    

    
    def on_section_changed(self, section_name):
        self.central.load_section(section_name)
