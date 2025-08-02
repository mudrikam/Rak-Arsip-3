

class DatabaseUrlsHelper:
    """Helper class for URL provider database operations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_url_providers(self):
        """Retrieve all URL providers from database, with file_url count"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT id, name, description, status, email, password 
            FROM url_provider 
            ORDER BY name
        """)
        providers = cursor.fetchall()
        provider_list = []
        for provider in providers:
            provider_id = provider[0]
            cursor.execute("SELECT COUNT(*) FROM file_url WHERE provider_id = ?", (provider_id,))
            url_count = cursor.fetchone()[0]
            provider_list.append(tuple(list(provider) + [url_count]))
        self.db_manager.close()
        return provider_list

    def get_file_url_count(self, provider_id):
        """Get count of file_url entries for a provider"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_url WHERE provider_id = ?", (provider_id,))
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def add_url_provider(self, name, description, status, email, password):
        """Add new URL provider to database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            INSERT INTO url_provider (name, description, status, email, password)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, status, email, password))
        
        self.db_manager.connection.commit()
        provider_id = cursor.lastrowid
        self.db_manager.close()
        self.db_manager.create_temp_file()
        return provider_id

    def update_url_provider(self, provider_id, name, description, status, email, password):
        """Update existing URL provider in database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            UPDATE url_provider 
            SET name = ?, description = ?, status = ?, email = ?, password = ?
            WHERE id = ?
        """, (name, description, status, email, password, provider_id))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def delete_url_provider(self, provider_id):
        """Delete URL provider from database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("DELETE FROM url_provider WHERE id = ?", (provider_id,))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def get_url_provider_by_id(self, provider_id):
        """Get specific URL provider by ID"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            SELECT id, name, description, status, email, password 
            FROM url_provider 
            WHERE id = ?
        """, (provider_id,))
        
        provider = cursor.fetchone()
        self.db_manager.close()
        return provider

    def add_file_url(self, file_id, provider_id, url_value, note=""):
        """Add new file URL assignment to database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            INSERT INTO file_url (file_id, provider_id, url_value, note)
            VALUES (?, ?, ?, ?)
        """, (file_id, provider_id, url_value, note))
        
        self.db_manager.connection.commit()
        file_url_id = cursor.lastrowid
        self.db_manager.close()
        self.db_manager.create_temp_file()
        return file_url_id

    def update_file_url(self, file_url_id, provider_id, url_value, note=""):
        """Update existing file URL assignment in database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            UPDATE file_url 
            SET provider_id = ?, url_value = ?, note = ?
            WHERE id = ?
        """, (provider_id, url_value, note, file_url_id))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def get_file_urls_by_file_id(self, file_id):
        """Get all URLs assigned to a specific file"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            SELECT fu.id, fu.url_value, fu.note, up.name as provider_name
            FROM file_url fu
            JOIN url_provider up ON fu.provider_id = up.id
            WHERE fu.file_id = ?
            ORDER BY fu.created_at DESC
        """, (file_id,))
        
        urls = cursor.fetchall()
        self.db_manager.close()
        return urls

    def get_file_urls_by_batch_and_client(self, batch_id, client_id):
        """Get all file URLs for files in a specific batch and client"""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("""
            SELECT f.name, up.name as provider_name, fu.url_value, fu.note
            FROM files f
            JOIN file_client_batch fcb ON f.id = fcb.file_id
            JOIN file_url fu ON f.id = fu.file_id
            JOIN url_provider up ON fu.provider_id = up.id
            WHERE fcb.batch_number = ? AND fcb.client_id = ?
            ORDER BY f.name, up.name
        """, (batch_id, client_id))
        
        urls = cursor.fetchall()
        self.db_manager.close()
        return urls

    def delete_file_url(self, file_url_id):
        """Delete file URL assignment from database"""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        
        cursor.execute("DELETE FROM file_url WHERE id = ?", (file_url_id,))
        
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()
