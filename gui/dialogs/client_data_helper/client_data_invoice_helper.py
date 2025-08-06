from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy, QHeaderView, QMessageBox, QMenu, QComboBox, QLabel,
    QProgressDialog
)
from PySide6.QtCore import Qt, Signal, QCoreApplication
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
        
        # Progress tracking
        self.progress_dialog = None
        self.current_step = 0
        self.total_steps = 0
    
    def init_progress(self, steps, title="Processing..."):
        """Initialize progress dialog with dynamic step calculation"""
        self.total_steps = len(steps)
        self.current_step = 0
        
        self.progress_dialog = QProgressDialog("Initializing...", "Cancel", 0, self.total_steps, self.parent)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setModal(True)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        QCoreApplication.processEvents()
        
        print(f"Progress initialized: {self.total_steps} steps")
    
    def update_progress(self, step_description):
        """Update progress to next step with description"""
        if not self.progress_dialog:
            return False
            
        if self.progress_dialog.wasCanceled():
            return False
            
        self.current_step += 1
        progress_percentage = int((self.current_step / self.total_steps) * 100)
        
        self.progress_dialog.setLabelText(step_description)
        self.progress_dialog.setValue(self.current_step)
        QCoreApplication.processEvents()
        
        print(f"Progress: Step {self.current_step}/{self.total_steps} ({progress_percentage}%) - {step_description}")
        return True
    
    def close_progress(self):
        """Close progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.current_step = 0
        self.total_steps = 0
    
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
        
        # Get client info first to determine steps needed
        client_name = file_urls_helper._client_name_label.text().replace("Client: ", "")
        client_id = file_urls_helper._selected_client_id
        batch_number = file_urls_helper._selected_batch_number
        
        # Get actual file count from database (not just filtered URLs)
        actual_file_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
        total_files = actual_file_count  # Use actual count from database
        
        print(f"Client Name: {client_name}")
        print(f"Client ID: {client_id}")
        print(f"Batch Number: {batch_number}")
        print(f"Total Files (from database): {total_files}")
        print(f"Filtered URLs Count: {len(file_urls_helper._file_urls_data_filtered)}")
        
        # Define all possible steps dynamically
        sync_steps = [
            "Connecting to Google Drive",
            "Checking/Creating main folders",
            "Searching for invoice template", 
            "Creating client folder structure",
            "Generating invoice filename",
            "Checking for existing invoice files"
        ]
        
        # Add conditional step based on whether file exists or not
        # We'll determine this during execution and add the appropriate step
        
        # Initialize progress with known steps
        self.init_progress(sync_steps, "Syncing to Google Drive")
        
        try:
            # Step 1: Initialize Google Drive connection and ensure folders exist
            if not self.update_progress("Connecting to Google Drive..."):
                return
            
            if not self.ensure_folders_exist():
                print("Failed to ensure folders exist")
                self.close_progress()
                QMessageBox.critical(self.parent, "Error", "Failed to initialize Google Drive folders.")
                return
            
            # Step 2: Verify folders are ready
            if not self.update_progress("Checking/Creating main folders..."):
                return
            
            # Step 3: Find Template folder and Invoice_Template file
            if not self.update_progress("Searching for invoice template..."):
                return
            
            template_file_id = self.find_invoice_template()
            if not template_file_id:
                self.close_progress()
                QMessageBox.critical(self.parent, "Template Not Found", "Invoice_Template file not found in Template folder.")
                return
            
            # Step 4: Create folder structure
            if not self.update_progress("Creating client folder structure..."):
                return
            
            target_folder_id = self.create_folder_structure(client_id, client_name, batch_number)
            if not target_folder_id:
                self.close_progress()
                QMessageBox.critical(self.parent, "Folder Creation Failed", "Failed to create folder structure.")
                return
            
            # Step 5: Generate invoice filename
            if not self.update_progress("Generating invoice filename..."):
                return
            
            invoice_filename = self.generate_invoice_filename(client_name, batch_number, total_files)
            print(f"Generated filename: {invoice_filename}")
            
            # Step 6: Check if invoice file already exists for this batch
            if not self.update_progress("Checking for existing invoice files..."):
                return
            
            existing_file_id, existing_filename, existing_count = self.find_existing_invoice(target_folder_id, client_name, batch_number)
            
            # Now we know if we need to add update step or create step
            if existing_file_id:
                # Check if count has changed and needs renaming
                if existing_count != total_files:
                    # Add rename step dynamically
                    self.total_steps += 1
                    self.progress_dialog.setMaximum(self.total_steps)
                    
                    if not self.update_progress(f"Renaming file (count changed: {existing_count} → {total_files})..."):
                        return
                    
                    # Generate new filename with updated count
                    new_filename = self.generate_invoice_filename(client_name, batch_number, total_files)
                    
                    # Rename the existing file
                    renamed_file_id = self.rename_existing_invoice(existing_file_id, new_filename)
                    
                    if renamed_file_id:
                        print(f"Successfully renamed existing invoice file for batch {batch_number}")
                        self.close_progress()
                        
                        QMessageBox.information(
                            self.parent, 
                            "File Renamed", 
                            f"Invoice file for batch {batch_number} has been renamed to reflect updated count.\n\nOld: {existing_filename}\nNew: {new_filename}\n\nFile ID: {renamed_file_id}"
                        )
                        print(f"Invoice file renamed with ID: {renamed_file_id}")
                    else:
                        self.close_progress()
                        QMessageBox.critical(self.parent, "Rename Failed", "Failed to rename existing invoice file to update count.")
                else:
                    # Count is the same, just update
                    self.total_steps += 1
                    self.progress_dialog.setMaximum(self.total_steps)
                    
                    if not self.update_progress("Updating existing invoice file (count unchanged)..."):
                        return
                    
                    print(f"Found existing invoice file for batch {batch_number}, count unchanged ({existing_count})")
                    self.close_progress()
                    
                    QMessageBox.information(
                        self.parent, 
                        "Update Mode", 
                        f"Invoice file for batch {batch_number} already exists with correct count ({existing_count}).\n\nFile: {existing_filename}\nFile ID: {existing_file_id}"
                    )
                    print(f"Invoice file already up to date with ID: {existing_file_id}")
            else:
                # Add create step dynamically
                self.total_steps += 1
                self.progress_dialog.setMaximum(self.total_steps)
                
                if not self.update_progress("Copying template and creating new invoice file..."):
                    return
                
                new_file_id = self.copy_template_to_target(template_file_id, target_folder_id, invoice_filename)
                
                self.close_progress()
                
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
            self.close_progress()
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
        """Find existing invoice file for the same client and batch number
        Returns: (file_id, filename, file_count) or (None, None, 0) if not found"""
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
                        current_count = self.extract_count_from_filename(filename)
                        print(f"Found existing invoice file: {filename} (ID: {file_id}, Count: {current_count})")
                        return (file_id, filename, current_count)
                
                print("No exact match found for the batch number pattern")
                return (None, None, 0)
            else:
                print("No existing invoice files found for this batch")
                return (None, None, 0)
                
        except Exception as e:
            print(f"Error finding existing invoice: {e}")
            return (None, None, 0)
                
        except Exception as e:
            print(f"Error finding existing invoice: {e}")
            return None
    
    def rename_existing_invoice(self, file_id, new_filename):
        """Rename existing invoice file to reflect updated count"""
        try:
            print(f"Renaming existing file with ID: {file_id} to: {new_filename}")
            
            # Rename the file
            file_metadata = {
                'name': new_filename
            }
            
            updated_file = self.drive_service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id,name'
            ).execute()
            
            updated_file_id = updated_file.get('id')
            updated_file_name = updated_file.get('name')
            
            print(f"Successfully renamed file to: {updated_file_name} (ID: {updated_file_id})")
            
            return updated_file_id
            
        except Exception as e:
            print(f"Error renaming existing invoice: {e}")
            return None
    
    def extract_count_from_filename(self, filename):
        """Extract the file count from existing invoice filename"""
        try:
            # Expected pattern: Invoice_ClientName_BatchNumber_YYYY_Month_DD_COUNT
            parts = filename.split('_')
            if len(parts) >= 6:
                # Count should be the last part
                count_str = parts[-1]
                try:
                    return int(count_str)
                except ValueError:
                    print(f"Could not parse count from filename: {filename}")
                    return 0
            return 0
        except Exception as e:
            print(f"Error extracting count from filename: {e}")
            return 0
    
    def create_folder_structure(self, client_id, client_name, batch_number):
        """Create folder structure: INVOICE/client_id/year/month based on batch creation date"""
        try:
            from datetime import datetime
            
            # Get batch creation date from database
            batch_created_at = self.db_helper.get_batch_created_date(batch_number, client_id)
            
            if batch_created_at:
                # Parse the database timestamp
                if isinstance(batch_created_at, str):
                    # Parse string format like "2025-08-06 14:30:25" or "2025-08-06"
                    try:
                        batch_date = datetime.strptime(batch_created_at, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            batch_date = datetime.strptime(batch_created_at, "%Y-%m-%d")
                        except ValueError:
                            print(f"Unable to parse batch date: {batch_created_at}, using current date")
                            batch_date = datetime.now()
                else:
                    batch_date = batch_created_at
            else:
                print(f"No batch found for batch_number: {batch_number}, using current date")
                batch_date = datetime.now()
            
            year = batch_date.strftime("%Y")
            month = batch_date.strftime("%B")  # Full month name like "August"
            
            print(f"Creating folder structure for client {client_id} ({client_name})")
            print(f"Batch: {batch_number}, Batch Date: {batch_date.strftime('%Y-%m-%d')}")
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
    
    def get_invoice_share_link(self, client_id, client_name, batch_number):
        """Get shareable read-only link for invoice file"""
        try:
            if not self.drive_service:
                if not self.init_google_drive_connection():
                    return None
            
            if not self.ensure_folders_exist():
                return None
            
            # Create folder structure path to find the file
            target_folder_id = self.create_folder_structure(client_id, client_name, batch_number)
            if not target_folder_id:
                return None
            
            # Find existing invoice file
            existing_file_id, existing_filename, existing_count = self.find_existing_invoice(target_folder_id, client_name, batch_number)
            
            if not existing_file_id:
                print(f"No invoice file found for client {client_name}, batch {batch_number}")
                return None
            
            # Get shareable link
            print(f"Getting share link for file ID: {existing_file_id}")
            
            # Create permission for anyone with the link to view
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            # Add the permission
            self.drive_service.permissions().create(
                fileId=existing_file_id,
                body=permission,
                fields='id'
            ).execute()
            
            # Get the file details including webViewLink
            file_info = self.drive_service.files().get(
                fileId=existing_file_id,
                fields='webViewLink, name'
            ).execute()
            
            share_link = file_info.get('webViewLink')
            filename = file_info.get('name')
            
            print(f"Share link obtained for {filename}: {share_link}")
            return share_link
            
        except Exception as e:
            print(f"Error getting invoice share link: {e}")
            return None
