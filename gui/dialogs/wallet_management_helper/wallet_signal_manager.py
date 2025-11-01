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
        self.pocket_changed.emit()

    def emit_card_changed(self):
        """Emit signal for card data change."""
        self.card_changed.emit()

    def emit_category_changed(self):
        """Emit signal for category data change."""
        self.category_changed.emit()

    def emit_currency_changed(self):
        """Emit signal for currency data change."""
        self.currency_changed.emit()

    def emit_location_changed(self):
        """Emit signal for location data change."""
        self.location_changed.emit()

    def emit_status_changed(self):
        """Emit signal for status data change."""
        self.status_changed.emit()

    def emit_transaction_changed(self):
        """Emit signal for transaction data change."""
        self.transaction_changed.emit()
