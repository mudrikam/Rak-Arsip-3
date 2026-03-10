class DatabaseMicrostockHelper:
    """Helper class for microstock platform management and file upload status tracking."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_platforms(self):
        """Get all microstock platforms with assigned file count."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT p.id, p.platform_name, p.platform_url, p.platform_description, p.platform_note,
                   COUNT(fms.id) as file_count
            FROM microstock_platforms p
            LEFT JOIN file_microstock_status fms ON fms.platform_id = p.id
            GROUP BY p.id
            ORDER BY p.platform_name ASC
        """)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "platform_name": row["platform_name"],
                "platform_url": row["platform_url"],
                "platform_description": row["platform_description"],
                "platform_note": row["platform_note"],
                "file_count": row["file_count"]
            })
        self.db_manager.close()
        return result

    def add_platform(self, name, url, description, note):
        """Add a new microstock platform."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO microstock_platforms (platform_name, platform_url, platform_description, platform_note)
            VALUES (?, ?, ?, ?)
        """, (name, url, description, note))
        self.db_manager.connection.commit()
        last_id = cursor.lastrowid
        self.db_manager.close()
        return last_id

    def update_platform(self, platform_id, name, url, description, note):
        """Update an existing microstock platform."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            UPDATE microstock_platforms
            SET platform_name = ?, platform_url = ?, platform_description = ?, platform_note = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, url, description, note, platform_id))
        self.db_manager.connection.commit()
        self.db_manager.close()

    def delete_platform(self, platform_id):
        """Delete a microstock platform and all related file assignments (cascade)."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("DELETE FROM file_microstock_status WHERE platform_id = ?", (platform_id,))
        cursor.execute("DELETE FROM microstock_platforms WHERE id = ?", (platform_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()

    def get_file_microstock_statuses(self, file_id):
        """Get all platform assignments and statuses for a given file."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT fms.id, fms.file_id, fms.platform_id, fms.status_id, fms.note,
                   p.platform_name, p.platform_url,
                   s.name as status_name, s.color as status_color
            FROM file_microstock_status fms
            JOIN microstock_platforms p ON fms.platform_id = p.id
            JOIN statuses s ON fms.status_id = s.id
            WHERE fms.file_id = ?
            ORDER BY p.platform_name ASC
        """, (file_id,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "file_id": row["file_id"],
                "platform_id": row["platform_id"],
                "status_id": row["status_id"],
                "note": row["note"],
                "platform_name": row["platform_name"],
                "platform_url": row["platform_url"],
                "status_name": row["status_name"],
                "status_color": row["status_color"]
            })
        self.db_manager.close()
        return result

    def upsert_file_microstock_status(self, file_id, platform_id, status_id, note=""):
        """Insert or update a file microstock status assignment."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO file_microstock_status (file_id, platform_id, status_id, note)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_id, platform_id) DO UPDATE SET
                status_id = excluded.status_id,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP
        """, (file_id, platform_id, status_id, note))
        self.db_manager.connection.commit()
        self.db_manager.close()

    def delete_file_microstock_status(self, file_id, platform_id):
        """Remove a single platform assignment from a file."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "DELETE FROM file_microstock_status WHERE file_id = ? AND platform_id = ?",
            (file_id, platform_id)
        )
        self.db_manager.connection.commit()
        self.db_manager.close()

    def get_all_statuses(self):
        """Get all statuses from the statuses table."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id, name, color FROM statuses ORDER BY id ASC")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "name": row["name"],
                "color": row["color"]
            })
        self.db_manager.close()
        return result
