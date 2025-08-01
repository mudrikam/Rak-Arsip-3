import sqlite3


class DatabaseClientsHelper:
    """Helper class for client management and client-file relationships."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_clients(self):
        """Get all clients with full details."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id, client_name, contact, links, status, note, created_at, updated_at FROM client ORDER BY client_name ASC"
        )
        clients = []
        for row in cursor.fetchall():
            clients.append({
                "id": row["id"],
                "client_name": row["client_name"],
                "contact": row["contact"],
                "links": row["links"],
                "status": row["status"],
                "note": row["note"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        self.db_manager.close()
        return clients

    def get_all_clients_simple(self):
        """Get simple client list (id and name only)."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id, client_name FROM client ORDER BY client_name ASC")
        result = [{"id": row[0], "client_name": row[1]} for row in cursor.fetchall()]
        self.db_manager.close()
        return result

    def add_client(self, client_name, contact, links, status, note):
        """Add new client."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO client (client_name, contact, links, status, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (client_name, contact, links, status, note)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def update_client(self, client_id, client_name, contact, links, status, note):
        """Update existing client."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE client SET client_name = ?, contact = ?, links = ?, status = ?, note = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (client_name, contact, links, status, note, client_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def get_files_by_client_id_paged(self, client_id, search_text=None, batch_filter=None, 
                                     sort_field="date", sort_order="desc", offset=0, limit=20):
        """Get paginated files for specific client."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["fcp.client_id = ?"]
        params = [client_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR ip.price LIKE ? OR s.name LIKE ? OR ip.note LIKE ?)"
            )
            params.extend([search_pattern] * 5)
        
        if batch_filter:
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        join_batch = "LEFT JOIN file_client_batch fcb ON fcb.file_id = f.id AND fcb.client_id = fcp.client_id"
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sort_map = {
            "File Name": "f.name",
            "Date": "f.date",
            "Price": "ip.price",
            "Status": "s.name",
            "Note": "ip.note",
            "Batch": "fcb.batch_number"
        }
        sort_sql = sort_map.get(sort_field, "f.date")
        order_sql = "DESC" if sort_order.lower() == "descending" or sort_order.lower() == "desc" else "ASC"
        
        sql = f"""
            SELECT
                f.id as file_id,
                f.name,
                f.date,
                ip.price,
                ip.currency,
                ip.note,
                s.name as status,
                fcb.batch_number as batch
            FROM file_client_price fcp
            JOIN files f ON fcp.file_id = f.id
            JOIN item_price ip ON fcp.item_price_id = ip.id
            LEFT JOIN statuses s ON f.status_id = s.id
            {join_batch}
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, f.date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(sql, params)
        files = []
        for row in cursor.fetchall():
            files.append({
                "file_id": row["file_id"],
                "name": row["name"],
                "date": row["date"],
                "price": row["price"],
                "currency": row["currency"],
                "note": row["note"],
                "status": row["status"],
                "batch": row["batch"]
            })
        self.db_manager.close()
        return files

    def count_files_by_client_id_filtered(self, client_id, search_text=None, batch_filter=None):
        """Count files for specific client with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["fcp.client_id = ?"]
        params = [client_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR ip.price LIKE ? OR s.name LIKE ? OR ip.note LIKE ?)"
            )
            params.extend([search_pattern] * 5)
        
        if batch_filter:
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        join_batch = "LEFT JOIN file_client_batch fcb ON fcb.file_id = f.id AND fcb.client_id = fcp.client_id"
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sql = f"""
            SELECT COUNT(*)
            FROM file_client_price fcp
            JOIN files f ON fcp.file_id = f.id
            JOIN item_price ip ON fcp.item_price_id = ip.id
            LEFT JOIN statuses s ON f.status_id = s.id
            {join_batch}
            {where_sql}
        """
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def sum_price_by_client_id_filtered(self, client_id, search_text=None, batch_filter=None):
        """Sum prices for specific client with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["fcp.client_id = ?"]
        params = [client_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR ip.price LIKE ? OR s.name LIKE ? OR ip.note LIKE ?)"
            )
            params.extend([search_pattern] * 5)
        
        if batch_filter:
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        join_batch = "LEFT JOIN file_client_batch fcb ON fcb.file_id = f.id AND fcb.client_id = fcp.client_id"
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sql = f"""
            SELECT SUM(CASE WHEN ip.price IS NOT NULL AND ip.price != '' THEN CAST(ip.price AS FLOAT) ELSE 0 END) as total_price,
                   MAX(ip.currency) as currency
            FROM file_client_price fcp
            JOIN files f ON fcp.file_id = f.id
            JOIN item_price ip ON fcp.item_price_id = ip.id
            LEFT JOIN statuses s ON f.status_id = s.id
            {join_batch}
            {where_sql}
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        total_price = row["total_price"] if row and row["total_price"] is not None else 0
        currency = row["currency"] if row and row["currency"] else ""
        self.db_manager.close()
        return total_price, currency

    def get_client_name_by_file_id(self, file_id):
        """Get client name associated with a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT c.client_name
            FROM file_client_price fcp
            JOIN client c ON fcp.client_id = c.id
            WHERE fcp.file_id = ?
            LIMIT 1
        """, (file_id,))
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return row[0]
        return ""

    def get_file_count_by_client_id(self, client_id):
        """Get total file count for client."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_client_price WHERE client_id = ?", (client_id,))
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def get_assigned_client_id_for_file(self, file_id):
        """Get assigned client ID for a file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        item_price_id = self.db_manager.get_item_price_id(file_id, cursor)
        assigned_client_id = None
        if item_price_id:
            cursor.execute(
                "SELECT client_id FROM file_client_price WHERE file_id = ? AND item_price_id = ?",
                (file_id, item_price_id)
            )
            row = cursor.fetchone()
            if row:
                assigned_client_id = row[0]
        self.db_manager.close()
        return assigned_client_id

    def assign_file_client_price(self, file_id, item_price_id, client_id):
        """Assign file to client with price."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM file_client_price WHERE file_id = ? AND item_price_id = ? AND client_id = ?",
            (file_id, item_price_id, client_id)
        )
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO file_client_price (file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, item_price_id, client_id)
            )
            self.db_manager.connection.commit()
            self.db_manager.create_temp_file()
        self.db_manager.close()

    def update_file_client_relation(self, file_id, item_price_id, client_id):
        """Update file-client relationship."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM file_client_price WHERE file_id = ?", (file_id,))
        self.db_manager.connection.commit()
        if client_id and item_price_id:
            cursor.execute(
                "INSERT INTO file_client_price (file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, item_price_id, client_id)
            )
            self.db_manager.connection.commit()
            self.db_manager.create_temp_file()
        self.db_manager.close()

    def update_file_client_batch_client(self, file_id, old_client_id, new_client_id):
        """Update client in file-client-batch relationship."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE file_client_batch SET client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE file_id = ? AND client_id = ?",
            (new_client_id, file_id, old_client_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    # Batch management methods
    def add_batch_number(self, batch_number, note="", client_id=None):
        """Add new batch number."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM batch_list WHERE batch_number = ?", (batch_number,))
        exists = cursor.fetchone()[0]
        self.db_manager.close()
        if not exists:
            if client_id is None:
                raise ValueError("client_id is required for batch_list")
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "INSERT INTO batch_list (batch_number, client_id, note, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (batch_number, client_id, note)
            )
            self.db_manager.connection.commit()
            self.db_manager.create_temp_file()
            self.db_manager.close()

    def assign_file_client_batch(self, file_id, client_id, batch_number, note=""):
        """Assign file to client batch."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM file_client_batch WHERE file_id = ? AND client_id = ?",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "UPDATE file_client_batch SET batch_number = ?, note = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (batch_number, note, row[0])
            )
            self.db_manager.connection.commit()
            self.db_manager.create_temp_file()
            self.db_manager.close()
        elif client_id and batch_number:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "INSERT INTO file_client_batch (file_id, client_id, batch_number, note, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, client_id, batch_number, note)
            )
            self.db_manager.connection.commit()
            self.db_manager.create_temp_file()
            self.db_manager.close()

    def get_assigned_batch_number(self, file_id, client_id):
        """Get assigned batch number for file-client."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT batch_number FROM file_client_batch WHERE file_id = ? AND client_id = ? ORDER BY id DESC LIMIT 1",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return row[0]
        return ""

    def get_batch_list_note_and_client(self, batch_number):
        """Get batch list details."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT note, client_id FROM batch_list WHERE batch_number = ?", (batch_number,))
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return (row["note"] if row["note"] else "", row["client_id"])
        return ("", None)

    def update_batch_list_note_and_client(self, batch_number, note, client_id):
        """Update batch list details."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE batch_list SET note = ?, client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (note, client_id, batch_number)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def update_batch_number_and_note_and_client(self, old_batch_number, new_batch_number, note, client_id):
        """Update batch number and details."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE batch_list SET batch_number = ?, note = ?, client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, note, client_id, old_batch_number)
        )
        cursor.execute(
            "UPDATE file_client_batch SET batch_number = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, old_batch_number)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def count_file_client_batch_by_batch_number(self, batch_number):
        """Count files in batch."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def delete_batch_and_file_client_batch(self, batch_number):
        """Delete batch and all associated file-client-batch records."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        cursor.execute("DELETE FROM batch_list WHERE batch_number = ?", (batch_number,))
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def get_batch_number_for_file_client(self, file_id, client_id):
        """Get batch number for specific file-client."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT batch_number FROM file_client_batch WHERE file_id = ? AND client_id = ? ORDER BY id DESC LIMIT 1",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return row[0]
        return ""

    def get_batch_numbers_by_client(self, client_id):
        """Get all batch numbers for a client."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT batch_number FROM batch_list WHERE client_id = ? ORDER BY batch_number ASC", (client_id,))
        batch_numbers = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return batch_numbers

    def get_status_statistics_by_client_id(self, client_id, search_text=None, batch_filter=None):
        """Get status-based statistics (count and total price) for specific client with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["fcp.client_id = ?"]
        params = [client_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR ip.price LIKE ? OR s.name LIKE ? OR ip.note LIKE ?)"
            )
            params.extend([search_pattern] * 5)
        
        if batch_filter:
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        join_batch = "LEFT JOIN file_client_batch fcb ON fcb.file_id = f.id AND fcb.client_id = fcp.client_id"
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sql = f"""
            SELECT
                s.name as status,
                COUNT(*) as count,
                SUM(CASE WHEN ip.price IS NOT NULL AND ip.price != '' THEN CAST(ip.price AS FLOAT) ELSE 0 END) as total_price
            FROM file_client_price fcp
            JOIN files f ON fcp.file_id = f.id
            JOIN item_price ip ON fcp.item_price_id = ip.id
            LEFT JOIN statuses s ON f.status_id = s.id
            {join_batch}
            {where_sql}
            GROUP BY s.name
            ORDER BY s.name ASC
        """
        cursor.execute(sql, params)
        
        status_stats = {}
        for row in cursor.fetchall():
            status = row["status"] if row["status"] else "No Status"
            count = row["count"] if row["count"] else 0
            total_price = row["total_price"] if row["total_price"] else 0
            
            status_stats[status] = {
                "count": count,
                "total_price": total_price
            }
        
        self.db_manager.close()
        return status_stats

    def get_overall_statistics(self):
        """Get overall statistics for all clients"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        # Get total files and draft count from ALL files (not just assigned ones)
        # Use LOWER() for case-insensitive comparison
        cursor.execute("""
            SELECT 
                COUNT(*) as total_files,
                SUM(CASE WHEN LOWER(s.name) = 'draft' THEN 1 ELSE 0 END) as draft_count
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
        """)
        
        row = cursor.fetchone()
        total_files = row["total_files"] if row and row["total_files"] else 0
        draft_count = row["draft_count"] if row and row["draft_count"] else 0
        
        # Get total asset value by currency from ALL item_price records
        cursor.execute("""
            SELECT 
                ip.currency,
                SUM(CASE WHEN ip.price IS NOT NULL AND ip.price != '' THEN CAST(ip.price AS REAL) ELSE 0 END) as total_value
            FROM item_price ip
            WHERE ip.currency IS NOT NULL AND ip.currency != ''
            GROUP BY ip.currency
        """)
        
        asset_values = {}
        for row in cursor.fetchall():
            currency = row["currency"].upper() if row["currency"] else "UNKNOWN"
            total_value = row["total_value"] if row["total_value"] else 0
            asset_values[currency] = total_value
        
        self.db_manager.close()
        
        return {
            "total_files": total_files,
            "draft_count": draft_count,
            "asset_values": asset_values
        }
