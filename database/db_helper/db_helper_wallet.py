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
    
    def get_cards_by_pocket(self, pocket_id):
        """Get all cards for a specific pocket."""
        return self.get_all_cards(pocket_id=pocket_id)
    
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
    
    def count_transactions_by_pocket(self, pocket_id):
        """Count transactions for a specific pocket."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM wallet_transactions WHERE pocket_id = ?", (pocket_id,))
        count = cursor.fetchone()['count']
        self.db_manager.close()
        return count
    
    def count_transactions_by_card(self, card_id):
        """Count transactions for a specific card."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM wallet_transactions WHERE card_id = ?", (card_id,))
        count = cursor.fetchone()['count']
        self.db_manager.close()
        return count
    
    def count_transaction_items_by_pocket(self, pocket_id):
        """Count transaction items for a specific pocket (via transactions)."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM wallet_transaction_items wti
            JOIN wallet_transactions wt ON wti.wallet_transaction_id = wt.id
            WHERE wt.pocket_id = ?
        """, (pocket_id,))
        count = cursor.fetchone()['count']
        self.db_manager.close()
        return count
    
    def count_transaction_items_by_card(self, card_id):
        """Count transaction items for a specific card (via transactions)."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM wallet_transaction_items wti
            JOIN wallet_transactions wt ON wti.wallet_transaction_id = wt.id
            WHERE wt.card_id = ?
        """, (card_id,))
        count = cursor.fetchone()['count']
        self.db_manager.close()
        return count
    
    def delete_transactions_by_pocket(self, pocket_id):
        """Delete all transactions for a specific pocket."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_transactions WHERE pocket_id = ?", (pocket_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_transactions_by_card(self, card_id):
        """Delete all transactions for a specific card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_transactions WHERE card_id = ?", (card_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_transaction_items_by_pocket(self, pocket_id):
        """Delete all transaction items for a specific pocket (via transactions)."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            DELETE FROM wallet_transaction_items 
            WHERE wallet_transaction_id IN (
                SELECT id FROM wallet_transactions WHERE pocket_id = ?
            )
        """, (pocket_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_transaction_items_by_card(self, card_id):
        """Delete all transaction items for a specific card (via transactions)."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            DELETE FROM wallet_transaction_items 
            WHERE wallet_transaction_id IN (
                SELECT id FROM wallet_transactions WHERE card_id = ?
            )
        """, (card_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def add_category(self, name, note=""):
        """Add a new wallet category."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO wallet_categories (name, note) VALUES (?, ?)",
            (name, note)
        )
        category_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return category_id
    
    def update_category(self, category_id, name, note=""):
        """Update an existing wallet category."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE wallet_categories SET name = ?, note = ? WHERE id = ?",
            (name, note, category_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_category(self, category_id):
        """Delete a wallet category."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_categories WHERE id = ?", (category_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def add_currency(self, code, name, symbol, note=""):
        """Add a new wallet currency."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO wallet_currency (code, name, symbol, note) VALUES (?, ?, ?, ?)",
            (code, name, symbol, note)
        )
        currency_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return currency_id
    
    def update_currency(self, currency_id, code, name, symbol, note=""):
        """Update an existing wallet currency."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE wallet_currency SET code = ?, name = ?, symbol = ?, note = ? WHERE id = ?",
            (code, name, symbol, note, currency_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_currency(self, currency_id):
        """Delete a wallet currency."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_currency WHERE id = ?", (currency_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def add_transaction_status(self, name, note=""):
        """Add a new wallet transaction status."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO wallet_transaction_statuses (name, note) VALUES (?, ?)",
            (name, note)
        )
        status_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return status_id
    
    def update_transaction_status(self, status_id, name, note=""):
        """Update an existing wallet transaction status."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE wallet_transaction_statuses SET name = ?, note = ? WHERE id = ?",
            (name, note, status_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_transaction_status(self, status_id):
        """Delete a wallet transaction status."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_transaction_statuses WHERE id = ?", (status_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def add_pocket(self, name, pocket_type="", icon="", color="", image="", settings="", note=""):
        """Add a new wallet pocket."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO wallet_pockets (name, pocket_type, icon, color, image, settings, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, pocket_type, icon, color, image, settings, note)
        )
        pocket_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return pocket_id
    
    def update_pocket(self, pocket_id, name, pocket_type="", icon="", color="", image="", settings="", note=""):
        """Update an existing wallet pocket."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE wallet_pockets SET name = ?, pocket_type = ?, icon = ?, color = ?, image = ?, settings = ?, note = ? WHERE id = ?",
            (name, pocket_type, icon, color, image, settings, note, pocket_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_pocket(self, pocket_id):
        """Delete a wallet pocket."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_pockets WHERE id = ?", (pocket_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def add_card(self, pocket_id, card_name, card_number, card_type="", vendor="", issuer="", 
                 status="", virtual=0, issue_date="", expiry_date="", holder_name="", 
                 cvv="", billing_address="", phone="", email="", country="", 
                 card_limit=0.0, balance=0.0, image="", color="", note=""):
        """Add a new wallet card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            """INSERT INTO wallet_cards 
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual, 
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email, 
             country, card_limit, balance, image, color, note) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual,
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email,
             country, card_limit, balance, image, color, note)
        )
        card_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return card_id
    
    def update_card(self, card_id, pocket_id, card_name, card_number, card_type="", vendor="", 
                    issuer="", status="", virtual=0, issue_date="", expiry_date="", 
                    holder_name="", cvv="", billing_address="", phone="", email="", 
                    country="", card_limit=0.0, balance=0.0, image="", color="", note=""):
        """Update an existing wallet card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            """UPDATE wallet_cards SET 
            pocket_id = ?, card_name = ?, card_number = ?, card_type = ?, vendor = ?, 
            issuer = ?, status = ?, virtual = ?, issue_date = ?, expiry_date = ?, 
            holder_name = ?, cvv = ?, billing_address = ?, phone = ?, email = ?, 
            country = ?, card_limit = ?, balance = ?, image = ?, color = ?, note = ? 
            WHERE id = ?""",
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual,
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email,
             country, card_limit, balance, image, color, note, card_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
    
    def delete_card(self, card_id):
        """Delete a wallet card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM wallet_cards WHERE id = ?", (card_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
