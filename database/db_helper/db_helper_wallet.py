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
    
    # Transaction operations
    def get_all_transactions(self, search_text="", transaction_type="", pocket_id=None, 
                           category_id=None, date_from="", date_to="", limit=None, offset=None):
        """Get all transactions with filters and pagination."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        # Build query with filters
        query = """
            SELECT 
                t.id,
                t.transaction_date,
                t.transaction_name,
                t.transaction_type,
                p.name as pocket_name,
                c.name as category_name,
                s.name as status_name,
                COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                cu.symbol as currency_symbol
            FROM wallet_transactions t
            LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
            LEFT JOIN wallet_categories c ON t.category_id = c.id
            LEFT JOIN wallet_transaction_statuses s ON t.status_id = s.id
            LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
            LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
            WHERE 1=1
        """
        
        params = []
        
        if search_text:
            query += " AND t.transaction_name LIKE ?"
            params.append(f"%{search_text}%")
        
        if transaction_type:
            query += " AND t.transaction_type = ?"
            params.append(transaction_type)
        
        if pocket_id:
            query += " AND t.pocket_id = ?"
            params.append(pocket_id)
        
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)
        
        if date_from and date_to:
            query += " AND DATE(t.transaction_date) BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        
        query += " GROUP BY t.id ORDER BY t.transaction_date DESC"
        
        # Add pagination
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        transactions = [dict(row) for row in rows]
        self.db_manager.close()
        return transactions
    
    def count_transactions(self, search_text="", transaction_type="", pocket_id=None, 
                          category_id=None, date_from="", date_to=""):
        """Count transactions with filters."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            query = """
                SELECT COUNT(DISTINCT t.id)
                FROM wallet_transactions t
                WHERE 1=1
            """
            
            params = []
            
            if search_text:
                query += " AND t.transaction_name LIKE ?"
                params.append(f"%{search_text}%")
            
            if transaction_type:
                query += " AND t.transaction_type = ?"
                params.append(transaction_type)
            
            if pocket_id:
                query += " AND t.pocket_id = ?"
                params.append(pocket_id)
            
            if category_id:
                query += " AND t.category_id = ?"
                params.append(category_id)
            
            if date_from and date_to:
                query += " AND DATE(t.transaction_date) BETWEEN ? AND ?"
                params.extend([date_from, date_to])
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            return count
            
        except Exception as e:
            print(f"Error counting transactions: {e}")
            return 0
        finally:
            self.db_manager.close()
    
    def add_transaction(self, pocket_id, category_id, status_id, currency_id, location_id,
                       transaction_name, transaction_date, transaction_type, tags="", note=""):
        """Add a new transaction."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO wallet_transactions 
            (pocket_id, category_id, status_id, currency_id, location_id, 
             transaction_name, transaction_date, transaction_type, tags, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pocket_id, category_id, status_id, currency_id, location_id,
              transaction_name, transaction_date, transaction_type, tags, note))
        
        transaction_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return transaction_id
    
    def add_transaction_item(self, wallet_transaction_id, item_type, sku, item_name, 
                           item_description, quantity, unit, amount, width=None, height=None,
                           depth=None, weight=None, material="", color="", file_url="",
                           license_key="", expiry_date=None, digital_type="", note=""):
        """Add a transaction item."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO wallet_transaction_items
            (wallet_transaction_id, item_type, sku, item_name, item_description,
             quantity, unit, amount, width, height, depth, weight, material, color,
             file_url, license_key, expiry_date, digital_type, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (wallet_transaction_id, item_type, sku, item_name, item_description,
              quantity, unit, amount, width, height, depth, weight, material, color,
              file_url, license_key, expiry_date, digital_type, note))
        
        item_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return item_id
    
    def delete_transaction(self, transaction_id):
        """Delete a transaction and its items and invoice images."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            # Get invoice image paths before deletion for file cleanup
            cursor.execute("SELECT image_path FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            invoice_paths = [row[0] for row in cursor.fetchall()]
            
            # Delete invoice images from database
            cursor.execute("DELETE FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            # Delete transaction items (foreign key constraint)
            cursor.execute("DELETE FROM wallet_transaction_items WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            # Delete transaction
            cursor.execute("DELETE FROM wallet_transactions WHERE id = ?", (transaction_id,))
            
            self.db_manager.connection.commit()
            
            # Delete physical image files if they exist
            import os
            for image_path in invoice_paths:
                try:
                    # Try to get basedir from parent components
                    basedir = getattr(self.db_manager, 'basedir', None)
                    if basedir and image_path:
                        full_path = os.path.join(basedir, image_path)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            print(f"Deleted image file: {full_path}")
                except Exception as e:
                    print(f"Warning: Could not delete image file {image_path}: {e}")
            
        except Exception as e:
            print(f"Error deleting transaction: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def get_transaction_by_id(self, transaction_id):
        """Get transaction details by ID."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                SELECT t.*, p.name as pocket_name, c.name as category_name, 
                       s.name as status_name, cu.code as currency_code,
                       l.name as location_name
                FROM wallet_transactions t
                LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
                LEFT JOIN wallet_categories c ON t.category_id = c.id
                LEFT JOIN wallet_transaction_statuses s ON t.status_id = s.id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                LEFT JOIN wallet_transaction_locations l ON t.location_id = l.id
                WHERE t.id = ?
            """, (transaction_id,))
            
            transaction = cursor.fetchone()
            return dict(transaction) if transaction else None
            
        except Exception as e:
            print(f"Error getting transaction by ID: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def get_transaction_items(self, transaction_id):
        """Get all items for a transaction."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                SELECT * FROM wallet_transaction_items 
                WHERE wallet_transaction_id = ?
                ORDER BY id
            """, (transaction_id,))
            
            items = cursor.fetchall()
            return [dict(item) for item in items]
            
        except Exception as e:
            print(f"Error getting transaction items: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def update_transaction(self, transaction_id, pocket_id, category_id, status_id, 
                          currency_id, location_id, transaction_name, transaction_date, 
                          transaction_type, tags="", note=""):
        """Update an existing transaction."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                UPDATE wallet_transactions 
                SET pocket_id=?, category_id=?, status_id=?, currency_id=?, location_id=?,
                    transaction_name=?, transaction_date=?, transaction_type=?, tags=?, note=?
                WHERE id=?
            """, (pocket_id, category_id, status_id, currency_id, location_id,
                  transaction_name, transaction_date, transaction_type, tags, note, transaction_id))
            
            self.db_manager.connection.commit()
            return transaction_id
            
        except Exception as e:
            print(f"Error updating transaction: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def delete_transaction_items(self, transaction_id):
        """Delete all items for a transaction."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("DELETE FROM wallet_transaction_items WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            self.db_manager.connection.commit()
            
        except Exception as e:
            print(f"Error deleting transaction items: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def count_transaction_items(self, transaction_id):
        """Count transaction items for a transaction."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM wallet_transaction_items WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            count = cursor.fetchone()[0]
            return count
            
        except Exception as e:
            print(f"Error counting transaction items: {e}")
            return 0
        finally:
            self.db_manager.close()
    
    def count_invoice_images(self, transaction_id):
        """Count invoice images for a transaction."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            count = cursor.fetchone()[0]
            return count
            
        except Exception as e:
            print(f"Error counting invoice images: {e}")
            return 0
        finally:
            self.db_manager.close()
    
    def get_invoice_images(self, transaction_id):
        """Get invoice image paths for a transaction."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("SELECT image_path FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            images = cursor.fetchall()
            return [img[0] for img in images] if images else []
            
        except Exception as e:
            print(f"Error getting invoice images: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def add_transaction_invoice_image(self, transaction_id, image_path, image_name=None, 
                                    image_size=None, image_type=None, description=None):
        """Add invoice image for transaction."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                INSERT INTO wallet_transactions_invoice_prove
                (wallet_transaction_id, image_path, image_name, image_size, image_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (transaction_id, image_path, image_name, image_size, image_type, description))
            
            invoice_id = cursor.lastrowid
            self.db_manager.connection.commit()
            return invoice_id
            
        except Exception as e:
            print(f"Error adding transaction invoice image: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def get_transaction_invoice_image(self, transaction_id):
        """Get invoice image for transaction."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                SELECT * FROM wallet_transactions_invoice_prove 
                WHERE wallet_transaction_id = ?
                ORDER BY uploaded_at DESC
                LIMIT 1
            """, (transaction_id,))
            
            invoice = cursor.fetchone()
            return dict(invoice) if invoice else None
            
        except Exception as e:
            print(f"Error getting transaction invoice image: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def update_transaction_invoice_image(self, transaction_id, image_path, image_name=None,
                                       image_size=None, image_type=None, description=None):
        """Update or add invoice image for transaction."""
        try:
            # Check if invoice exists
            existing = self.get_transaction_invoice_image(transaction_id)
            
            if existing:
                # Update existing
                self.db_manager.connect(write=True)
                cursor = self.db_manager.connection.cursor()
                
                cursor.execute("""
                    UPDATE wallet_transactions_invoice_prove 
                    SET image_path=?, image_name=?, image_size=?, image_type=?, description=?,
                        uploaded_at=CURRENT_TIMESTAMP
                    WHERE wallet_transaction_id=?
                """, (image_path, image_name, image_size, image_type, description, transaction_id))
                
                self.db_manager.connection.commit()
                return existing['id']
            else:
                # Add new
                return self.add_transaction_invoice_image(transaction_id, image_path, image_name,
                                                        image_size, image_type, description)
                
        except Exception as e:
            print(f"Error updating transaction invoice image: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def delete_transaction_invoice_image(self, transaction_id):
        """Delete invoice image for transaction."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("DELETE FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            self.db_manager.connection.commit()
            
        except Exception as e:
            print(f"Error deleting transaction invoice image: {e}")
            raise
        finally:
            self.db_manager.close()
