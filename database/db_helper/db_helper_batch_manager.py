class DatabaseBatchManagerHelper:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_batches(self):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT b.batch_number, b.client_id, c.client_name, b.note, b.created_at "
            "FROM batch_list b "
            "JOIN client c ON b.client_id = c.id "
            "ORDER BY b.created_at DESC"
        )
        batches = []
        for row in cursor.fetchall():
            batches.append({
                "batch_number": row["batch_number"],
                "client_id": row["client_id"],
                "client_name": row["client_name"],
                "note": row["note"],
                "created_at": row["created_at"]
            })
        self.db_manager.close()
        return batches

    def get_batch_by_number(self, batch_number):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT b.batch_number, b.client_id, c.client_name, b.note, b.created_at "
            "FROM batch_list b "
            "JOIN client c ON b.client_id = c.id "
            "WHERE b.batch_number = ?",
            (batch_number,)
        )
        row = cursor.fetchone()
        self.db_manager.close()
        if row:
            return {
                "batch_number": row["batch_number"],
                "client_id": row["client_id"],
                "client_name": row["client_name"],
                "note": row["note"],
                "created_at": row["created_at"]
            }
        return None

    def add_batch(self, batch_number, client_id, note="", created_at=None):
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        if created_at:
            cursor.execute(
                "INSERT INTO batch_list (batch_number, client_id, note, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (batch_number, client_id, note, created_at)
            )
        else:
            cursor.execute(
                "INSERT INTO batch_list (batch_number, client_id, note, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (batch_number, client_id, note)
            )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def update_batch(self, old_batch_number, new_batch_number, note, client_id, created_at=None):
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        if created_at:
            cursor.execute(
                "UPDATE batch_list SET batch_number = ?, note = ?, client_id = ?, created_at = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
                (new_batch_number, note, client_id, created_at, old_batch_number)
            )
        else:
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

    def delete_batch(self, batch_number):
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        cursor.execute("DELETE FROM batch_list WHERE batch_number = ?", (batch_number,))
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def get_batch_clients(self):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT DISTINCT client_id FROM batch_list")
        client_ids = [row["client_id"] for row in cursor.fetchall()]
        self.db_manager.close()
        return client_ids

    def get_batch_file_count(self, batch_number):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def get_batch_list(self, search_text=None, sort_field="Created At", sort_order="Ascending", offset=0, limit=20):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = []
        params = []
        if search_text:
            where_clauses.append("(b.batch_number LIKE ? OR b.note LIKE ? OR c.client_name LIKE ?)")
            params.extend([f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"])
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        sort_map = {
            "Client Name": "c.client_name",
            "Batch Number": "b.batch_number",
            "Note": "b.note",
            "File Count": "(SELECT COUNT(*) FROM file_client_batch WHERE batch_number = b.batch_number)",
            "Created At": "b.created_at"
        }
        sort_sql = sort_map.get(sort_field, "b.created_at")
        order_sql = "DESC" if sort_order.lower() == "descending" else "ASC"
        sql = f"""
            SELECT b.batch_number, b.client_id, c.client_name, b.note, b.created_at
            FROM batch_list b
            JOIN client c ON b.client_id = c.id
            {where_sql}
            ORDER BY {sort_sql} {order_sql}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(sql, params)
        batches = []
        for row in cursor.fetchall():
            batches.append({
                "batch_number": row["batch_number"],
                "client_id": row["client_id"],
                "client_name": row["client_name"],
                "note": row["note"],
                "created_at": row["created_at"]
            })
        self.db_manager.close()
        return batches

    def update_batch_with_date(self, old_batch_number, new_batch_number, note, client_id, created_at):
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE batch_list SET batch_number = ?, note = ?, client_id = ?, created_at = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, note, client_id, created_at, old_batch_number)
        )
        cursor.execute(
            "UPDATE file_client_batch SET batch_number = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, old_batch_number)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()

    def get_batch_status_breakdown(self, batch_number):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT s.name, COUNT(f.id) as count
            FROM file_client_batch fcb
            JOIN files f ON fcb.file_id = f.id  
            JOIN statuses s ON f.status_id = s.id
            WHERE fcb.batch_number = ? 
            AND s.name IN ('Draft', 'Modelling', 'Rendering', 'Photoshop', 'Need Upload', 'Pending')
            GROUP BY s.name
        """, (batch_number,))
        status_counts = {}
        for row in cursor.fetchall():
            status_counts[row["name"]] = row["count"]
        self.db_manager.close()
        return status_counts

    def get_all_batches_with_status_counts(self):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT 
                b.batch_number,
                b.client_id,
                c.client_name,
                b.note,
                b.created_at,
                COUNT(fcb.file_id) as total_files,
                SUM(CASE WHEN s.name = 'Draft' THEN 1 ELSE 0 END) as draft_count,
                SUM(CASE WHEN s.name = 'Modelling' THEN 1 ELSE 0 END) as modelling_count,
                SUM(CASE WHEN s.name = 'Rendering' THEN 1 ELSE 0 END) as rendering_count,
                SUM(CASE WHEN s.name = 'Photoshop' THEN 1 ELSE 0 END) as photoshop_count,
                SUM(CASE WHEN s.name = 'Need Upload' THEN 1 ELSE 0 END) as need_upload_count,
                SUM(CASE WHEN s.name = 'Pending' THEN 1 ELSE 0 END) as pending_count
            FROM batch_list b
            JOIN client c ON b.client_id = c.id
            LEFT JOIN file_client_batch fcb ON b.batch_number = fcb.batch_number
            LEFT JOIN files f ON fcb.file_id = f.id
            LEFT JOIN statuses s ON f.status_id = s.id
            GROUP BY b.batch_number, b.client_id, c.client_name, b.note, b.created_at
            ORDER BY b.created_at DESC
        """)
        batches = []
        for row in cursor.fetchall():
            batches.append({
                "batch_number": row["batch_number"],
                "client_id": row["client_id"],
                "client_name": row["client_name"],
                "note": row["note"],
                "created_at": row["created_at"],
                "total_files": row["total_files"] or 0,
                "draft_count": row["draft_count"] or 0,
                "modelling_count": row["modelling_count"] or 0,
                "rendering_count": row["rendering_count"] or 0,
                "photoshop_count": row["photoshop_count"] or 0,
                "need_upload_count": row["need_upload_count"] or 0,
                "pending_count": row["pending_count"] or 0
            })
        self.db_manager.close()
        return batches
