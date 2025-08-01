import sqlite3


class DatabasePriceHelper:
    """Helper class for price and earnings management."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def assign_price(self, file_id, price, currency, note=""):
        """Assign or update price for a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
        item_price_row = cursor.fetchone()
        self.db_manager.close()
        
        if item_price_row:
            item_price_id = item_price_row["id"]
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "UPDATE item_price SET price = ?, currency = ?, note = ? WHERE id = ?",
                (price, currency, note, item_price_id)
            )
            self.db_manager.connection.commit()
            self.db_manager.close()
            self.db_manager.create_temp_file()
        else:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "INSERT INTO item_price (file_id, price, currency, note) VALUES (?, ?, ?, ?)",
                (file_id, price, currency, note)
            )
            self.db_manager.connection.commit()
            self.db_manager.close()
            self.db_manager.create_temp_file()

    def get_item_price(self, file_id):
        """Get price and currency for a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT price, currency FROM item_price WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return row["price"], row["currency"]
        return None, None

    def get_item_price_detail(self, file_id):
        """Get detailed price information for a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT price, currency, note FROM item_price WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return str(row["price"]) if row["price"] is not None else "", row["currency"] or "IDR", row["note"] or ""
        return "", "IDR", ""

    def get_item_price_id(self, file_id, cursor=None):
        """Get item price ID for a file."""
        if cursor is None:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            self.db_manager.close()
        else:
            cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
        if row:
            return row["id"]
        return None

    def get_earnings_by_file_id(self, file_id):
        """Get all earnings for a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT e.id, t.username, t.full_name, e.amount, e.note
            FROM earnings e
            JOIN item_price ip ON e.item_price_id = ip.id
            JOIN teams t ON e.team_id = t.id
            WHERE ip.file_id = ?
            ORDER BY e.id ASC
        """, (file_id,))
        result = []
        for row in cursor.fetchall():
            result.append({
                "id": row[0],
                "username": row[1],
                "full_name": row[2],
                "amount": row[3],
                "note": row[4]
            })
        self.db_manager.close()
        return result

    def assign_earning_with_percentage(self, file_id, username, note, operational_percentage):
        """Assign earning to team member with percentage calculation."""
        # Read-only check
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM teams WHERE username = ?", (username,))
        team_row = cursor.fetchone()
        if not team_row:
            self.db_manager.close()
            return False
        
        team_id = team_row[0]
        cursor.execute("SELECT id, price FROM item_price WHERE file_id = ?", (file_id,))
        price_row = cursor.fetchone()
        if not price_row:
            self.db_manager.close()
            return False
        
        item_price_id = price_row[0]
        price = price_row[1]
        cursor.execute("SELECT COUNT(*) FROM earnings WHERE item_price_id = ?", (item_price_id,))
        count = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM earnings WHERE item_price_id = ? AND team_id = ?", (item_price_id, team_id))
        exists = cursor.fetchone()
        self.db_manager.close()
        
        if exists:
            return False
        
        # Insert (write)
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO earnings (team_id, item_price_id, amount, note) VALUES (?, ?, ?, ?)",
            (team_id, item_price_id, 0, note)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.update_earnings_shares_with_percentage(file_id, operational_percentage)
        self.db_manager.create_temp_file()
        return True

    def update_earnings_shares_with_percentage(self, file_id, operational_percentage):
        """Update earnings shares based on operational percentage."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id, price FROM item_price WHERE file_id = ?", (file_id,))
        price_row = cursor.fetchone()
        if not price_row:
            self.db_manager.close()
            return
        
        item_price_id = price_row[0]
        price = price_row[1]
        cursor.execute("SELECT id FROM earnings WHERE item_price_id = ?", (item_price_id,))
        earning_rows = cursor.fetchall()
        n = len(earning_rows)
        if n == 0:
            self.db_manager.close()
            return
        
        opr_amount = float(price) * (operational_percentage / 100)
        share_total = float(price) - opr_amount
        share = share_total / n if n > 0 else 0
        
        for row in earning_rows:
            earning_id = row[0]
            cursor.execute("UPDATE earnings SET amount = ? WHERE id = ?", (share, earning_id))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def remove_earning(self, earning_id, file_id):
        """Remove earning and recalculate shares."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM earnings WHERE id = ?", (earning_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
        operational_percentage = int(self.db_manager.window_config_manager.get("operational_percentage"))
        self.update_earnings_shares_with_percentage(file_id, operational_percentage)
        self.db_manager.create_temp_file()

    def update_earning_note(self, earning_id, note):
        """Update earning note."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("UPDATE earnings SET note = ? WHERE id = ?", (note, earning_id))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()
