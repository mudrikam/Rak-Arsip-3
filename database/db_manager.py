import sqlite3
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QTimer

# Import all helper classes
from .db_helper.db_helper_connection import DatabaseConnectionHelper
from .db_helper.db_helper_categories import DatabaseCategoriesHelper
from .db_helper.db_helper_templates import DatabaseTemplatesHelper
from .db_helper.db_helper_files import DatabaseFilesHelper
from .db_helper.db_helper_clients import DatabaseClientsHelper
from .db_helper.db_helper_teams import DatabaseTeamsHelper
from .db_helper.db_helper_price import DatabasePriceHelper
from .db_helper.db_helper_backup import DatabaseBackupHelper
from .db_helper.db_helper_urls import DatabaseUrlsHelper


class DatabaseManager(QObject):

    """Optimized Database Manager using helper classes for modular organization."""
    
    data_changed = Signal()
    status_message = Signal(str, int)
    
    def __init__(self, config_manager, window_config_manager, parent_widget=None, first_launch=False):
        super().__init__()
        self.config_manager = config_manager
        self.window_config_manager = window_config_manager
        self.db_config = config_manager.get("database")
        self.tables_config = config_manager.get("tables")
        self.db_path = self.db_config["path"]
        self.connection = None
        self.session_id = str(int(time.time() * 1000))
        self.temp_dir = os.path.join(os.path.dirname(self.db_path), "temp")
        self._parent_widget = parent_widget
        self._wal_shm_last_clear = 0
        self._wal_shm_debounce_seconds = 5
        self._wal_shm_handled = False

        # Initialize helper classes
        self.connection_helper = DatabaseConnectionHelper(self)
        self.categories_helper = DatabaseCategoriesHelper(self)
        self.templates_helper = DatabaseTemplatesHelper(self)
        self.files_helper = DatabaseFilesHelper(self)
        self.clients_helper = DatabaseClientsHelper(self)
        self.teams_helper = DatabaseTeamsHelper(self)
        self.price_helper = DatabasePriceHelper(self)
        self.backup_helper = DatabaseBackupHelper(self)
        self.urls_helper = DatabaseUrlsHelper(self)

        # Initialize database
        self.connection_helper.ensure_database_exists()
        self.connection_helper.setup_file_watcher()
        if first_launch:
            self.backup_helper.auto_backup_database_daily()
        self.backup_helper.setup_auto_backup_timer()

    # Core connection methods - delegate to connection helper
    def connect(self, write=True):
        """Connect to database."""
        return self.connection_helper.connect(write)

    def close(self):
        """Close database connection."""
        return self.connection_helper.close()

    def create_temp_file(self):
        """Create temporary file to signal changes."""
        return self.connection_helper.create_temp_file()

    def get_status_id(self, status_name):
        """Get status ID by name."""
        return self.connection_helper.get_status_id(status_name)

    def get_status_id_by_name(self, status_name):
        """Get status ID by name (alias for compatibility)."""
        return self.connection_helper.get_status_id(status_name)

    def get_status_name_by_id(self, status_id):
        """Get status name by ID."""
        return self.connection_helper.get_status_name_by_id(status_id)

    # Categories methods - delegate to categories helper
    def get_all_categories(self):
        """Get all categories."""
        return self.categories_helper.get_all_categories()

    def get_subcategories_by_category(self, category_name):
        """Get subcategories by category."""
        return self.categories_helper.get_subcategories_by_category(category_name)

    def get_or_create_category(self, category_name):
        """Get or create category."""
        return self.categories_helper.get_or_create_category(category_name)

    def get_or_create_subcategory(self, category_id, subcategory_name):
        """Get or create subcategory."""
        return self.categories_helper.get_or_create_subcategory(category_id, subcategory_name)

    def delete_category(self, category_name):
        """Delete category."""
        return self.categories_helper.delete_category(category_name)

    def delete_subcategory(self, category_name, subcategory_name):
        """Delete subcategory."""
        return self.categories_helper.delete_subcategory(category_name, subcategory_name)

    # Templates methods - delegate to templates helper
    def get_all_templates(self):
        """Get all templates."""
        return self.templates_helper.get_all_templates()

    def get_template_by_id(self, template_id):
        """Get template by ID."""
        return self.templates_helper.get_template_by_id(template_id)

    def insert_template(self, name, content):
        """Insert template."""
        return self.templates_helper.insert_template(name, content)

    def delete_template(self, template_name):
        """Delete template."""
        return self.templates_helper.delete_template(template_name)

    def create_unique_path(self, base_path):
        """Create unique path."""
        return self.templates_helper.create_unique_path(base_path)

    def create_folder_structure(self, main_path, template_content=None):
        """Create folder structure."""
        return self.templates_helper.create_folder_structure(main_path, template_content)

    # Files methods - delegate to files helper
    def insert_file(self, date, name, root, path, status_id, category_id=None, subcategory_id=None, template_id=None):
        """Insert file."""
        return self.files_helper.insert_file(date, name, root, path, status_id, category_id, subcategory_id, template_id)

    def update_file_status(self, file_id, status_id):
        """Update file status."""
        return self.files_helper.update_file_status(file_id, status_id)

    def update_file_record(self, file_id, name, root, path, status_id, category_id, subcategory_id, date=None):
        """Update file record."""
        return self.files_helper.update_file_record(file_id, name, root, path, status_id, category_id, subcategory_id, date)

    def delete_file(self, file_id):
        """Delete file."""
        return self.files_helper.delete_file(file_id)

    def get_files_page(self, page=1, page_size=20, search_query=None, sort_field="date", sort_order="desc", 
                       status_value=None, client_id=None, batch_number=None, root_value=None, 
                       category_value=None, subcategory_value=None):
        """Get files page."""
        return self.files_helper.get_files_page(page, page_size, search_query, sort_field, sort_order,
                                                status_value, client_id, batch_number, root_value, 
                                                category_value, subcategory_value)

    def count_files(self, search_query=None, status_value=None, client_id=None, batch_number=None, 
                    root_value=None, category_value=None, subcategory_value=None):
        """Count files."""
        return self.files_helper.count_files(search_query, status_value, client_id, batch_number,
                                             root_value, category_value, subcategory_value)

    def get_all_roots(self):
        """Get all roots."""
        return self.files_helper.get_all_roots()

    def get_file_related_delete_info(self, file_id):
        """Get file related delete info."""
        return self.files_helper.get_file_related_delete_info(file_id)

    def get_files_by_batch_and_client(self, batch_number, client_id):
        """Get files by batch and client."""
        return self.files_helper.get_files_by_batch_and_client(batch_number, client_id)

    def update_files_status_by_batch(self, batch_number, client_id, status_id):
        """Update files status by batch."""
        return self.files_helper.update_files_status_by_batch(batch_number, client_id, status_id)

    # Clients methods - delegate to clients helper
    def get_all_clients(self):
        """Get all clients."""
        return self.clients_helper.get_all_clients()

    def get_all_clients_simple(self):
        """Get simple clients list."""
        return self.clients_helper.get_all_clients_simple()

    def add_client(self, client_name, contact, links, status, note):
        """Add client."""
        return self.clients_helper.add_client(client_name, contact, links, status, note)

    def update_client(self, client_id, client_name, contact, links, status, note):
        """Update client."""
        return self.clients_helper.update_client(client_id, client_name, contact, links, status, note)

    def get_files_by_client_id_paged(self, client_id, search_text=None, batch_filter=None, 
                                     sort_field="date", sort_order="desc", offset=0, limit=20):
        """Get files by client ID paged."""
        return self.clients_helper.get_files_by_client_id_paged(client_id, search_text, batch_filter,
                                                                sort_field, sort_order, offset, limit)

    def count_files_by_client_id_filtered(self, client_id, search_text=None, batch_filter=None):
        """Count files by client ID filtered."""
        return self.clients_helper.count_files_by_client_id_filtered(client_id, search_text, batch_filter)

    def sum_price_by_client_id_filtered(self, client_id, search_text=None, batch_filter=None):
        """Sum price by client ID filtered."""
        return self.clients_helper.sum_price_by_client_id_filtered(client_id, search_text, batch_filter)

    def get_status_statistics_by_client_id(self, client_id, search_text=None, batch_filter=None):
        """Get status statistics by client ID filtered."""
        return self.clients_helper.get_status_statistics_by_client_id(client_id, search_text, batch_filter)

    def get_overall_statistics(self):
        """Get overall statistics for all clients."""
        return self.clients_helper.get_overall_statistics()

    def get_client_name_by_file_id(self, file_id):
        """Get client name by file ID."""
        return self.clients_helper.get_client_name_by_file_id(file_id)

    def get_file_count_by_client_id(self, client_id):
        """Get file count by client ID."""
        return self.clients_helper.get_file_count_by_client_id(client_id)

    def get_assigned_client_id_for_file(self, file_id):
        """Get assigned client ID for file."""
        return self.clients_helper.get_assigned_client_id_for_file(file_id)

    def assign_file_client_price(self, file_id, item_price_id, client_id):
        """Assign file client price."""
        return self.clients_helper.assign_file_client_price(file_id, item_price_id, client_id)

    def update_file_client_relation(self, file_id, item_price_id, client_id):
        """Update file client relation."""
        return self.clients_helper.update_file_client_relation(file_id, item_price_id, client_id)

    def update_file_client_batch_client(self, file_id, old_client_id, new_client_id):
        """Update file client batch client."""
        return self.clients_helper.update_file_client_batch_client(file_id, old_client_id, new_client_id)

    # Batch methods - delegate to clients helper
    def add_batch_number(self, batch_number, note="", client_id=None):
        """Add batch number."""
        return self.clients_helper.add_batch_number(batch_number, note, client_id)

    def assign_file_client_batch(self, file_id, client_id, batch_number, note=""):
        """Assign file client batch."""
        return self.clients_helper.assign_file_client_batch(file_id, client_id, batch_number, note)

    def get_assigned_batch_number(self, file_id, client_id):
        """Get assigned batch number."""
        return self.clients_helper.get_assigned_batch_number(file_id, client_id)

    def get_batch_list_note_and_client(self, batch_number):
        """Get batch list note and client."""
        return self.clients_helper.get_batch_list_note_and_client(batch_number)

    def update_batch_list_note_and_client(self, batch_number, note, client_id):
        """Update batch list note and client."""
        return self.clients_helper.update_batch_list_note_and_client(batch_number, note, client_id)

    def update_batch_number_and_note_and_client(self, old_batch_number, new_batch_number, note, client_id):
        """Update batch number and note and client."""
        return self.clients_helper.update_batch_number_and_note_and_client(old_batch_number, new_batch_number, note, client_id)

    def count_file_client_batch_by_batch_number(self, batch_number):
        """Count file client batch by batch number."""
        return self.clients_helper.count_file_client_batch_by_batch_number(batch_number)

    def delete_batch_and_file_client_batch(self, batch_number):
        """Delete batch and file client batch."""
        return self.clients_helper.delete_batch_and_file_client_batch(batch_number)

    def get_batch_number_for_file_client(self, file_id, client_id):
        """Get batch number for file client."""
        return self.clients_helper.get_batch_number_for_file_client(file_id, client_id)

    def get_batch_numbers_by_client(self, client_id):
        """Get batch numbers by client."""
        return self.clients_helper.get_batch_numbers_by_client(client_id)

    def get_batch_creation_date(self, batch_number, client_id):
        """Get batch creation date."""
        return self.clients_helper.get_batch_created_date(batch_number, client_id)

    # Teams methods - delegate to teams helper
    def get_all_teams(self):
        """Get all teams."""
        return self.teams_helper.get_all_teams()

    def add_team(self, username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder):
        """Add team."""
        return self.teams_helper.add_team(username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder)

    def update_team(self, old_username, new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder):
        """Update team."""
        return self.teams_helper.update_team(old_username, new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder)

    def get_team_profile_data(self, username=None):
        """Get team profile data."""
        return self.teams_helper.get_team_profile_data(username)

    # Attendance methods - delegate to teams helper
    def get_latest_open_attendance(self, username, pin):
        """Get latest open attendance."""
        return self.teams_helper.get_latest_open_attendance(username, pin)

    def add_attendance_record(self, username, pin, note="", mode="checkin"):
        """Add attendance record."""
        return self.teams_helper.add_attendance_record(username, pin, note, mode)

    def get_attendance_by_username_pin(self, username, pin):
        """Get attendance by username pin."""
        return self.teams_helper.get_attendance_by_username_pin(username, pin)

    def get_attendance_records_by_username(self, username):
        """Get attendance records by username."""
        return self.teams_helper.get_attendance_records_by_username(username)

    def get_attendance_by_team_id_paged(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None, sort_field="date", sort_order="desc", offset=0, limit=20):
        """Get attendance by team ID paged."""
        return self.teams_helper.get_attendance_by_team_id_paged(team_id, search_text, day_filter, month_filter, year_filter, sort_field, sort_order, offset, limit)

    def count_attendance_by_team_id_filtered(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None):
        """Count attendance by team ID filtered."""
        return self.teams_helper.count_attendance_by_team_id_filtered(team_id, search_text, day_filter, month_filter, year_filter)

    def attendance_summary_by_team_id_filtered(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None):
        """Attendance summary by team ID filtered."""
        return self.teams_helper.attendance_summary_by_team_id_filtered(team_id, search_text, day_filter, month_filter, year_filter)

    def get_earnings_by_team_id_paged(self, team_id, search_text=None, batch_filter=None, sort_field="File Name", sort_order="desc", offset=0, limit=20):
        """Get earnings by team ID paged."""
        return self.teams_helper.get_earnings_by_team_id_paged(team_id, search_text, batch_filter, sort_field, sort_order, offset, limit)

    def count_earnings_by_team_id_filtered(self, team_id, search_text=None, batch_filter=None):
        """Count earnings by team ID filtered."""
        return self.teams_helper.count_earnings_by_team_id_filtered(team_id, search_text, batch_filter)

    def earnings_summary_by_team_id_filtered(self, team_id, search_text=None, batch_filter=None):
        """Earnings summary by team ID filtered."""
        return self.teams_helper.earnings_summary_by_team_id_filtered(team_id, search_text, batch_filter)

    # Price and earnings methods - delegate to price helper
    def assign_price(self, file_id, price, currency, note=""):
        """Assign price."""
        return self.price_helper.assign_price(file_id, price, currency, note)

    def get_item_price(self, file_id):
        """Get item price."""
        return self.price_helper.get_item_price(file_id)

    def get_item_price_detail(self, file_id):
        """Get item price detail."""
        return self.price_helper.get_item_price_detail(file_id)

    def get_item_price_id(self, file_id, cursor=None):
        """Get item price ID."""
        return self.price_helper.get_item_price_id(file_id, cursor)

    def get_earnings_by_file_id(self, file_id):
        """Get earnings by file ID."""
        return self.price_helper.get_earnings_by_file_id(file_id)

    def assign_earning_with_percentage(self, file_id, username, note, operational_percentage):
        """Assign earning with percentage."""
        return self.price_helper.assign_earning_with_percentage(file_id, username, note, operational_percentage)

    def update_earnings_shares_with_percentage(self, file_id, operational_percentage):
        """Update earnings shares with percentage."""
        return self.price_helper.update_earnings_shares_with_percentage(file_id, operational_percentage)

    def remove_earning(self, earning_id, file_id):
        """Remove earning."""
        return self.price_helper.remove_earning(earning_id, file_id)

    def update_earning_note(self, earning_id, note):
        """Update earning note."""
        return self.price_helper.update_earning_note(earning_id, note)

    # Backup methods - delegate to backup helper
    def auto_backup_database_daily(self):
        """Auto backup database daily."""
        return self.backup_helper.auto_backup_database_daily()

    def manual_backup_database(self):
        """Manual backup database."""
        return self.backup_helper.manual_backup_database()

    def import_from_csv(self, csv_path, progress_callback=None):
        """Import from CSV."""
        return self.backup_helper.import_from_csv(csv_path, progress_callback)

    def export_to_csv(self, csv_path, progress_callback=None):
        """Export to CSV."""
        return self.backup_helper.export_to_csv(csv_path, progress_callback)

    # URL Provider methods - delegate to urls helper
    def get_all_url_providers(self):
        """Get all URL providers."""
        return self.urls_helper.get_all_url_providers()

    def add_url_provider(self, name, description, status, email, password):
        """Add URL provider."""
        return self.urls_helper.add_url_provider(name, description, status, email, password)

    def update_url_provider(self, provider_id, name, description, status, email, password):
        """Update URL provider."""
        return self.urls_helper.update_url_provider(provider_id, name, description, status, email, password)

    def delete_url_provider(self, provider_id):
        """Delete URL provider."""
        return self.urls_helper.delete_url_provider(provider_id)

    def get_url_provider_by_id(self, provider_id):
        """Get URL provider by ID."""
        return self.urls_helper.get_url_provider_by_id(provider_id)

    # File URL methods - delegate to urls helper
    def add_file_url(self, file_id, provider_id, url_value, note=""):
        """Add file URL assignment."""
        return self.urls_helper.add_file_url(file_id, provider_id, url_value, note)

    def update_file_url(self, file_url_id, provider_id, url_value, note=""):
        """Update file URL assignment."""
        return self.urls_helper.update_file_url(file_url_id, provider_id, url_value, note)

    def get_file_urls_by_file_id(self, file_id):
        """Get file URLs by file ID."""
        return self.urls_helper.get_file_urls_by_file_id(file_id)
    
    def get_file_urls_by_batch_and_client(self, batch_id, client_id):
        """Get all file URLs for files in a specific batch and client"""
        return self.urls_helper.get_file_urls_by_batch_and_client(batch_id, client_id)

    def get_all_files_by_batch_and_client_with_details(self, batch_id, client_id):
        """Get all files by batch and client with complete details"""
        return self.urls_helper.get_all_files_by_batch_and_client_with_details(batch_id, client_id)

    def delete_file_url(self, file_url_id):
        """Delete file URL assignment."""
        return self.urls_helper.delete_file_url(file_url_id)

    def get_batch_created_date(self, batch_number, client_id):
        """Get batch creation date from batch_list table."""
        return self.clients_helper.get_batch_created_date(batch_number, client_id)

    def update_files_status_by_batch(self, batch_number, client_id, status_id):
        """Update status of all files in a batch."""
        return self.clients_helper.update_files_status_by_batch(batch_number, client_id, status_id)
    def rename_category(self, old_name, new_name):
        """Rename a category (delegated to categories helper)"""
        return DatabaseCategoriesHelper(self).rename_category(old_name, new_name)

    def rename_subcategory(self, category_name, old_subcategory_name, new_subcategory_name):
        """Rename a subcategory (delegated to categories helper)"""
        return DatabaseCategoriesHelper(self).rename_subcategory(category_name, old_subcategory_name, new_subcategory_name)
    
    def get_template_by_name(self, name):
        """Get template by name (delegasi ke templates_helper)"""
        return self.templates_helper.get_template_by_name(name)
    
    def update_template(self, template_id, name, content):
        """Update template by id (delegasi ke templates_helper)"""
        return self.templates_helper.update_template(template_id, name, content)