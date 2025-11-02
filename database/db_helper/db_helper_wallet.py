import sqlite3
import os
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

    def get_location_by_id(self, location_id):
        """Get a single location record by ID."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("SELECT * FROM wallet_transaction_locations WHERE id = ?", (location_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting location by id: {e}")
            raise
        finally:
            self.db_manager.close()
    
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

    # Location operations moved from GUI into DB helper to centralize DB + filesystem logic
    def add_location(self, name, location_type="", address="", city="", country="", postal_code="", online_url="", contact="", phone="", email="", status="", description="", rating=None, note="", image_src_path=None, basedir=None):
        """Add a new transaction location and save its image into a per-id folder.

        image_src_path: optional path to an uploaded image (on disk)
        basedir: base project directory used to build managed image paths
        """
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                INSERT INTO wallet_transaction_locations
                (name, location_type, address, city, country, postal_code, online_url, contact, phone, email, status, description, rating, note, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, location_type, address, city, country, postal_code, online_url, contact, phone, email, status, description, rating, note, None))

            location_id = cursor.lastrowid
            self.db_manager.connection.commit()

            # If an image source was provided, save it into managed folder using location_id
            if image_src_path and basedir:
                try:
                    from helpers.image_helper import ImageHelper
                    output_path = ImageHelper.generate_location_image_path(basedir, location_id, image_src_path)
                    saved = ImageHelper.save_image_to_file(image_src_path, output_path)
                    if saved:
                        rel = os.path.relpath(output_path, basedir).replace("\\", "/")
                        self.db_manager.connect(write=True)
                        cursor = self.db_manager.connection.cursor()
                        cursor.execute("UPDATE wallet_transaction_locations SET image = ? WHERE id = ?", (rel, location_id))
                        self.db_manager.connection.commit()
                        try:
                            src_abs = image_src_path if os.path.isabs(image_src_path) else os.path.join(basedir, image_src_path)
                            tmp_root = os.path.abspath(os.path.join(basedir, "images", "locations", "tmp"))
                            src_abs_norm = os.path.abspath(src_abs)
                            if os.path.exists(src_abs_norm) and os.path.commonpath([tmp_root, src_abs_norm]) == tmp_root:
                                try:
                                    os.remove(src_abs_norm)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Warning: failed saving location image for location {location_id}: {e}")

            return location_id

        except Exception as e:
            print(f"Error adding location: {e}")
            raise
        finally:
            self.db_manager.close()

    def update_location(self, location_id, name, location_type="", address="", city="", country="", postal_code="", online_url="", contact="", phone="", email="", status="", description="", rating=None, note="", image_src_path=None, basedir=None):
        """Update an existing location and optionally replace its image.

        If image_src_path is provided, save into per-id managed folder and attempt to remove the old image file.
        """
        try:
            # Retrieve existing image path so we can cleanup if replaced
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("SELECT image FROM wallet_transaction_locations WHERE id = ?", (location_id,))
            row = cursor.fetchone()
            existing_image = row['image'] if row and 'image' in row.keys() else None
            self.db_manager.close()

            new_rel = existing_image

            if image_src_path and basedir:
                from helpers.image_helper import ImageHelper
                output_path = ImageHelper.generate_location_image_path(basedir, location_id, image_src_path)
                saved = ImageHelper.save_image_to_file(image_src_path, output_path)
                if saved:
                    new_rel = os.path.relpath(output_path, basedir).replace("\\", "/")

            # Update record (image will be updated if new_rel set)
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                UPDATE wallet_transaction_locations
                SET name = ?, location_type = ?, address = ?, city = ?, country = ?, postal_code = ?,
                    online_url = ?, contact = ?, phone = ?, email = ?, status = ?, description = ?, rating = ?, note = ?, image = ?
                WHERE id = ?
            """, (name, location_type, address, city, country, postal_code, online_url, contact, phone, email, status, description, rating, note, new_rel, location_id))
            self.db_manager.connection.commit()

            # If we saved a new image, try to remove old image file to prevent orphan
            if image_src_path and basedir and existing_image and existing_image != new_rel:
                try:
                    old_abs = os.path.join(basedir, existing_image)
                    new_abs = os.path.abspath(os.path.join(basedir, new_rel)) if new_rel else None
                    if os.path.exists(old_abs) and (not new_abs or os.path.abspath(old_abs) != new_abs):
                        os.remove(old_abs)
                        print(f"Removed old location image: {old_abs}")
                except Exception as e:
                    print(f"Warning: could not remove old location image {existing_image}: {e}")

            if image_src_path and basedir:
                try:
                    src_abs = image_src_path if os.path.isabs(image_src_path) else os.path.join(basedir, image_src_path)
                    tmp_root = os.path.abspath(os.path.join(basedir, "images", "locations", "tmp"))
                    src_abs_norm = os.path.abspath(src_abs)
                    if os.path.exists(src_abs_norm) and os.path.commonpath([tmp_root, src_abs_norm]) == tmp_root:
                        try:
                            os.remove(src_abs_norm)
                        except Exception:
                            pass
                except Exception:
                    pass

            return location_id

        except Exception as e:
            print(f"Error updating location: {e}")
            raise
        finally:
            self.db_manager.close()

    def delete_location(self, location_id):
        """Delete a location and its associated image file (if basedir is available on db_manager).

        Note: db_manager may expose `basedir` attribute so we can delete the physical file.
        """
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("SELECT image FROM wallet_transaction_locations WHERE id = ?", (location_id,))
            row = cursor.fetchone()
            image_path = row['image'] if row and 'image' in row.keys() else None

            cursor.execute("DELETE FROM wallet_transaction_locations WHERE id = ?", (location_id,))
            self.db_manager.connection.commit()

            
            try:
                basedir = getattr(self.db_manager, 'basedir', None)
                if basedir and image_path:
                    full_path = os.path.join(basedir, image_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        print(f"Deleted location image file: {full_path}")
            except Exception as e:
                print(f"Warning: could not delete physical location image: {e}")

        except Exception as e:
            print(f"Error deleting location: {e}")
            raise
        finally:
            self.db_manager.close()
    
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
                 card_limit=0.0, image="", color="", note=""):
        """Add a new wallet card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            """INSERT INTO wallet_cards 
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual, 
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email, 
             country, card_limit, image, color, note) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual,
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email,
             country, card_limit, image, color, note)
        )
        card_id = cursor.lastrowid
        self.db_manager.connection.commit()
        self.db_manager.close()
        return card_id
    
    def update_card(self, card_id, pocket_id, card_name, card_number, card_type="", vendor="", 
                    issuer="", status="", virtual=0, issue_date="", expiry_date="", 
                    holder_name="", cvv="", billing_address="", phone="", email="", 
                    country="", card_limit=0.0, image="", color="", note=""):
        """Update an existing wallet card."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            """UPDATE wallet_cards SET 
            pocket_id = ?, card_name = ?, card_number = ?, card_type = ?, vendor = ?, 
            issuer = ?, status = ?, virtual = ?, issue_date = ?, expiry_date = ?, 
            holder_name = ?, cvv = ?, billing_address = ?, phone = ?, email = ?, 
            country = ?, card_limit = ?, image = ?, color = ?, note = ? 
            WHERE id = ?""",
            (pocket_id, card_name, card_number, card_type, vendor, issuer, status, virtual,
             issue_date, expiry_date, holder_name, cvv, billing_address, phone, email,
             country, card_limit, image, color, note, card_id)
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
                ca.card_name as card_name,
                c.name as category_name,
                s.name as status_name,
                COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                cu.symbol as currency_symbol
            FROM wallet_transactions t
            LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
            LEFT JOIN wallet_cards ca ON t.card_id = ca.id
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
        
        if pocket_id is not None and pocket_id != "":
            query += " AND t.pocket_id = ?"
            params.append(pocket_id)
        
        if category_id is not None and category_id != "":
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
            
            if pocket_id is not None and pocket_id != "":
                query += " AND t.pocket_id = ?"
                params.append(pocket_id)
            
            if category_id is not None and category_id != "":
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
    
    def add_transaction(self, pocket_id, card_id=None, category_id=None, status_id=None, currency_id=None, location_id=None,
                       transaction_name=None, transaction_date=None, transaction_type=None, tags="", note="", destination_pocket_id=None):
        """Add a new transaction."""
        self.db_manager.connect(write=True)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO wallet_transactions 
            (pocket_id, destination_pocket_id, card_id, category_id, status_id, currency_id, location_id, 
             transaction_name, transaction_date, transaction_type, tags, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pocket_id, destination_pocket_id, card_id, category_id, status_id, currency_id, location_id,
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
    
    def update_transaction_item(self, item_id, item_type, sku, item_name, 
                               item_description, quantity, unit, amount, width=None, height=None,
                               depth=None, weight=None, material="", color="", file_url="",
                               license_key="", expiry_date=None, digital_type="", note=""):
        """Update a transaction item."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                UPDATE wallet_transaction_items
                SET item_type = ?, sku = ?, item_name = ?, item_description = ?,
                    quantity = ?, unit = ?, amount = ?, width = ?, height = ?, 
                    depth = ?, weight = ?, material = ?, color = ?,
                    file_url = ?, license_key = ?, expiry_date = ?, digital_type = ?, note = ?
                WHERE id = ?
            """, (item_type, sku, item_name, item_description,
                  quantity, unit, amount, width, height, depth, weight, material, color,
                  file_url, license_key, expiry_date, digital_type, note, item_id))
            
            self.db_manager.connection.commit()
            
        except Exception as e:
            print(f"Error updating transaction item: {e}")
            raise
        finally:
            self.db_manager.close()
    
    def delete_transaction(self, transaction_id):
        """Delete a transaction and its items and invoice images."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("SELECT image_path FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            invoice_paths = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("DELETE FROM wallet_transactions_invoice_prove WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            cursor.execute("DELETE FROM wallet_transaction_items WHERE wallet_transaction_id = ?", 
                          (transaction_id,))
            
            cursor.execute("DELETE FROM wallet_transactions WHERE id = ?", (transaction_id,))
            
            self.db_manager.connection.commit()
            
            import os
            for image_path in invoice_paths:
                try:
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
                       l.name as location_name, ca.card_name as card_name
                FROM wallet_transactions t
                LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
                LEFT JOIN wallet_categories c ON t.category_id = c.id
                LEFT JOIN wallet_transaction_statuses s ON t.status_id = s.id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                LEFT JOIN wallet_transaction_locations l ON t.location_id = l.id
                LEFT JOIN wallet_cards ca ON t.card_id = ca.id
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
    
    def update_transaction(self, transaction_id, pocket_id, card_id=None, category_id=None, status_id=None, 
                          currency_id=None, location_id=None, transaction_name=None, transaction_date=None, 
                          transaction_type=None, tags="", note="", destination_pocket_id=None):
        """Update an existing transaction."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                UPDATE wallet_transactions 
                SET pocket_id=?, destination_pocket_id=?, card_id=?, category_id=?, status_id=?, currency_id=?, location_id=?,
                    transaction_name=?, transaction_date=?, transaction_type=?, tags=?, note=?
                WHERE id=?
            """, (pocket_id, destination_pocket_id, card_id, category_id, status_id, currency_id, location_id,
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
    
    def delete_transaction_item(self, item_id):
        """Delete a single transaction item by its ID."""
        try:
            self.db_manager.connect(write=True)
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("DELETE FROM wallet_transaction_items WHERE id = ?", 
                          (item_id,))
            
            self.db_manager.connection.commit()
            
        except Exception as e:
            print(f"Error deleting transaction item: {e}")
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
    
    def get_pocket_balance(self, pocket_id, exclude_transaction_id=None):
        """Calculate real balance for a pocket based on transactions.
        Logic:
        - Income: adds to balance
        - Expense: subtracts from balance
        - Transfer OUT (pocket_id): subtracts from balance
        - Transfer IN (destination_pocket_id): adds to balance
        
        Args:
            pocket_id: ID of the pocket
            exclude_transaction_id: Optional transaction ID to exclude from calculation (for edit mode)
        """
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            # Build WHERE clause for excluding transaction
            exclude_clause = ""
            params_income = [pocket_id]
            if exclude_transaction_id:
                exclude_clause = " AND t.id != ?"
                params_income.append(exclude_transaction_id)
            
            # Get income total
            cursor.execute(f"""
                SELECT COALESCE(SUM(ti.quantity * ti.amount), 0) as total
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                WHERE t.pocket_id = ? AND t.transaction_type = 'income'{exclude_clause}
            """, tuple(params_income))
            income_total = cursor.fetchone()[0]
            
            # Build params for expense query
            params_expense = [pocket_id]
            if exclude_transaction_id:
                params_expense.append(exclude_transaction_id)
            
            # Get expense total
            cursor.execute(f"""
                SELECT COALESCE(SUM(ti.quantity * ti.amount), 0) as total
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                WHERE t.pocket_id = ? AND t.transaction_type = 'expense'{exclude_clause}
            """, tuple(params_expense))
            expense_total = cursor.fetchone()[0]
            
            # Build params for transfer OUT query
            params_transfer_out = [pocket_id]
            if exclude_transaction_id:
                params_transfer_out.append(exclude_transaction_id)
            
            # Get transfer OUT total (money leaving this pocket)
            cursor.execute(f"""
                SELECT COALESCE(SUM(ti.quantity * ti.amount), 0) as total
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                WHERE t.pocket_id = ? AND t.transaction_type = 'transfer'{exclude_clause}
            """, tuple(params_transfer_out))
            transfer_out_total = cursor.fetchone()[0]
            
            # Build params for transfer IN query
            params_transfer_in = [pocket_id]
            if exclude_transaction_id:
                params_transfer_in.append(exclude_transaction_id)
            
            # Get transfer IN total (money coming to this pocket)
            cursor.execute(f"""
                SELECT COALESCE(SUM(ti.quantity * ti.amount), 0) as total
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                WHERE t.destination_pocket_id = ? AND t.transaction_type = 'transfer'{exclude_clause}
            """, tuple(params_transfer_in))
            transfer_in_total = cursor.fetchone()[0]
            
            # Calculate balance: income + transfer_in - expense - transfer_out
            balance = income_total + transfer_in_total - expense_total - transfer_out_total
            
            return balance
            
        except Exception as e:
            print(f"Error calculating pocket balance: {e}")
            return 0.0
        finally:
            self.db_manager.close()
    
    def get_currency_symbol(self, currency_id):
        """Get currency symbol by currency ID."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                SELECT symbol
                FROM wallet_currency
                WHERE id = ?
            """, (currency_id,))
            row = cursor.fetchone()
            return row[0] if row and row[0] else "Rp"
            
        except Exception as e:
            print(f"Error getting currency symbol: {e}")
            return "Rp"
        finally:
            self.db_manager.close()
    
    def get_pockets_with_transactions(self):
        """Get only pockets that have transactions."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                SELECT DISTINCT p.id, p.name
                FROM wallet_pockets p
                INNER JOIN wallet_transactions t ON p.id = t.pocket_id
                ORDER BY p.name
            """)
            rows = cursor.fetchall()
            pockets = [dict(row) for row in rows]
            return pockets
            
        except Exception as e:
            print(f"Error getting pockets with transactions: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_categories_with_transactions(self):
        """Get only categories that have transactions."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                SELECT DISTINCT c.id, c.name
                FROM wallet_categories c
                INNER JOIN wallet_transactions t ON c.id = t.category_id
                ORDER BY c.name
            """)
            rows = cursor.fetchall()
            categories = [dict(row) for row in rows]
            return categories
            
        except Exception as e:
            print(f"Error getting categories with transactions: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_summary_report(self, date_from, date_to, pocket_id=None, category_id=None, transaction_type=""):
        """Get summary report data."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            where_clauses = []
            params = []
            
            if date_from and date_to:
                where_clauses.append("DATE(t.transaction_date) BETWEEN ? AND ?")
                params.extend([date_from, date_to])
            
            if pocket_id:
                where_clauses.append("t.pocket_id = ?")
                params.append(pocket_id)
            
            if category_id:
                where_clauses.append("t.category_id = ?")
                params.append(category_id)
            
            if transaction_type:
                where_clauses.append("t.transaction_type = ?")
                params.append(transaction_type)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    t.transaction_type,
                    COUNT(DISTINCT t.id) as transaction_count,
                    COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                    cu.symbol as currency_symbol
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                WHERE {where_sql}
                GROUP BY t.transaction_type, cu.symbol
                ORDER BY t.transaction_type
            """, params)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting summary report: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_transactions_by_pocket(self, date_from, date_to, category_id=None, transaction_type=""):
        """Get transactions grouped by pocket."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            where_clauses = []
            params = []
            
            if date_from and date_to:
                where_clauses.append("DATE(t.transaction_date) BETWEEN ? AND ?")
                params.extend([date_from, date_to])
            
            if category_id:
                where_clauses.append("t.category_id = ?")
                params.append(category_id)
            
            if transaction_type:
                where_clauses.append("t.transaction_type = ?")
                params.append(transaction_type)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    p.name as pocket_name,
                    t.transaction_type,
                    COUNT(DISTINCT t.id) as transaction_count,
                    COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                    cu.symbol as currency_symbol
                FROM wallet_transactions t
                LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                WHERE {where_sql}
                GROUP BY p.name, t.transaction_type, cu.symbol
                ORDER BY p.name, t.transaction_type
            """, params)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting transactions by pocket: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_transactions_by_category(self, date_from, date_to, pocket_id=None, transaction_type=""):
        """Get transactions grouped by category."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            where_clauses = []
            params = []
            
            if date_from and date_to:
                where_clauses.append("DATE(t.transaction_date) BETWEEN ? AND ?")
                params.extend([date_from, date_to])
            
            if pocket_id:
                where_clauses.append("t.pocket_id = ?")
                params.append(pocket_id)
            
            if transaction_type:
                where_clauses.append("t.transaction_type = ?")
                params.append(transaction_type)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    COALESCE(c.name, 'Uncategorized') as category_name,
                    t.transaction_type,
                    COUNT(DISTINCT t.id) as transaction_count,
                    COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                    cu.symbol as currency_symbol
                FROM wallet_transactions t
                LEFT JOIN wallet_categories c ON t.category_id = c.id
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                WHERE {where_sql}
                GROUP BY c.name, t.transaction_type, cu.symbol
                ORDER BY c.name, t.transaction_type
            """, params)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting transactions by category: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_transaction_trends(self, date_from, date_to, pocket_id=None, category_id=None, transaction_type="", group_by="month"):
        """Get transaction trends over time."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            if group_by == "day":
                date_format = "%Y-%m-%d"
            elif group_by == "week":
                date_format = "%Y-W%W"
            elif group_by == "year":
                date_format = "%Y"
            else:
                date_format = "%Y-%m"
            
            where_clauses = []
            params = []
            
            if date_from and date_to:
                where_clauses.append("DATE(t.transaction_date) BETWEEN ? AND ?")
                params.extend([date_from, date_to])
            
            if pocket_id:
                where_clauses.append("t.pocket_id = ?")
                params.append(pocket_id)
            
            if category_id:
                where_clauses.append("t.category_id = ?")
                params.append(category_id)
            
            if transaction_type:
                where_clauses.append("t.transaction_type = ?")
                params.append(transaction_type)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    strftime('{date_format}', t.transaction_date) as period,
                    t.transaction_type,
                    COUNT(DISTINCT t.id) as transaction_count,
                    COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                    cu.symbol as currency_symbol
                FROM wallet_transactions t
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                WHERE {where_sql}
                GROUP BY period, t.transaction_type, cu.symbol
                ORDER BY period, t.transaction_type
            """, params)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting transaction trends: {e}")
            return []
        finally:
            self.db_manager.close()
    
    def get_detailed_transactions_report(self, date_from, date_to, pocket_id=None, category_id=None, 
                                        transaction_type="", search_text=""):
        """Get detailed transactions for reporting."""
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            where_clauses = []
            params = []
            
            if date_from and date_to:
                where_clauses.append("DATE(t.transaction_date) BETWEEN ? AND ?")
                params.extend([date_from, date_to])
            
            if pocket_id:
                where_clauses.append("t.pocket_id = ?")
                params.append(pocket_id)
            
            if category_id:
                where_clauses.append("t.category_id = ?")
                params.append(category_id)
            
            if transaction_type:
                where_clauses.append("t.transaction_type = ?")
                params.append(transaction_type)
            
            if search_text:
                where_clauses.append("t.transaction_name LIKE ?")
                params.append(f"%{search_text}%")
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    t.transaction_date,
                    t.transaction_name,
                    t.transaction_type,
                    p.name as pocket_name,
                    COALESCE(c.name, 'Uncategorized') as category_name,
                    COALESCE(ca.card_name, '-') as card_name,
                    COALESCE(l.name, '-') as location_name,
                    COALESCE(SUM(ti.quantity * ti.amount), 0) as total_amount,
                    cu.symbol as currency_symbol,
                    s.name as status_name
                FROM wallet_transactions t
                LEFT JOIN wallet_pockets p ON t.pocket_id = p.id
                LEFT JOIN wallet_categories c ON t.category_id = c.id
                LEFT JOIN wallet_cards ca ON t.card_id = ca.id
                LEFT JOIN wallet_transaction_locations l ON t.location_id = l.id
                LEFT JOIN wallet_transaction_items ti ON t.id = ti.wallet_transaction_id
                LEFT JOIN wallet_currency cu ON t.currency_id = cu.id
                LEFT JOIN wallet_transaction_statuses s ON t.status_id = s.id
                WHERE {where_sql}
                GROUP BY t.id
                ORDER BY t.transaction_date DESC
            """, params)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting detailed transactions report: {e}")
            return []
        finally:
            self.db_manager.close()
