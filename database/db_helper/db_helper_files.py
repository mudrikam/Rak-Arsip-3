

class DatabaseFilesHelper:
    """Helper class for file management operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def initialize_statuses(self):
        """Initialize default status values."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM statuses")
        count = cursor.fetchone()[0]
        if count > 0:
            self.db_manager.close()
            return
        
        status_config = self.db_manager.window_config_manager.get("status_options")
        status_list = []
        for status_name, config in status_config.items():
            cursor.execute(
                "INSERT INTO statuses (name, color, font_weight) VALUES (%s, %s, %s)",
                (status_name, config["color"], config["font_weight"])
            )
            status_list.append(f"{status_name} ({config['color']})")
        self.db_manager.connection.commit()
        print(f"[DB] Initialized {len(status_config)} default statuses: {', '.join(status_list)}")
        self.db_manager.close()

    def get_status_id(self, status_name):
        """Get status ID by name."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM statuses WHERE name = %s", (status_name,))
        result = cursor.fetchone()
        self.db_manager.close()
        if result is not None:
            return result[0]
        return None

    def get_status_name_by_id(self, status_id):
        """Get status name by ID."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT name FROM statuses WHERE id = %s", (status_id,))
        result = cursor.fetchone()
        self.db_manager.close()
        if result is not None:
            return result[0]
        return None

    def insert_file(self, date, name, root, path, status_id, category_id=None, subcategory_id=None, template_id=None):
        """Insert new file record."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (date, name, root, path, status_id, category_id, subcategory_id, template_id))
        last_id = cursor.fetchone()[0]
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        self.db_manager.close()
        return last_id

    def update_file_status(self, file_id, status_id):
        """Update file status."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "UPDATE files SET status_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (status_id, file_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def update_file_record(self, file_id, name, root, path, status_id, category_id, subcategory_id, date=None):
        """Update complete file record."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            UPDATE files SET name = %s, root = %s, path = %s, status_id = %s, category_id = %s, subcategory_id = %s, date = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (name, root, path, status_id, category_id, subcategory_id, date, file_id))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def delete_file(self, file_id):
        """Delete file and all related records."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        # Find all item_price_id related to this file_id
        cursor.execute("SELECT id FROM item_price WHERE file_id = %s", (file_id,))
        item_price_rows = cursor.fetchall()
        item_price_ids = [row["id"] for row in item_price_rows] if item_price_rows else []
        
        # Delete earnings related to item_price_id
        if item_price_ids:
            cursor.executemany("DELETE FROM earnings WHERE item_price_id = %s", [(ipid,) for ipid in item_price_ids])
        
        # Delete from item_price
        cursor.execute("DELETE FROM item_price WHERE file_id = %s", (file_id,))
        
        # Delete from file_client_price
        cursor.execute("DELETE FROM file_client_price WHERE file_id = %s", (file_id,))
        
        # Delete from file_client_batch
        cursor.execute("DELETE FROM file_client_batch WHERE file_id = %s", (file_id,))
        
        # Delete from file_url
        cursor.execute("DELETE FROM file_url WHERE file_id = %s", (file_id,))
        
        # Delete from file_microstock_status
        cursor.execute("DELETE FROM file_microstock_status WHERE file_id = %s", (file_id,))
        
        # Finally, delete from files
        cursor.execute("DELETE FROM files WHERE id = %s", (file_id,))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def get_files_page(self, page=1, page_size=20, search_query=None, sort_field="date", sort_order="desc", 
                       status_value=None, client_id=None, batch_number=None, root_value=None, 
                       category_value=None, subcategory_value=None, microstock_platform_id=None):
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
                "(f.name ILIKE %s OR f.path ILIKE %s OR c.name ILIKE %s OR sc.name ILIKE %s)"
            )
            params.extend([search_pattern] * 4)
        
        if status_value:
            where_clauses.append("s.name = %s")
            params.append(status_value)
        
        if batch_number and client_id:
            join_clauses.append("JOIN file_client_batch fcb ON fcb.file_id = f.id")
            where_clauses.append("fcb.batch_number = %s")
            params.append(batch_number)
            where_clauses.append("fcb.client_id = %s")
            params.append(client_id)
        
        if root_value:
            where_clauses.append("f.root = %s")
            params.append(root_value)
        
        if category_value:
            where_clauses.append("c.name = %s")
            params.append(category_value)
        
        if subcategory_value:
            where_clauses.append("sc.name = %s")
            params.append(subcategory_value)

        if microstock_platform_id:
            join_clauses.append("JOIN file_microstock_status fms ON fms.file_id = f.id")
            where_clauses.append("fms.platform_id = %s")
            params.append(microstock_platform_id)

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
            "batch_number": "fcb.batch_number",
            "microstock": "fms_sort.status_name",
        }
        sort_sql = sort_map.get(sort_field, "parsed_date")
        order_sql = "DESC" if sort_order == "desc" else "ASC"

        # For microstock sort, add a left join to get status name for the chosen platform
        microstock_sort_join = ""
        if sort_field == "microstock" and microstock_platform_id:
            microstock_sort_join = (
                f"LEFT JOIN ("
                f"SELECT fms2.file_id, s2.name AS status_name "
                f"FROM file_microstock_status fms2 "
                f"LEFT JOIN statuses s2 ON s2.id = fms2.status_id "
                f"WHERE fms2.platform_id = {int(microstock_platform_id)}"
                f") fms_sort ON fms_sort.file_id = f.id"
            )
        
        sql = f"""
            SELECT
                f.id, f.date, f.name, f.root, f.path, f.status_id, f.category_id, f.subcategory_id, f.template_id,
                s.name as status, s.color as status_color, 
                c.name as category, sc.name as subcategory,
                t.name as template,
                CASE 
                    WHEN position(chr(92) in f.date) > 0 THEN 
                        CASE
                            WHEN length(split_part(f.date, chr(92), 1)) = 4 THEN
                                (
                                    split_part(f.date, chr(92), 1) || '-' ||
                                    (
                                        CASE lower(split_part(f.date, chr(92), 2))
                                            WHEN 'januari' THEN '01' WHEN 'january' THEN '01'
                                            WHEN 'februari' THEN '02' WHEN 'february' THEN '02'
                                            WHEN 'maret' THEN '03' WHEN 'march' THEN '03'
                                            WHEN 'april' THEN '04'
                                            WHEN 'mei' THEN '05' WHEN 'may' THEN '05'
                                            WHEN 'juni' THEN '06' WHEN 'june' THEN '06'
                                            WHEN 'juli' THEN '07' WHEN 'july' THEN '07'
                                            WHEN 'agustus' THEN '08' WHEN 'august' THEN '08'
                                            WHEN 'september' THEN '09'
                                            WHEN 'oktober' THEN '10' WHEN 'october' THEN '10'
                                            WHEN 'november' THEN '11'
                                            WHEN 'desember' THEN '12' WHEN 'december' THEN '12'
                                            ELSE '01'
                                        END
                                    ) || '-' ||
                                    lpad(split_part(f.date, chr(92), 3), 2, '0')
                                )
                            ELSE
                                (
                                    split_part(f.date, chr(92), 3) || '-' ||
                                    (
                                        CASE lower(split_part(f.date, chr(92), 2))
                                            WHEN 'januari' THEN '01' WHEN 'january' THEN '01'
                                            WHEN 'februari' THEN '02' WHEN 'february' THEN '02'
                                            WHEN 'maret' THEN '03' WHEN 'march' THEN '03'
                                            WHEN 'april' THEN '04'
                                            WHEN 'mei' THEN '05' WHEN 'may' THEN '05'
                                            WHEN 'juni' THEN '06' WHEN 'june' THEN '06'
                                            WHEN 'juli' THEN '07' WHEN 'july' THEN '07'
                                            WHEN 'agustus' THEN '08' WHEN 'august' THEN '08'
                                            WHEN 'september' THEN '09'
                                            WHEN 'oktober' THEN '10' WHEN 'october' THEN '10'
                                            WHEN 'november' THEN '11'
                                            WHEN 'desember' THEN '12' WHEN 'december' THEN '12'
                                            ELSE '01'
                                        END
                                    ) || '-' ||
                                    lpad(split_part(f.date, chr(92), 1), 2, '0')
                                )
                        END
                    ELSE f.date
                END AS parsed_date
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            LEFT JOIN templates t ON f.template_id = t.id
            {join_sql}
            {microstock_sort_join}
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, f.id DESC
            LIMIT %s OFFSET %s
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
                    root_value=None, category_value=None, subcategory_value=None, microstock_platform_id=None):
        """Count files with filtering."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        params = []
        where_clauses = []
        join_clauses = []
        
        if search_query:
            search_pattern = f"%{search_query}%"
            where_clauses.append(
                "(f.name ILIKE %s OR f.path ILIKE %s OR c.name ILIKE %s OR sc.name ILIKE %s)"
            )
            params.extend([search_pattern] * 4)
        
        if status_value:
            where_clauses.append("s.name = %s")
            params.append(status_value)
        
        if batch_number and client_id:
            join_clauses.append("JOIN file_client_batch fcb ON fcb.file_id = f.id")
            where_clauses.append("fcb.batch_number = %s")
            params.append(batch_number)
            where_clauses.append("fcb.client_id = %s")
            params.append(client_id)
        
        if root_value:
            where_clauses.append("f.root = %s")
            params.append(root_value)
        
        if category_value:
            where_clauses.append("c.name = %s")
            params.append(category_value)
        
        if subcategory_value:
            where_clauses.append("sc.name = %s")
            params.append(subcategory_value)

        if microstock_platform_id:
            join_clauses.append("JOIN file_microstock_status fms ON fms.file_id = f.id")
            where_clauses.append("fms.platform_id = %s")
            params.append(microstock_platform_id)

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

    def get_files_by_batch_and_client(self, batch_number, client_id):
        """Get all files in a specific batch and client with details."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            SELECT 
                f.id, f.name, f.date, f.root, f.path, f.status_id, 
                s.name as status_name,
                c.name as category_name, 
                sc.name as subcategory_name
            FROM files f
            JOIN file_client_batch fcb ON f.id = fcb.file_id
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            WHERE fcb.batch_number = %s AND fcb.client_id = %s
            ORDER BY f.name
        """, (batch_number, client_id))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                "id": row["id"],
                "name": row["name"],
                "date": row["date"],
                "root": row["root"],
                "path": row["path"],
                "status_id": row["status_id"],
                "status_name": row["status_name"],
                "category_name": row["category_name"],
                "subcategory_name": row["subcategory_name"]
            })
        
        self.db_manager.close()
        return files

    def update_files_status_by_batch(self, batch_number, client_id, status_id):
        """Update status for all files in a specific batch and client."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        # Get all file IDs in the batch first
        cursor.execute("""
            SELECT f.id 
            FROM files f
            JOIN file_client_batch fcb ON f.id = fcb.file_id
            WHERE fcb.batch_number = %s AND fcb.client_id = %s
        """, (batch_number, client_id))
        
        file_ids = [row["id"] for row in cursor.fetchall()]
        
        if file_ids:
            # Update status for all files in the batch
            placeholders = ",".join(["%s"] * len(file_ids))
            cursor.execute(f"""
                UPDATE files 
                SET status_id = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id IN ({placeholders})
            """, [status_id] + file_ids)
            
            self.db_manager.connection.commit()
        
        self.db_manager.close()
        self.db_manager.create_temp_file()
        return len(file_ids)

    def get_file_related_delete_info(self, file_id):
        """Get all related information for file deletion."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("SELECT id, price, currency, note FROM item_price WHERE file_id = %s", (file_id,))
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
            cursor.execute("SELECT id, team_id, amount, note FROM earnings WHERE item_price_id = %s", (ipid,))
            for e in cursor.fetchall():
                earnings_info.append({
                    "id": e["id"],
                    "team_id": e["team_id"],
                    "amount": e["amount"],
                    "note": e["note"]
                })
        
        cursor.execute("SELECT id, client_id FROM file_client_price WHERE file_id = %s", (file_id,))
        file_client_price_info = []
        for fcp in cursor.fetchall():
            file_client_price_info.append({
                "id": fcp["id"],
                "client_id": fcp["client_id"]
            })
        
        cursor.execute("SELECT id, client_id, batch_number FROM file_client_batch WHERE file_id = %s", (file_id,))
        file_client_batch_info = []
        for fcb in cursor.fetchall():
            file_client_batch_info.append({
                "id": fcb["id"],
                "client_id": fcb["client_id"],
                "batch_number": fcb["batch_number"]
            })
        
        # Get file URL assignments
        cursor.execute("""
            SELECT fu.id, fu.provider_id, fu.url_value, fu.note, up.name as provider_name 
            FROM file_url fu 
            LEFT JOIN url_provider up ON fu.provider_id = up.id 
            WHERE fu.file_id = %s
        """, (file_id,))
        file_url_info = []
        for fu in cursor.fetchall():
            file_url_info.append({
                "id": fu["id"],
                "provider_id": fu["provider_id"],
                "provider_name": fu["provider_name"] or "Unknown",
                "url_value": fu["url_value"],
                "note": fu["note"]
            })
        
        # Get microstock assignments
        cursor.execute("""
            SELECT fms.id, fms.platform_id, fms.note,
                   p.platform_name, s.name as status_name
            FROM file_microstock_status fms
            JOIN microstock_platforms p ON fms.platform_id = p.id
            JOIN statuses s ON fms.status_id = s.id
            WHERE fms.file_id = %s
        """, (file_id,))
        file_microstock_info = []
        for fm in cursor.fetchall():
            file_microstock_info.append({
                "id": fm["id"],
                "platform_id": fm["platform_id"],
                "platform_name": fm["platform_name"],
                "status_name": fm["status_name"],
                "note": fm["note"]
            })
        
        self.db_manager.close()
        return {
            "item_price": item_price_info,
            "earnings": earnings_info,
            "file_client_price": file_client_price_info,
            "file_client_batch": file_client_batch_info,
            "file_url": file_url_info,
            "file_microstock": file_microstock_info
        }
