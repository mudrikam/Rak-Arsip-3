from pathlib import Path
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager

class ClientDataDatabaseHelper:
    """Helper class for database operations in Client Data Dialog"""
    
    def __init__(self, parent_dialog):
        self.parent = parent_dialog
        self._db_manager = None
        self._config_manager = None
    
    def get_db_manager(self):
        """Get database manager instance"""
        if self._db_manager is None:
            basedir = Path(__file__).resolve().parents[3]
            db_config_path = basedir / "configs" / "db_config.json"
            self._config_manager = ConfigManager(str(db_config_path))
            self._db_manager = DatabaseManager(self._config_manager, self._config_manager)
        return self._db_manager
    
    def get_config_manager(self, config_type="db"):
        """Get config manager instance"""
        basedir = Path(__file__).resolve().parents[3]
        if config_type == "window":
            config_path = basedir / "configs" / "window_config.json"
        else:
            config_path = basedir / "configs" / "db_config.json"
        return ConfigManager(str(config_path))
    
    def get_all_clients(self):
        """Load all clients with file count"""
        db_manager = self.get_db_manager()
        clients = db_manager.get_all_clients()
        for client in clients:
            file_count = db_manager.get_file_count_by_client_id(client["id"])
            client["_file_count"] = file_count
        return clients
    
    def get_client_by_id(self, client_id):
        """Get client by ID"""
        db_manager = self.get_db_manager()
        db_manager.connect(write=False)
        cursor = db_manager.connection.cursor()
        cursor.execute("SELECT id, client_name, contact, links, status, note FROM client WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        db_manager.close()
        if row:
            return {
                "id": row[0],
                "client_name": row[1],
                "contact": row[2],
                "links": row[3],
                "status": row[4],
                "note": row[5]
            }
        return None
    
    def add_client(self, client_name, contact, links, status, note):
        """Add new client to database"""
        db_manager = self.get_db_manager()
        return db_manager.add_client(
            client_name=client_name,
            contact=contact,
            links=links,
            status=status,
            note=note
        )
    
    def update_client(self, client_id, client_name, contact, links, status, note):
        """Update existing client in database"""
        db_manager = self.get_db_manager()
        return db_manager.update_client(
            client_id=client_id,
            client_name=client_name,
            contact=contact,
            links=links,
            status=status,
            note=note
        )
    
    def get_files_by_client_id_paged(self, client_id, search_text, batch_filter, sort_field, sort_order, offset, limit):
        """Get paginated files for client"""
        db_manager = self.get_db_manager()
        return db_manager.get_files_by_client_id_paged(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter,
            sort_field=sort_field,
            sort_order=sort_order,
            offset=offset,
            limit=limit
        )
    
    def count_files_by_client_id_filtered(self, client_id, search_text, batch_filter):
        """Count filtered files for client"""
        db_manager = self.get_db_manager()
        return db_manager.count_files_by_client_id_filtered(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter
        )
    
    def sum_price_by_client_id_filtered(self, client_id, search_text, batch_filter):
        """Sum prices for filtered files"""
        db_manager = self.get_db_manager()
        return db_manager.sum_price_by_client_id_filtered(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter
        )
    
    def get_batch_numbers_by_client(self, client_id):
        """Get batch numbers for client"""
        db_manager = self.get_db_manager()
        return db_manager.get_batch_numbers_by_client(client_id)
    
    def get_batch_list_note_and_client(self, batch_number):
        """Get batch note and client"""
        db_manager = self.get_db_manager()
        return db_manager.get_batch_list_note_and_client(batch_number)
    
    def count_file_client_batch_by_batch_number(self, batch_number):
        """Count files in batch"""
        db_manager = self.get_db_manager()
        return db_manager.count_file_client_batch_by_batch_number(batch_number)
    
    def add_batch_number(self, batch_number, note, client_id):
        """Add new batch"""
        db_manager = self.get_db_manager()
        return db_manager.add_batch_number(batch_number, note, client_id)
    
    def update_batch_number_and_note_and_client(self, old_batch, new_batch, note, client_id):
        """Update batch number and note"""
        db_manager = self.get_db_manager()
        return db_manager.update_batch_number_and_note_and_client(old_batch, new_batch, note, client_id)
    
    def update_batch_list_note_and_client(self, batch_number, note, client_id):
        """Update batch note only"""
        db_manager = self.get_db_manager()
        return db_manager.update_batch_list_note_and_client(batch_number, note, client_id)
    
    def delete_batch_and_file_client_batch(self, batch_number):
        """Delete batch and related records"""
        db_manager = self.get_db_manager()
        return db_manager.delete_batch_and_file_client_batch(batch_number)
    
    def get_file_path_by_id(self, file_id):
        """Get file path by ID for context menu operations"""
        db_manager = self.get_db_manager()
        db_manager.connect(write=False)
        cursor = db_manager.connection.cursor()
        cursor.execute("SELECT path FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        db_manager.close()
        return row[0] if row and row[0] else ""

    def get_status_statistics_by_client_id(self, client_id, search_text, batch_filter):
        """Get status statistics for client"""
        db_manager = self.get_db_manager()
        return db_manager.get_status_statistics_by_client_id(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter
        )

    def get_overall_statistics(self):
        """Get overall statistics for all clients"""
        db_manager = self.get_db_manager()
        return db_manager.get_overall_statistics()

    def get_file_urls_by_batch_and_client(self, batch_id, client_id):
        """Get file URLs for files in specific batch and client"""
        db_manager = self.get_db_manager()
        return db_manager.get_file_urls_by_batch_and_client(batch_id, client_id)

    def get_all_files_by_batch_and_client_with_details(self, batch_id, client_id):
        """Get all files by batch and client with complete details"""
        db_manager = self.get_db_manager()
        return db_manager.get_all_files_by_batch_and_client_with_details(batch_id, client_id)

    def get_batch_created_date(self, batch_number, client_id):
        """Get batch creation date from batch_list table."""
        db_manager = self.get_db_manager()
        result = db_manager.get_batch_created_date(batch_number, client_id)
        return result

    def get_status_id_by_name(self, status_name):
        """Get status ID by status name."""
        db_manager = self.get_db_manager()
        return db_manager.get_status_id(status_name)

    def get_status_id(self, status_name):
        """Get status ID by status name (alias for compatibility)."""
        db_manager = self.get_db_manager()
        return db_manager.get_status_id(status_name)

    def update_files_status_by_batch(self, batch_number, client_id, status_id):
        """Update status of all files in a batch."""
        db_manager = self.get_db_manager()
        return db_manager.update_files_status_by_batch(batch_number, client_id, status_id)

    def get_files_by_batch_and_client(self, batch_number, client_id):
        """Get all files in a specific batch and client with details."""
        db_manager = self.get_db_manager()
        return db_manager.get_files_by_batch_and_client(batch_number, client_id)

    def get_status_name_by_id(self, status_id):
        """Get status name by status ID."""
        db_manager = self.get_db_manager()
        return db_manager.connection_helper.get_status_name_by_id(status_id)
