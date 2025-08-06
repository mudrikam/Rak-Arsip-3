from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QComboBox, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
import qtawesome as qta
from pathlib import Path
import json


class ClientDataInvoiceHelper:
    """Helper class for Invoice management and Google Drive sync"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # Google Drive service
        self.drive_service = None
        self.sheets_service = None
        self.credentials = None
        
        # Folder IDs
        self.rak_arsip_folder_id = None
        self.invoice_folder_id = None
    
    def init_google_drive_connection(self):
        """Initialize Google Drive API connection"""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Path ke credentials
            creds_path = Path(__file__).parent.parent.parent.parent / "configs" / "credentials_config.json"
            if not creds_path.exists():
                QMessageBox.critical(self.parent, "Configuration Not Found", f"Credentials file not found in application preferences:\n{creds_path}")
                return False
            
            scopes = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
            self.credentials = service_account.Credentials.from_service_account_file(str(creds_path), scopes=scopes)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            print("Google Drive API connection initialized successfully")
            return True
            
        except ImportError:
            print("Google API libraries not installed")
            return False
        except Exception as e:
            print(f"Error initializing Google Drive connection: {e}")
            return False
    
    def ensure_folders_exist(self):
        """Ensure Rak_Arsip_Database and INVOICE folders exist"""
        if not self.drive_service:
            if not self.init_google_drive_connection():
                return False
        
        try:
            # Cari folder Rak_Arsip_Database
            print("Checking for Rak_Arsip_Database folder...")
            results = self.drive_service.files().list(
                q="name = 'Rak_Arsip_Database' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            folders = results.get('files', [])
            
            if folders:
                self.rak_arsip_folder_id = folders[0]['id']
                print(f"Found Rak_Arsip_Database folder with ID: {self.rak_arsip_folder_id}")
            else:
                # Buat folder Rak_Arsip_Database di root
                print("Creating Rak_Arsip_Database folder...")
                file_metadata = {
                    'name': 'Rak_Arsip_Database',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
                self.rak_arsip_folder_id = folder.get('id')
                print(f"Created Rak_Arsip_Database folder with ID: {self.rak_arsip_folder_id}")
            
            # Cari folder INVOICE di dalam Rak_Arsip_Database
            print("Checking for INVOICE folder...")
            results = self.drive_service.files().list(
                q=f"name = 'INVOICE' and mimeType = 'application/vnd.google-apps.folder' and '{self.rak_arsip_folder_id}' in parents and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            folders = results.get('files', [])
            
            if folders:
                self.invoice_folder_id = folders[0]['id']
                print(f"Found INVOICE folder with ID: {self.invoice_folder_id}")
            else:
                # Buat folder INVOICE di dalam Rak_Arsip_Database
                print("Creating INVOICE folder...")
                file_metadata = {
                    'name': 'INVOICE',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.rak_arsip_folder_id]
                }
                folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
                self.invoice_folder_id = folder.get('id')
                print(f"Created INVOICE folder with ID: {self.invoice_folder_id}")
            
            return True
            
        except Exception as e:
            print(f"Error ensuring folders exist: {e}")
            return False
    
    def add_sync_button_to_file_urls_tab(self, file_urls_helper):
        """Connect Sync to Drive button in File URLs tab"""
        try:
            # Connect the existing sync button to our sync function
            if hasattr(file_urls_helper, 'sync_drive_btn') and file_urls_helper.sync_drive_btn:
                file_urls_helper.sync_drive_btn.clicked.connect(lambda: self.sync_to_drive(file_urls_helper))
                print("Sync to Drive button connected in File URLs tab")
                return True
            else:
                print("Sync to Drive button not found in File URLs helper")
                return False
        except Exception as e:
            print(f"Error connecting sync button: {e}")
        
        return False
    
    def sync_to_drive(self, file_urls_helper):
        """Sync current file URLs data to Google Drive as spreadsheet"""
        print("=== SYNC TO DRIVE CLICKED ===")
        print(f"Selected Client ID: {file_urls_helper._selected_client_id}")
        print(f"Selected Batch Number: {file_urls_helper._selected_batch_number}")
        
        # Cek apakah ada data yang dipilih
        if not file_urls_helper._selected_client_id or not file_urls_helper._selected_batch_number:
            print("No client or batch selected")
            QMessageBox.warning(self.parent, "No Selection", "Please select a client and batch first.")
            return
        
        # Ensure folders exist
        if not self.ensure_folders_exist():
            print("Failed to ensure folders exist")
            QMessageBox.critical(self.parent, "Error", "Failed to initialize Google Drive folders.")
            return
        
        try:
            # Get client info
            client_name = file_urls_helper._client_name_label.text().replace("Client: ", "")
            client_id = file_urls_helper._selected_client_id
            batch_number = file_urls_helper._selected_batch_number
            total_files = len(file_urls_helper._file_urls_data_filtered)
            
            print(f"Client Name: {client_name}")
            print(f"Client ID: {client_id}")
            print(f"Batch Number: {batch_number}")
            print(f"Total Files: {total_files}")
            
            # Step 1: Find Template folder and Invoice_Template file
            template_file_id = self.find_invoice_template()
            if not template_file_id:
                QMessageBox.critical(self.parent, "Template Not Found", "Invoice_Template file not found in Template folder.")
                return
            
            # Step 2: Create folder structure
            target_folder_id = self.create_folder_structure(client_id, client_name)
            if not target_folder_id:
                QMessageBox.critical(self.parent, "Folder Creation Failed", "Failed to create folder structure.")
                return
            
            # Step 3: Generate invoice filename
            invoice_filename = self.generate_invoice_filename(client_name, batch_number, total_files)
            print(f"Generated filename: {invoice_filename}")
            
            # Step 4: Check if invoice file already exists for this batch
            existing_file_id = self.find_existing_invoice(target_folder_id, client_name, batch_number)
            
            if existing_file_id:
                print(f"Found existing invoice file for batch {batch_number}, updating instead of creating new file")
                QMessageBox.information(
                    self.parent, 
                    "Update Mode", 
                    f"Invoice file for batch {batch_number} already exists.\nUpdating existing file.\n\nFile ID: {existing_file_id}"
                )
                # TODO: Here we can add code to update the existing spreadsheet with new data
                print(f"Invoice file updated with ID: {existing_file_id}")
            else:
                # Step 5: Copy template and create new file
                new_file_id = self.copy_template_to_target(template_file_id, target_folder_id, invoice_filename)
                if new_file_id:
                    QMessageBox.information(
                        self.parent, 
                        "Success", 
                        f"New invoice file created successfully:\n{invoice_filename}\n\nFile ID: {new_file_id}"
                    )
                    print(f"New invoice file created with ID: {new_file_id}")
                else:
                    QMessageBox.critical(self.parent, "Copy Failed", "Failed to copy template and create invoice file.")
            
        except Exception as e:
            print(f"Error during sync: {e}")
            QMessageBox.critical(self.parent, "Sync Error", f"Error during sync: {str(e)}")
    
    def find_invoice_template(self):
        """Find Invoice_Template file in Template folder"""
        try:
            print("Searching for Template folder...")
            
            # Search for Template folder
            template_results = self.drive_service.files().list(
                q="name = 'Template' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name)",
                pageSize=10
            ).execute()
            
            template_folders = template_results.get('files', [])
            if not template_folders:
                print("Template folder not found")
                return None
            
            template_folder_id = template_folders[0]['id']
            print(f"Found Template folder with ID: {template_folder_id}")
            
            # Search for Invoice_Template file in Template folder
            invoice_results = self.drive_service.files().list(
                q=f"name = 'Invoice_Template' and '{template_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=10
            ).execute()
            
            invoice_files = invoice_results.get('files', [])
            if not invoice_files:
                print("Invoice_Template file not found in Template folder")
                return None
            
            template_file_id = invoice_files[0]['id']
            template_mime_type = invoice_files[0]['mimeType']
            print(f"Found Invoice_Template file with ID: {template_file_id}, MIME type: {template_mime_type}")
            
            return template_file_id
            
        except Exception as e:
            print(f"Error finding invoice template: {e}")
            return None
    
    def find_existing_invoice(self, target_folder_id, client_name, batch_number):
        """Find existing invoice file for the same client and batch number"""
        try:
            print(f"Checking for existing invoice file with batch number: {batch_number}")
            
            # Clean client name for search pattern
            clean_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_client_name = clean_client_name.replace(' ', '_')
            
            # Search pattern: Invoice_ClientName_BatchNumber_*
            search_pattern = f"Invoice_{clean_client_name}_{batch_number}_"
            
            print(f"Searching for files with pattern: {search_pattern}")
            
            # Search for files in target folder that match the pattern
            results = self.drive_service.files().list(
                q=f"name contains '{search_pattern}' and '{target_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=10
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                # Filter files that exactly match our pattern (to avoid partial matches)
                for file in files:
                    filename = file['name']
                    if filename.startswith(search_pattern):
                        file_id = file['id']
                        print(f"Found existing invoice file: {filename} (ID: {file_id})")
                        return file_id
                
                print("No exact match found for the batch number pattern")
                return None
            else:
                print("No existing invoice files found for this batch")
                return None
                
        except Exception as e:
            print(f"Error finding existing invoice: {e}")
            return None
    
    def create_folder_structure(self, client_id, client_name):
        """Create folder structure: INVOICE/client_id/year/month"""
        try:
            from datetime import datetime
            
            current_date = datetime.now()
            year = current_date.strftime("%Y")
            month = current_date.strftime("%B")  # Full month name like "August"
            
            print(f"Creating folder structure for client {client_id} ({client_name})")
            print(f"Year: {year}, Month: {month}")
            
            # Step 1: Check/Create client folder inside INVOICE
            client_folder_id = self.get_or_create_folder(str(client_id), self.invoice_folder_id)
            if not client_folder_id:
                print("Failed to create client folder")
                return None
            
            print(f"Client folder ID: {client_folder_id}")
            
            # Step 2: Check/Create year folder inside client folder
            year_folder_id = self.get_or_create_folder(year, client_folder_id)
            if not year_folder_id:
                print("Failed to create year folder")
                return None
            
            print(f"Year folder ID: {year_folder_id}")
            
            # Step 3: Check/Create month folder inside year folder
            month_folder_id = self.get_or_create_folder(month, year_folder_id)
            if not month_folder_id:
                print("Failed to create month folder")
                return None
            
            print(f"Month folder ID: {month_folder_id}")
            
            return month_folder_id
            
        except Exception as e:
            print(f"Error creating folder structure: {e}")
            return None
    
    def get_or_create_folder(self, folder_name, parent_folder_id):
        """Get existing folder or create new one"""
        try:
            # Check if folder exists
            results = self.drive_service.files().list(
                q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                print(f"Found existing folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            
            # Create new folder
            print(f"Creating new folder '{folder_name}'...")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Created folder '{folder_name}' with ID: {folder_id}")
            
            return folder_id
            
        except Exception as e:
            print(f"Error creating folder '{folder_name}': {e}")
            return None
    
    def generate_invoice_filename(self, client_name, batch_number, total_files):
        """Generate invoice filename: Invoice_clientname_batchnumber_YYYY_Month_DD_totalfiles"""
        try:
            from datetime import datetime
            
            current_date = datetime.now()
            year = current_date.strftime("%Y")
            month = current_date.strftime("%B")
            day = current_date.strftime("%d")
            
            # Clean client name (remove spaces and special characters)
            clean_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_client_name = clean_client_name.replace(' ', '_')
            
            filename = f"Invoice_{clean_client_name}_{batch_number}_{year}_{month}_{day}_{total_files}"
            
            return filename
            
        except Exception as e:
            print(f"Error generating filename: {e}")
            return f"Invoice_{client_name}_{batch_number}"
    
    def copy_template_to_target(self, template_file_id, target_folder_id, new_filename):
        """Copy template file to target folder with new name"""
        try:
            print(f"Copying template to target folder...")
            print(f"Template ID: {template_file_id}")
            print(f"Target folder ID: {target_folder_id}")
            print(f"New filename: {new_filename}")
            
            # Copy file
            copy_metadata = {
                'name': new_filename,
                'parents': [target_folder_id]
            }
            
            copied_file = self.drive_service.files().copy(
                fileId=template_file_id,
                body=copy_metadata,
                fields='id,name'
            ).execute()
            
            new_file_id = copied_file.get('id')
            new_file_name = copied_file.get('name')
            
            print(f"Successfully copied template to: {new_file_name} (ID: {new_file_id})")
            
            return new_file_id
            
        except Exception as e:
            print(f"Error copying template: {e}")
            return None
