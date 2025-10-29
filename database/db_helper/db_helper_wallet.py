import sqlite3
from datetime import datetime


class DatabaseWalletHelper:
    """Helper class for wallet-related database operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all_pockets(self):
        """Get all wallet pockets."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT * FROM wallet_pockets ORDER BY name")
        rows = cursor.fetchall()
        pockets = [dict(row) for row in rows]
        self.db_manager.close()
        return pockets
    
    def get_all_cards(self, pocket_id=None):
        """Get all wallet cards, optionally filtered by pocket."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        if pocket_id:
            cursor.execute("SELECT * FROM wallet_cards WHERE pocket_id = ? ORDER BY card_name", (pocket_id,))
        else:
            cursor.execute("SELECT * FROM wallet_cards ORDER BY card_name")
        rows = cursor.fetchall()
        cards = [dict(row) for row in rows]
        self.db_manager.close()
        return cards
    
    def get_all_categories(self):
        """Get all wallet transaction categories."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT * FROM wallet_categories ORDER BY name")
        rows = cursor.fetchall()
        categories = [dict(row) for row in rows]
        self.db_manager.close()
        return categories
    
    def get_all_currencies(self):
        """Get all wallet currencies."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT * FROM wallet_currency ORDER BY code")
        rows = cursor.fetchall()
        currencies = [dict(row) for row in rows]
        self.db_manager.close()
        return currencies
    
    def get_all_transaction_statuses(self):
        """Get all wallet transaction statuses."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT * FROM wallet_transaction_statuses ORDER BY name")
        rows = cursor.fetchall()
        statuses = [dict(row) for row in rows]
        self.db_manager.close()
        return statuses
    
    def get_all_locations(self):
        """Get all wallet transaction locations."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT * FROM wallet_transaction_locations ORDER BY name")
        rows = cursor.fetchall()
        locations = [dict(row) for row in rows]
        self.db_manager.close()
        return locations
    
    def get_transactions(self, pocket_id=None, limit=100, offset=0):
        """Get wallet transactions, optionally filtered by pocket."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        if pocket_id:
            cursor.execute("""
                SELECT wt.*, 
                       wc.name as category_name,
                       wts.name as status_name,
                       wcur.code as currency_code,
                       wtl.name as location_name
                FROM wallet_transactions wt
                LEFT JOIN wallet_categories wc ON wt.category_id = wc.id
                LEFT JOIN wallet_transaction_statuses wts ON wt.status_id = wts.id
                LEFT JOIN wallet_currency wcur ON wt.currency_id = wcur.id
                LEFT JOIN wallet_transaction_locations wtl ON wt.location_id = wtl.id
                WHERE wt.pocket_id = ?
                ORDER BY wt.transaction_date DESC
                LIMIT ? OFFSET ?
            """, (pocket_id, limit, offset))
        else:
            cursor.execute("""
                SELECT wt.*, 
                       wc.name as category_name,
                       wts.name as status_name,
                       wcur.code as currency_code,
                       wtl.name as location_name
                FROM wallet_transactions wt
                LEFT JOIN wallet_categories wc ON wt.category_id = wc.id
                LEFT JOIN wallet_transaction_statuses wts ON wt.status_id = wts.id
                LEFT JOIN wallet_currency wcur ON wt.currency_id = wcur.id
                LEFT JOIN wallet_transaction_locations wtl ON wt.location_id = wtl.id
                ORDER BY wt.transaction_date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        rows = cursor.fetchall()
        transactions = [dict(row) for row in rows]
        self.db_manager.close()
        return transactions
    
    def get_transaction_items(self, transaction_id):
        """Get all items for a specific transaction."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT * FROM wallet_transaction_items 
            WHERE wallet_transaction_id = ?
            ORDER BY id
        """, (transaction_id,))
        rows = cursor.fetchall()
        items = [dict(row) for row in rows]
        self.db_manager.close()
        return items
