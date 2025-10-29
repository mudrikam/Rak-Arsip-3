from PySide6.QtCore import QObject, Signal


class WalletSignalManager(QObject):
    """Centralized signal manager for wallet data changes."""
    
    # Signals for data changes
    pocket_changed = Signal()  # Emitted when pocket data changes
    card_changed = Signal()  # Emitted when card data changes
    category_changed = Signal()  # Emitted when category data changes
    currency_changed = Signal()  # Emitted when currency data changes
    location_changed = Signal()  # Emitted when location data changes
    status_changed = Signal()  # Emitted when status data changes
    transaction_changed = Signal()  # Emitted when transaction data changes
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of signal manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def emit_pocket_changed(self):
        """Emit signal for pocket data change."""
        print("Signal: Pocket data changed")
        self.pocket_changed.emit()
    
    def emit_card_changed(self):
        """Emit signal for card data change."""
        print("Signal: Card data changed")
        self.card_changed.emit()
    
    def emit_category_changed(self):
        """Emit signal for category data change."""
        print("Signal: Category data changed")
        self.category_changed.emit()
    
    def emit_currency_changed(self):
        """Emit signal for currency data change."""
        print("Signal: Currency data changed")
        self.currency_changed.emit()
    
    def emit_location_changed(self):
        """Emit signal for location data change."""
        print("Signal: Location data changed")
        self.location_changed.emit()
    
    def emit_status_changed(self):
        """Emit signal for status data change."""
        print("Signal: Status data changed")
        self.status_changed.emit()
    
    def emit_transaction_changed(self):
        """Emit signal for transaction data change."""
        print("Signal: Transaction data changed")
        self.transaction_changed.emit()
