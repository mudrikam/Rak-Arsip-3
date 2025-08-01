import sqlite3


class DatabaseFilesHelper:
    """Helper class for file management operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def insert_file(self, date, name, root, path, status_id, category_id=None, subcategory_id=None, template_id=None):
        """Insert new file record."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, name, root, path, status_id, category_id, subcategory_id, template_id))
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        last_id = cursor.lastrowid
        self.db_manager.close()
        return last_id

    def update_file_status(self, file_id, status_id):
        """Update file status."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE files SET status_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status_id, file_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def update_file_record(self, file_id, name, root, path, status_id, category_id, subcategory_id):
        """Update complete file record."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            UPDATE files SET name = ?, root = ?, path = ?, status_id = ?, category_id = ?, subcategory_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, root, path, status_id, category_id, subcategory_id, file_id))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def delete_file(self, file_id):
        """Delete file and all related records."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        # Find all item_price_id related to this file_id
        cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
        item_price_rows = cursor.fetchall()
        item_price_ids = [row["id"] for row in item_price_rows] if item_price_rows else []
        
        # Delete earnings related to item_price_id
        if item_price_ids:
            cursor.executemany("DELETE FROM earnings WHERE item_price_id = ?", [(ipid,) for ipid in item_price_ids])
        
        # Delete from item_price
        cursor.execute("DELETE FROM item_price WHERE file_id = ?", (file_id,))
        
        # Delete from file_client_price
        cursor.execute("DELETE FROM file_client_price WHERE file_id = ?", (file_id,))
        
        # Delete from file_client_batch
        cursor.execute("DELETE FROM file_client_batch WHERE file_id = ?", (file_id,))
        
        # Finally, delete from files
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def get_files_page(self, page=1, page_size=20, search_query=None, sort_field="date", sort_order="desc", 
                       status_value=None, client_id=None, batch_number=None, root_value=None, 
                       category_value=None, subcategory_value=None):
        """Get paginated files with filtering and sorting."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        offset = (page - 1) * page_size
        params = []
        where_clauses = []
        join_clauses = []
        
        if search_query:
            search_pattern = f"%{search_query}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.path LIKE ? OR c.name LIKE ? OR sc.name LIKE ?)"
            )
            params.extend([search_pattern] * 4)
        
        if status_value:
            where_clauses.append("s.name = ?")
            params.append(status_value)
        
        if batch_number and client_id:
            join_clauses.append("JOIN file_client_batch fcb ON fcb.file_id = f.id")
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_number)
            where_clauses.append("fcb.client_id = ?")
            params.append(client_id)
        
        if root_value:
            where_clauses.append("f.root = ?")
            params.append(root_value)
        
        if category_value:
            where_clauses.append("c.name = ?")
            params.append(category_value)
        
        if subcategory_value:
            where_clauses.append("sc.name = ?")
            params.append(subcategory_value)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        join_sql = ""
        if join_clauses:
            join_sql = " ".join(join_clauses)
        
        sort_map = {
            "date": "parsed_date",
            "name": "f.name",
            "root": "f.root",
            "path": "f.path",
            "status": "s.name",
            "category": "c.name",
            "subcategory": "sc.name",
            "batch_number": "fcb.batch_number"
        }
        sort_sql = sort_map.get(sort_field, "parsed_date")
        order_sql = "DESC" if sort_order == "desc" else "ASC"
        
        sql = f"""
            SELECT
                f.id, f.date, f.name, f.root, f.path, f.status_id, f.category_id, f.subcategory_id, f.template_id,
                s.name as status, s.color as status_color, 
                c.name as category, sc.name as subcategory,
                t.name as template,
                CASE 
                    WHEN f.date LIKE '%_%_%' THEN 
                        date(
                            substr(f.date, -4) || '-' ||
                            (
                                CASE
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('januari','january') THEN '01'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('februari','february') THEN '02'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('maret','march') THEN '03'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'april' THEN '04'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'mei' THEN '05'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'may' THEN '05'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'juni' THEN '06'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'july' THEN '07'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'juli' THEN '07'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'agustus' THEN '08'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'august' THEN '08'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'september' THEN '09'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'oktober' THEN '10'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'october' THEN '10'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'november' THEN '11'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'desember' THEN '12'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'december' THEN '12'
                                    ELSE '01'
                                END
                            ) || '-' ||
                            printf('%02d', cast(substr(f.date, 1, instr(f.date, '_') - 1) as integer))
                        )
                    ELSE f.date
                END AS parsed_date
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            LEFT JOIN templates t ON f.template_id = t.id
            {join_sql}
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, f.id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "date": row["date"],
                "name": row["name"],
                "root": row["root"],
                "path": row["path"],
                "status_id": row["status_id"],
                "category_id": row["category_id"],
                "subcategory_id": row["subcategory_id"],
                "template_id": row["template_id"],
                "status": row["status"],
                "status_color": row["status_color"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "template": row["template"]
            })
        self.db_manager.close()
        return result

    def count_files(self, search_query=None, status_value=None, client_id=None, batch_number=None, 
                    root_value=None, category_value=None, subcategory_value=None):
        """Count files with filtering."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        params = []
        where_clauses = []
        join_clauses = []
        
        if search_query:
            search_pattern = f"%{search_query}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.path LIKE ? OR c.name LIKE ? OR sc.name LIKE ?)"
            )
            params.extend([search_pattern] * 4)
        
        if status_value:
            where_clauses.append("s.name = ?")
            params.append(status_value)
        
        if batch_number and client_id:
            join_clauses.append("JOIN file_client_batch fcb ON fcb.file_id = f.id")
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_number)
            where_clauses.append("fcb.client_id = ?")
            params.append(client_id)
        
        if root_value:
            where_clauses.append("f.root = ?")
            params.append(root_value)
        
        if category_value:
            where_clauses.append("c.name = ?")
            params.append(category_value)
        
        if subcategory_value:
            where_clauses.append("sc.name = ?")
            params.append(subcategory_value)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        join_sql = ""
        if join_clauses:
            join_sql = " ".join(join_clauses)
        
        sql = f"""
            SELECT COUNT(*) FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            {join_sql}
            {where_sql}
        """
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def get_all_roots(self):
        """Get all unique root values."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT DISTINCT root FROM files ORDER BY root ASC")
        roots = [row[0] for row in cursor.fetchall() if row[0]]
        self.db_manager.close()
        return roots

    def get_file_related_delete_info(self, file_id):
        """Get all related information for file deletion."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("SELECT id, price, currency, note FROM item_price WHERE file_id = ?", (file_id,))
        item_price_rows = cursor.fetchall()
        item_price_info = []
        item_price_ids = []
        for ip in item_price_rows:
            item_price_info.append({
                "id": ip["id"],
                "price": ip["price"],
                "currency": ip["currency"],
                "note": ip["note"]
            })
            item_price_ids.append(ip["id"])
        
        earnings_info = []
        for ipid in item_price_ids:
            cursor.execute("SELECT id, team_id, amount, note FROM earnings WHERE item_price_id = ?", (ipid,))
            for e in cursor.fetchall():
                earnings_info.append({
                    "id": e["id"],
                    "team_id": e["team_id"],
                    "amount": e["amount"],
                    "note": e["note"]
                })
        
        cursor.execute("SELECT id, client_id FROM file_client_price WHERE file_id = ?", (file_id,))
        file_client_price_info = []
        for fcp in cursor.fetchall():
            file_client_price_info.append({
                "id": fcp["id"],
                "client_id": fcp["client_id"]
            })
        
        cursor.execute("SELECT id, client_id, batch_number FROM file_client_batch WHERE file_id = ?", (file_id,))
        file_client_batch_info = []
        for fcb in cursor.fetchall():
            file_client_batch_info.append({
                "id": fcb["id"],
                "client_id": fcb["client_id"],
                "batch_number": fcb["batch_number"]
            })
        
        self.db_manager.close()
        return {
            "item_price": item_price_info,
            "earnings": earnings_info,
            "file_client_price": file_client_price_info,
            "file_client_batch": file_client_batch_info
        }
