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
import time


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
                    # Add rename step dynamically - now 12 steps in update_invoice_sheet_data_with_progress
                    self.total_steps += 12  # Clear + Resize + Format + Insert + Special + Merge + Format Copy + Delete + EF Merge + Payment Highlight + Final Merge + External Data Access
                    self.progress_dialog.setMaximum(self.total_steps)
                    
                    if not self.update_progress(f"Renaming file (count changed: {existing_count} → {total_files})..."):
                        return
                    
                    # Generate new filename with updated count
                    new_filename = self.generate_invoice_filename(client_name, batch_number, total_files)
                    
                    # Rename the existing file
                    renamed_file_id = self.rename_existing_invoice(existing_file_id, new_filename)
                    
                    if not renamed_file_id:
                        self.close_progress()
                        QMessageBox.critical(self.parent, "Rename Failed", "Failed to rename existing invoice file to update count.")
                        return
                    
                    # Update sheet data with detailed progress
                    if self.update_invoice_sheet_data_with_progress(renamed_file_id, client_id, batch_number, file_urls_helper, is_new_file=False):
                        print(f"Successfully updated invoice file and data for batch {batch_number}")
                        self.close_progress()
                        
                        QMessageBox.information(
                            self.parent, 
                            "File Updated", 
                            f"Invoice file for batch {batch_number} has been renamed and data updated.\n\nOld: {existing_filename}\nNew: {new_filename}\n\nTotal records: {total_files}"
                        )
                        print(f"Invoice file renamed and updated with ID: {renamed_file_id}")
                    else:
                        self.close_progress()
                        QMessageBox.warning(self.parent, "Partial Success", f"File renamed successfully but failed to update sheet data.\n\nFile ID: {renamed_file_id}")
                else:
                    # Count is the same, just update data - now 11 steps in update_invoice_sheet_data_with_progress  
                    self.total_steps += 11  # Clear + Resize + Format + Insert + Special + Merge + Format Copy + Delete + EF Merge + Payment Highlight + External Data Access
                    self.progress_dialog.setMaximum(self.total_steps)
                    
                    # Update sheet data with detailed progress
                    if self.update_invoice_sheet_data_with_progress(existing_file_id, client_id, batch_number, file_urls_helper, is_new_file=False):
                        print(f"Successfully updated invoice data for batch {batch_number}")
                        self.close_progress()
                        
                        QMessageBox.information(
                            self.parent, 
                            "Data Updated", 
                            f"Invoice data for batch {batch_number} has been updated successfully.\n\nFile: {existing_filename}\nTotal records: {existing_count}"
                        )
                        print(f"Invoice data updated for file ID: {existing_file_id}")
                    else:
                        self.close_progress()
                        QMessageBox.warning(self.parent, "Update Failed", f"Failed to update invoice sheet data.\n\nFile: {existing_filename}")
            else:
                # Add create step dynamically - now 11 steps in update_invoice_sheet_data_with_progress
                self.total_steps += 11  # Clear + Resize + Format + Insert + Special + Merge + Format Copy + Delete + EF Merge + Payment Highlight + External Data Access
                self.progress_dialog.setMaximum(self.total_steps)
                
                if not self.update_progress("Copying template and creating new invoice file..."):
                    return
                
                new_file_id = self.copy_template_to_target(template_file_id, target_folder_id, invoice_filename)
                
                if not new_file_id:
                    self.close_progress()
                    QMessageBox.critical(self.parent, "Copy Failed", "Failed to copy template and create invoice file.")
                    return
                
                # Update sheet data for new file with detailed progress
                if self.update_invoice_sheet_data_with_progress(new_file_id, client_id, batch_number, file_urls_helper, is_new_file=True):
                    self.close_progress()
                    
                    QMessageBox.information(
                        self.parent, 
                        "Success", 
                        f"New invoice file created and populated successfully:\n{invoice_filename}\n\nTotal records: {total_files}"
                    )
                    print(f"New invoice file created and populated with ID: {new_file_id}")
                else:
                    self.close_progress()
                    QMessageBox.warning(self.parent, "Partial Success", f"Invoice file created but failed to populate data.\n\nFile: {invoice_filename}\nFile ID: {new_file_id}")
            
            
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

    def update_invoice_sheet_data(self, file_id, client_id, batch_number):
        """Update invoice sheet with batch data starting from B39"""
        try:
            print(f"Updating invoice sheet data for file ID: {file_id}")
            
            # Get all files data for this batch and client
            batch_data = self.db_helper.get_all_files_by_batch_and_client_with_details(batch_number, client_id)
            
            if not batch_data:
                print("No batch data found")
                return False
            
            # Clear existing data from B39 downwards first
            if not self.clear_invoice_data_range(file_id):
                print("Failed to clear existing data")
                return False
            
            # Ensure sheet has enough rows for the data
            required_rows = 40 + len(batch_data)  # 40 for header + template + data rows start from 40
            if not self.ensure_sheet_size(file_id, required_rows):
                print("Failed to ensure adequate sheet size")
                return False
            
            # Format data for sheet insertion
            formatted_data = self.format_data_for_sheet(batch_data, batch_number)
            
            if not formatted_data:
                print("No formatted data to insert")
                return False
            
            # Get actual sheet name
            sheet_name = self.get_invoice_sheet_name(file_id)
            if not sheet_name:
                print("Could not determine sheet name")
                return False
            
            # Insert data starting from B40 (not B39, since B39 is template)
            range_name = f"{sheet_name}!B40:J{39 + len(formatted_data)}"  # B40 to J(40+count-1)
            
            body = {
                'values': formatted_data
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            print(f"Updated {result.get('updatedCells')} cells in range {range_name}")
            
            # Merge cells for filename column (C-D-E) for each row
            if not self.merge_filename_cells(file_id, len(formatted_data)):
                print("Warning: Failed to merge filename cells")
            
            # Copy formatting from template row (39) to all data rows
            if not self.copy_template_row_formatting(file_id, len(formatted_data)):
                print("Warning: Failed to copy row formatting")
            
            # Delete template row (39) after all data and formatting is complete
            if not self.delete_template_row(file_id):
                print("Warning: Failed to delete template row 39")
            
            return True
            
        except Exception as e:
            print(f"Error updating invoice sheet data: {e}")
            return False

    def update_invoice_sheet_data_with_progress(self, file_id, client_id, batch_number, file_urls_helper=None, is_new_file=False):
        """Update invoice sheet with batch data - with detailed progress tracking"""
        try:
            print(f"Updating invoice sheet data for file ID: {file_id}")
            
            # Get all files data for this batch and client
            batch_data = self.db_helper.get_all_files_by_batch_and_client_with_details(batch_number, client_id)
            
            if not batch_data:
                print("No batch data found")
                return False
            
            # Step 1: Clear existing data from B39 downwards first
            if not self.update_progress("Clearing existing invoice data..."):
                return False
            
            if not self.clear_invoice_data_range(file_id):
                print("Failed to clear existing data")
                return False
            
            # Step 2: Ensure sheet has enough rows for the data
            if not self.update_progress("Ensuring adequate sheet size..."):
                return False
            
            required_rows = 40 + len(batch_data)  # 40 for header + template + data rows start from 40
            if not self.ensure_sheet_size(file_id, required_rows):
                print("Failed to ensure adequate sheet size")
                return False
            
            # Step 3: Format data for sheet insertion
            if not self.update_progress("Formatting batch data for insertion..."):
                return False
            
            formatted_data = self.format_data_for_sheet(batch_data, batch_number)
            
            if not formatted_data:
                print("No formatted data to insert")
                return False
            
            # Step 4: Insert data starting from B40
            if not self.update_progress("Inserting batch data into spreadsheet..."):
                return False
            
            # Get actual sheet name
            sheet_name = self.get_invoice_sheet_name(file_id)
            if not sheet_name:
                print("Could not determine sheet name")
                return False
            
            # Insert data starting from B40 (not B39, since B39 is template)
            range_name = f"{sheet_name}!B40:J{39 + len(formatted_data)}"  # B40 to J(40+count-1)
            
            body = {
                'values': formatted_data
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            print(f"Updated {result.get('updatedCells')} cells in range {range_name}")
            
            # Step 5: Update special invoice cells with batch info and payment data
            if not self.update_progress("Updating special invoice cells..."):
                return False
            
            if not self.update_invoice_special_cells(file_id, client_id, batch_number, len(batch_data), file_urls_helper, is_new_file):
                print("Warning: Failed to update special invoice cells")
                return False
            
            # Step 6: Merge EF cells for client/payment info
            if not self.update_progress("Merging client information cells..."):
                return False
            
            if not self.merge_ef_cells(file_id):
                print("Warning: Failed to merge EF cells")
                return False
            
            # Step 7: Highlight payment method cell
            if not self.update_progress("Applying payment method highlighting..."):
                return False
            
            if file_urls_helper:
                payment_method = file_urls_helper.get_payment_method()
                if payment_method and payment_method != "":
                    if not self.highlight_payment_method_cell(file_id, payment_method):
                        print("Warning: Failed to highlight payment method cell")
            
            # Step 8: Merge cells for filename column (C-D-E) for each row
            if not self.update_progress("Merging filename cells..."):
                return False
            
            if not self.merge_filename_cells(file_id, len(formatted_data)):
                print("Warning: Failed to merge filename cells")
                return False
            
            # Step 9: Copy formatting from template row (39) to all data rows
            if not self.update_progress("Copying template formatting..."):
                return False
            
            if not self.copy_template_row_formatting(file_id, len(formatted_data)):
                print("Warning: Failed to copy row formatting")
                return False
            
            # Step 10: Delete template row (39) after all data and formatting is complete
            if not self.update_progress("Cleaning up template row..."):
                return False
            
            if not self.delete_template_row(file_id):
                print("Warning: Failed to delete template row 39")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error updating invoice sheet data: {e}")
            return False

    def update_invoice_special_cells(self, spreadsheet_id, client_id, batch_number, total_files, file_urls_helper=None, is_new_file=False):
        """Update special invoice cells with batch info, client data, and payment information"""
        try:
            from datetime import datetime
            
            # Get actual sheet name
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                print("Could not determine sheet name for special cells update")
                return False
            
            # Get client name from database
            client_name = ""
            try:
                client_data = self.db_helper.get_client_by_id(client_id)
                if client_data:
                    client_name = client_data.get('client_name', '')
            except:
                client_name = "Unknown Client"
            
            # Prepare cell updates
            cell_updates = []
            
            # 1. Cell C4: batch number/datetime/jumlahfile format (LVL004/2025Jul03/20)
            current_date = datetime.now()
            date_format = current_date.strftime("%Y%b%d")  # e.g., 2025Aug06
            c4_value = f"{batch_number}/{date_format}/{total_files}"
            cell_updates.append({
                'range': f"{sheet_name}!C4",
                'values': [[c4_value]]
            })
            
            # 2. Cell E9:F9 merged - Client name
            cell_updates.append({
                'range': f"{sheet_name}!E9:F9", 
                'values': [[client_name, ""]]  # Second value empty because cells are merged
            })
            
            # 3. Cell E10:F10 merged - Creation date (only set for new files)
            if is_new_file:
                creation_date = current_date.strftime("%m/%d/%Y")  # e.g., 8/6/2025
                cell_updates.append({
                    'range': f"{sheet_name}!E10:F10",
                    'values': [[creation_date, ""]]  # Second value empty because cells are merged
                })
            
            # 4. Payment status and method from file_urls_helper
            if file_urls_helper:
                payment_status = file_urls_helper.get_payment_status()
                payment_method = file_urls_helper.get_payment_method()
                
                # Cell E15:F15 merged - Payment status
                if payment_status:
                    cell_updates.append({
                        'range': f"{sheet_name}!E15:F15",
                        'values': [[payment_status, ""]]  # Second value empty because cells are merged
                    })
                
                # Cell E16:F16 merged - Payment date (only if status is Paid)
                if payment_status == "Paid":
                    payment_date = current_date.strftime("%m/%d/%Y")  # e.g., 8/20/2025
                    cell_updates.append({
                        'range': f"{sheet_name}!E16:F16",
                        'values': [[payment_date, ""]]  # Second value empty because cells are merged
                    })
            
            # Update all cells at once
            if cell_updates:
                for update in cell_updates:
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=update['range'],
                        valueInputOption='USER_ENTERED',
                        body={'values': update['values']}
                    ).execute()
                
                print(f"Updated {len(cell_updates)} special invoice cells")
            
            # Handle payment method highlighting
            if file_urls_helper:
                payment_method = file_urls_helper.get_payment_method()
                if payment_method and payment_method != "":
                    if not self.highlight_payment_method_cell(spreadsheet_id, payment_method):
                        print("Warning: Failed to highlight payment method cell")
            
            return True
            
        except Exception as e:
            print(f"Error updating special invoice cells: {e}")
            return False

    def highlight_payment_method_cell(self, spreadsheet_id, payment_method):
        """Highlight the appropriate cell based on payment method selection - clear others first"""
        try:
            # Payment method to cell mapping
            payment_cell_map = {
                "GoPay": "C21",
                "DANA": "D21", 
                "OVO": "E21",
                "LinkAja": "F21",
                "QRIS": "H19",
                "Bank Jago": "C26",
                "BCA": "C27",
                "BRI": "C28",
                "PayPal": "C29"
            }
            
            # Get sheet ID for the request
            sheet_id = 0  # Assuming Invoice is the first sheet
            import re
            
            requests = []
            
            # First, clear all payment method cells (reset to default background)
            for method, cell_ref in payment_cell_map.items():
                # Convert cell reference to row/column indices
                match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                if match:
                    col_letters = match.group(1)
                    row_number = int(match.group(2))
                    
                    # Convert column letters to index (A=0, B=1, etc.)
                    col_index = 0
                    for char in col_letters:
                        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
                    col_index -= 1  # Convert to 0-based index
                    
                    row_index = row_number - 1  # Convert to 0-based index
                    
                    # Clear background color (set to default/transparent)
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': row_index,
                                'endRowIndex': row_index + 1,
                                'startColumnIndex': col_index,
                                'endColumnIndex': col_index + 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 1.0,
                                        'green': 1.0,
                                        'blue': 1.0
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.backgroundColor'
                        }
                    })
            
            # Now highlight only the selected payment method
            target_cell = payment_cell_map.get(payment_method)
            if target_cell:
                # Convert cell reference to row/column indices
                match = re.match(r'([A-Z]+)(\d+)', target_cell)
                if match:
                    col_letters = match.group(1)
                    row_number = int(match.group(2))
                    
                    # Convert column letters to index (A=0, B=1, etc.)
                    col_index = 0
                    for char in col_letters:
                        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
                    col_index -= 1  # Convert to 0-based index
                    
                    row_index = row_number - 1  # Convert to 0-based index
                    
                    # Create format request with green background
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': row_index,
                                'endRowIndex': row_index + 1,
                                'startColumnIndex': col_index,
                                'endColumnIndex': col_index + 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 0.0,
                                        'green': 1.0,
                                        'blue': 0.0
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.backgroundColor'
                        }
                    })
            
            # Execute all format requests in one batch
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                if target_cell:
                    print(f"Cleared all payment cells and highlighted {target_cell} for {payment_method}")
                else:
                    print(f"Cleared all payment cells (no mapping found for: {payment_method})")
            
            return True
            
        except Exception as e:
            print(f"Error highlighting payment method cell: {e}")
            return False

    def merge_ef_cells(self, spreadsheet_id):
        """Merge EF cells for rows 9, 10, 14, 15, 16"""
        try:
            sheet_id = 0  # Assuming Invoice is the first sheet
            
            # Rows to merge EF cells (0-based indexing)
            merge_rows = [8, 9, 13, 14, 15]  # Rows 9, 10, 14, 15, 16 in 0-based
            
            requests = []
            for row_index in merge_rows:
                merge_request = {
                    'mergeCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': row_index,
                            'endRowIndex': row_index + 1,
                            'startColumnIndex': 4,  # Column E (0-based = 4)
                            'endColumnIndex': 6     # Column F (exclusive, so 6 means up to F)
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                }
                requests.append(merge_request)
            
            # Execute batch requests
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                print(f"Successfully merged EF cells for {len(requests)} rows")
            
            return True
            
        except Exception as e:
            print(f"Error merging EF cells: {e}")
            return False

    def get_invoice_sheet_name(self, spreadsheet_id):
        """Get the name of the invoice sheet - check Invoice first, then use first sheet"""
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='sheets.properties.title'
            ).execute()
            
            # First try to find "Invoice" sheet
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == 'Invoice':
                    return 'Invoice'
            
            # If not found, use first sheet
            if spreadsheet.get('sheets'):
                first_sheet_name = spreadsheet['sheets'][0]['properties']['title']
                print(f"Invoice sheet not found, using first sheet: {first_sheet_name}")
                return first_sheet_name
                
            return None
            
        except Exception as e:
            print(f"Error getting sheet name: {e}")
            return None

    def clear_invoice_data_range(self, spreadsheet_id):
        """Clear existing data from B40 downwards (preserve template row 39)"""
        try:
            print("Clearing existing invoice data from B40 downwards (preserving template row 39)...")
            
            # Get actual sheet name
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                print("Could not determine sheet name")
                return False
            
            # Clear from B40 downwards to preserve template row 39
            clear_range = f"{sheet_name}!B40:J1000"  # Clear from row 40, preserve template at row 39
            
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=clear_range
            ).execute()
            
            print(f"Cleared range: {clear_range}")
            return True
            
        except Exception as e:
            print(f"Error clearing invoice data range: {e}")
            return False

    def format_data_for_sheet(self, batch_data, batch_number):
        """Format database data for sheet insertion"""
        try:
            print(f"Formatting {len(batch_data)} records for sheet insertion")
            
            formatted_rows = []
            
            for i, item in enumerate(batch_data, 1):
                # Extract data from tuple
                # item structure: (file_id, filename, date, root, path, status_id, category_id, subcategory_id, category_name, subcategory_name, url_value, provider_name, price_value, currency)
                filename = item[1] or ""
                date = item[2] or ""
                category_name = item[8] or ""
                subcategory_name = item[9] or ""
                url_value = item[10] or ""
                price_value = item[12]
                
                # Format price
                price = ""
                if price_value is not None:
                    if isinstance(price_value, (int, float)) and price_value == int(price_value):
                        price = str(int(price_value))
                    else:
                        price = str(price_value)
                
                # Create row: [No, Filename(C), Filename(D), Filename(E), Category, Subcategory, Batch, URL, Price]
                # Filename will span C-D-E, so we put it in C and leave D-E empty for merging
                row = [
                    i,                    # B: No
                    filename,             # C: Filename (will be merged across C-D-E)
                    "",                   # D: Empty (will be merged)
                    "",                   # E: Empty (will be merged)
                    category_name,        # F: Category
                    subcategory_name,     # G: Subcategory
                    batch_number,         # H: Batch Number
                    url_value,            # I: URL
                    price                 # J: Price
                ]
                
                formatted_rows.append(row)
            
            print(f"Formatted {len(formatted_rows)} rows for insertion")
            return formatted_rows
            
        except Exception as e:
            print(f"Error formatting data for sheet: {e}")
            return []

    def merge_filename_cells(self, spreadsheet_id, data_rows_count):
        """Merge cells C-D-E for filename in each data row starting from row 40"""
        try:
            print(f"Merging filename cells for {data_rows_count} rows starting from row 40")
            
            # Prepare batch requests for merging
            requests = []
            
            for i in range(data_rows_count):
                row_index = 39 + i  # Start from row 40 (0-indexed = 39)
                
                # Merge C-D-E for this row (columns 2-3-4 in 0-indexed)
                merge_request = {
                    'mergeCells': {
                        'range': {
                            'sheetId': 0,  # Assuming Invoice is the first sheet
                            'startRowIndex': row_index,
                            'endRowIndex': row_index + 1,
                            'startColumnIndex': 2,  # Column C
                            'endColumnIndex': 5      # Column E (exclusive, so 5 means up to E)
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                }
                requests.append(merge_request)
            
            # Execute batch requests
            if requests:
                body = {
                    'requests': requests
                }
                
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                print(f"Successfully merged {len(requests)} filename cell ranges")
            
            return True
            
        except Exception as e:
            print(f"Error merging filename cells: {e}")
            return False

    def copy_template_row_formatting(self, spreadsheet_id, data_rows_count):
        """Copy formatting from template row (39) to all data rows (40+)"""
        try:
            print(f"Copying template row 39 formatting to {data_rows_count} data rows (40+)")
            
            if data_rows_count == 0:
                print("No data rows to format")
                return True
            
            # Prepare batch requests for copying formatting
            requests = []
            
            # Source range: Row 39 (template row) from B to J
            source_range = {
                'sheetId': 0,  # Assuming Invoice is the first sheet
                'startRowIndex': 38,  # Row 39 (0-indexed = 38)
                'endRowIndex': 39,    # Exclusive, so just row 39
                'startColumnIndex': 1,  # Column B
                'endColumnIndex': 10    # Column J (exclusive, so up to J)
            }
            
            # For each data row, copy formatting from template row (39)
            for i in range(data_rows_count):
                target_row_index = 39 + i  # Start from row 40 (0-indexed = 39)
                
                # Target range: Current data row from B to J
                target_range = {
                    'sheetId': 0,
                    'startRowIndex': target_row_index,
                    'endRowIndex': target_row_index + 1,
                    'startColumnIndex': 1,  # Column B
                    'endColumnIndex': 10    # Column J (exclusive, so up to J)
                }
                
                # Copy format request
                copy_format_request = {
                    'copyPaste': {
                        'source': source_range,
                        'destination': target_range,
                        'pasteType': 'PASTE_FORMAT',
                        'pasteOrientation': 'NORMAL'
                    }
                }
                
                requests.append(copy_format_request)
            
            # Execute batch requests
            if requests:
                body = {
                    'requests': requests
                }
                
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                print(f"Successfully copied formatting to {len(requests)} data rows")
            
            return True
            
        except Exception as e:
            print(f"Error copying template row formatting: {e}")
            return False

    def delete_template_row(self, spreadsheet_id):
        """Delete template row (39) after data insertion and formatting is complete"""
        try:
            print("Deleting template row 39 after data insertion...")
            
            # Prepare delete request for row 39 (0-indexed = 38)
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': 0,  # Assuming Invoice is the first sheet
                        'dimension': 'ROWS',
                        'startIndex': 38,  # Row 39 (0-indexed = 38)
                        'endIndex': 39     # Exclusive, so just row 39
                    }
                }
            }]
            
            # Execute delete request
            body = {'requests': requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print("Successfully deleted template row 39")
            return True
            
        except Exception as e:
            print(f"Error deleting template row: {e}")
            return False

    def ensure_sheet_size(self, spreadsheet_id, required_rows, required_cols=11):
        """Ensure the Invoice sheet has enough rows and columns"""
        try:
            print(f"Ensuring sheet has at least {required_rows} rows and {required_cols} columns")
            
            # Get current sheet properties
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='sheets.properties'
            ).execute()
            
            # Debug: Print all available sheets
            print("Available sheets in spreadsheet:")
            for sheet in spreadsheet.get('sheets', []):
                sheet_title = sheet['properties']['title']
                print(f"  - {sheet_title}")
            
            # Find the Invoice sheet directly
            invoice_sheet = None
            for sheet in spreadsheet.get('sheets', []):
                sheet_title = sheet['properties']['title']
                if sheet_title == 'Invoice':
                    invoice_sheet = sheet
                    break
            
            if not invoice_sheet:
                # Try with first sheet as fallback
                if spreadsheet.get('sheets'):
                    invoice_sheet = spreadsheet['sheets'][0]
                    print(f"Invoice sheet not found, using first sheet: {invoice_sheet['properties']['title']}")
                else:
                    print("No sheets found in spreadsheet")
                    return False
            
            sheet_id = invoice_sheet['properties']['sheetId']
            current_rows = invoice_sheet['properties']['gridProperties']['rowCount']
            current_cols = invoice_sheet['properties']['gridProperties']['columnCount']
            
            print(f"Current sheet size: {current_rows} rows, {current_cols} columns")
            print(f"Required sheet size: {required_rows} rows, {required_cols} columns")
            
            # Check if we need to expand
            needs_expansion = False
            new_rows = current_rows
            new_cols = current_cols
            
            if current_rows < required_rows:
                new_rows = required_rows + 10  # Add some buffer
                needs_expansion = True
                print(f"Need to expand rows from {current_rows} to {new_rows}")
            
            if current_cols < required_cols:
                new_cols = required_cols + 2  # Add some buffer
                needs_expansion = True
                print(f"Need to expand columns from {current_cols} to {new_cols}")
            
            if needs_expansion:
                # Prepare resize request
                requests = [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'rowCount': new_rows,
                                'columnCount': new_cols
                            }
                        },
                        'fields': 'gridProperties.rowCount,gridProperties.columnCount'
                    }
                }]
                
                # Execute resize
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                print(f"Successfully resized sheet to {new_rows} rows and {new_cols} columns")
            else:
                print("Sheet size is adequate, no expansion needed")
            
            return True
            
        except Exception as e:
            print(f"Error ensuring sheet size: {e}")
            return False

    def upload_payment_proof(self, client_id, client_name, batch_number, image_file_path):
        """Upload payment proof image to same folder as invoice and insert into K2:K24 merged cell"""
        try:
            print(f"Uploading payment proof for client {client_name}, batch {batch_number}")
            print(f"Image file: {image_file_path}")
            
            # Show progress dialog with detailed steps
            from PySide6.QtWidgets import QProgressDialog, QMessageBox
            from PySide6.QtCore import QCoreApplication
            
            progress = QProgressDialog("Preparing upload...", "Cancel", 0, 9, self.parent)
            progress.setWindowTitle("Upload Payment Proof")
            progress.setModal(True)
            progress.setValue(0)
            progress.show()
            QCoreApplication.processEvents()
            
            try:
                # Step 1: Initialize Google Drive connection
                progress.setLabelText("Connecting to Google Drive...")
                progress.setValue(1)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    return False
                
                if not self.drive_service or not self.sheets_service:
                    if not self.init_google_drive_connection():
                        progress.close()
                        return False
                
                if not self.ensure_folders_exist():
                    progress.close()
                    return False
                
                # Step 2: Create folder structure
                progress.setLabelText("Creating folder structure...")
                progress.setValue(2)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Get the target folder (same as invoice location)
                target_folder_id = self.create_folder_structure(client_id, client_name, batch_number)
                if not target_folder_id:
                    progress.close()
                    print("Failed to determine target folder for payment proof")
                    return False
                
                # Step 3: Upload image to Google Drive
                progress.setLabelText("Uploading image to Google Drive...")
                progress.setValue(3)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Upload image to Google Drive
                image_file_id = self.upload_image_to_drive(image_file_path, target_folder_id, client_name, batch_number)
                if not image_file_id:
                    progress.close()
                    print("Failed to upload image to Google Drive")
                    return False
                
                # Step 4: Setting permissions
                progress.setLabelText("Setting image permissions...")
                progress.setValue(4)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Step 5: Finding invoice spreadsheet
                progress.setLabelText("Locating invoice spreadsheet...")
                progress.setValue(5)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Find the invoice spreadsheet with improved search
                existing_file_id, existing_filename, existing_count = self.find_existing_invoice_for_payment_proof(target_folder_id, client_name, batch_number)
                if not existing_file_id:
                    progress.close()
                    print("No invoice spreadsheet found for payment proof insertion")
                    return False
                
                # Step 6: Preparing spreadsheet
                progress.setLabelText("Preparing spreadsheet for image insertion...")
                progress.setValue(6)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Step 7: Inserting image using IMAGE formula
                progress.setLabelText("Inserting image using IMAGE formula...")
                progress.setValue(7)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Insert image using IMAGE formula in K2 cell
                if not self.insert_image_into_invoice_cell(existing_file_id, image_file_id):
                    progress.close()
                    print("Failed to insert image formula")
                    return False
                
                # Step 8: Update payment proof upload date
                progress.setLabelText("Updating payment proof date...")
                progress.setValue(8)
                QCoreApplication.processEvents()
                
                if progress.wasCanceled():
                    progress.close()
                    return False
                
                # Update E14:F14 merged cell with current date
                if not self.update_payment_proof_date(existing_file_id):
                    print("Warning: Failed to update payment proof date")
                
                # Step 9: Complete
                progress.setLabelText("Upload complete!")
                progress.setValue(9)
                QCoreApplication.processEvents()
                
                progress.close()
                
                print(f"Successfully uploaded payment proof and inserted into invoice: {existing_filename}")
                return True
                
            except Exception as e:
                progress.close()
                print(f"Error during upload process: {e}")
                return False
            
        except Exception as e:
            print(f"Error uploading payment proof: {e}")
            return False

    def find_existing_invoice_for_payment_proof(self, target_folder_id, client_name, batch_number):
        """Find existing invoice file using the same logic as sync_to_drive() function"""
        try:
            print(f"Looking for invoice file in folder {target_folder_id} for batch {batch_number}")
            
            # Use the exact same search logic as find_existing_invoice() method
            return self.find_existing_invoice(target_folder_id, client_name, batch_number)
                
        except Exception as e:
            print(f"Error finding existing invoice for payment proof: {e}")
            return (None, None, 0)

    def upload_image_to_drive(self, image_file_path, target_folder_id, client_name, batch_number):
        """Upload image file to Google Drive"""
        try:
            import os
            from googleapiclient.http import MediaFileUpload
            
            # Generate image filename
            image_filename = f"Payment_Proof_{client_name.replace(' ', '_')}_{batch_number}_{os.path.basename(image_file_path)}"
            
            print(f"Uploading image as: {image_filename}")
            
            # Prepare file metadata
            file_metadata = {
                'name': image_filename,
                'parents': [target_folder_id]
            }
            
            # Create media upload
            media = MediaFileUpload(
                image_file_path,
                resumable=True
            )
            
            # Upload file
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name'
            ).execute()
            
            image_file_id = file.get('id')
            uploaded_name = file.get('name')
            
            print(f"Successfully uploaded image: {uploaded_name} (ID: {image_file_id})")
            
            # Make image publicly viewable for embedding in sheets
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.drive_service.permissions().create(
                fileId=image_file_id,
                body=permission
            ).execute()
            
            print(f"Set public permissions for image: {image_file_id}")
            
            return image_file_id
            
        except Exception as e:
            print(f"Error uploading image to Drive: {e}")
            return None

    def insert_image_into_invoice_cell(self, spreadsheet_id, image_file_id):
        """Insert image using IMAGE formula in K2 cell (Google Sheets native approach)"""
        try:
            print(f"Inserting image {image_file_id} using IMAGE formula in K2")
            
            # Get the sheet name
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                print("Could not determine sheet name for image insertion")
                return False
            
            # Use IMAGE formula with publicly accessible URL
            image_url = f"https://drive.google.com/uc?export=view&id={image_file_id}"
            print(f"Using image URL: {image_url}")
            
            # Insert IMAGE formula in K2 cell
            range_name = f"{sheet_name}!K2"
            
            # Use IMAGE function with mode 1 (fit to cell)
            image_formula = f'=IMAGE("{image_url}", 1)'
            
            body = {
                'values': [[image_formula]]
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            print(f"Successfully inserted IMAGE formula into K2: {result.get('updatedCells')} cells updated")
            
            # Merge K2:K24 to make image area larger
            if not self.merge_image_display_area(spreadsheet_id):
                print("Warning: Failed to merge K2:K24 for image display")
            
            return True
            
        except Exception as e:
            print(f"Error inserting image formula: {e}")
            return False

    def merge_image_display_area(self, spreadsheet_id):
        """Merge K2:K24 cells for larger image display area"""
        try:
            print("Merging K2:K24 cells for image display")
            
            sheet_id = 0  # Assuming Invoice is the first sheet
            
            # Merge K2:K24 (column K = index 10, rows 2-24 = indices 1-23)
            requests = [{
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,   # Row 2 (0-based = 1)
                        'endRowIndex': 24,    # Row 24 (exclusive, so 24 means up to row 24)
                        'startColumnIndex': 10,  # Column K (0-based = 10)
                        'endColumnIndex': 11     # Column K (exclusive, so 11 means just K)
                    },
                    'mergeType': 'MERGE_ALL'
                }
            }]
            
            # Execute merge request
            body = {'requests': requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print("Successfully merged K2:K24 cells for image display")
            return True
            
        except Exception as e:
            print(f"Error merging image display area: {e}")
            return False

    def update_payment_proof_date(self, spreadsheet_id):
        """Update E14:F14 merged cell with payment proof upload date"""
        try:
            from datetime import datetime
            
            # Get actual sheet name
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                print("Could not determine sheet name for payment proof date update")
                return False
            
            # Format current date same as other date cells (m/d/yyyy)
            current_date = datetime.now()
            date_formatted = current_date.strftime("%m/%d/%Y")  # e.g., 8/6/2025
            
            # Update E14:F14 merged cell with payment proof date
            range_name = f"{sheet_name}!E14:F14"
            body = {
                'values': [[date_formatted, ""]]  # Second value empty because cells are merged
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            print(f"Updated payment proof date in E14:F14: {date_formatted}")
            return True
            
        except Exception as e:
            print(f"Error updating payment proof date: {e}")
            return False

    def get_payment_proof_upload_dialog(self, client_id, client_name, batch_number):
        """Show file dialog to select payment proof image and upload it"""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            # Show file dialog to select image
            import os
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setNameFilter("Image files (*.png *.jpg *.jpeg *.gif *.bmp)")
            file_dialog.setWindowTitle("Select Payment Proof Image")
            file_dialog.setDirectory(os.path.expanduser("~"))
            
            if file_dialog.exec() == QFileDialog.Accepted:
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    image_file_path = selected_files[0]
                    
                    # Call the upload method with the selected file
                    success = self.upload_payment_proof(client_id, client_name, batch_number, image_file_path)
                    
                    # Show result message and don't return True to avoid double dialog
                    if success:
                        QMessageBox.information(
                            self.parent, 
                            "Upload Successful", 
                            "Payment proof has been successfully uploaded and inserted into the invoice."
                        )
                    else:
                        QMessageBox.warning(
                            self.parent, 
                            "Upload Failed", 
                            "Failed to upload payment proof. Please try again."
                        )
                    
                    # Always return False to prevent dialog from being called again
                    return False
            
            return False
            
        except Exception as e:
            print(f"Error in payment proof upload dialog: {e}")
            QMessageBox.critical(
                self.parent, 
                "Error", 
                f"An error occurred during upload: {str(e)}"
            )
            return False