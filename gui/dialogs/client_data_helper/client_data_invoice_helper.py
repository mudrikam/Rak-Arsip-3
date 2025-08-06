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
            
            return True
            
        except ImportError:
            return False
        except Exception as e:
            return False
    
    def ensure_folders_exist(self):
        """Ensure Rak_Arsip_Database and INVOICE folders exist"""
        if not self.drive_service:
            if not self.init_google_drive_connection():
                return False
        
        try:
            # Cari folder Rak_Arsip_Database
            results = self.drive_service.files().list(
                q="name = 'Rak_Arsip_Database' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            folders = results.get('files', [])
            
            if folders:
                self.rak_arsip_folder_id = folders[0]['id']
            else:
                # Buat folder Rak_Arsip_Database di root
                file_metadata = {
                    'name': 'Rak_Arsip_Database',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
                self.rak_arsip_folder_id = folder.get('id')
            
            # Cari folder INVOICE di dalam Rak_Arsip_Database
            results = self.drive_service.files().list(
                q=f"name = 'INVOICE' and mimeType = 'application/vnd.google-apps.folder' and '{self.rak_arsip_folder_id}' in parents and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            folders = results.get('files', [])
            
            if folders:
                self.invoice_folder_id = folders[0]['id']
            else:
                # Buat folder INVOICE di dalam Rak_Arsip_Database
                file_metadata = {
                    'name': 'INVOICE',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.rak_arsip_folder_id]
                }
                folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
                self.invoice_folder_id = folder.get('id')
            
            return True
            
        except Exception as e:
            return False
    
    def add_sync_button_to_file_urls_tab(self, file_urls_helper):
        """Connect Sync to Drive button in File URLs tab"""
        try:
            # Connect the existing sync button to our sync function
            if hasattr(file_urls_helper, 'sync_drive_btn') and file_urls_helper.sync_drive_btn:
                file_urls_helper.sync_drive_btn.clicked.connect(lambda: self.sync_to_drive(file_urls_helper))
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def sync_to_drive(self, file_urls_helper):
        """Sync current file URLs data to Google Drive as spreadsheet"""
        
        # Cek apakah ada data yang dipilih
        if not file_urls_helper._selected_client_id or not file_urls_helper._selected_batch_number:
            QMessageBox.warning(self.parent, "No Selection", "Please select a client and batch first.")
            return
        
        # Get client info first to determine steps needed
        client_name = file_urls_helper._client_name_label.text().replace("Client: ", "")
        client_id = file_urls_helper._selected_client_id
        batch_number = file_urls_helper._selected_batch_number
        
        # Get actual file count from database (not just filtered URLs)
        actual_file_count = self.db_helper.count_file_client_batch_by_batch_number(batch_number)
        total_files = actual_file_count  # Use actual count from database
        
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
                        self.close_progress()
                        
                        QMessageBox.information(
                            self.parent, 
                            "File Updated", 
                            f"Invoice file for batch {batch_number} has been renamed and data updated.\n\nOld: {existing_filename}\nNew: {new_filename}\n\nTotal records: {total_files}"
                        )
                    else:
                        self.close_progress()
                        QMessageBox.warning(self.parent, "Partial Success", f"File renamed successfully but failed to update sheet data.\n\nFile ID: {renamed_file_id}")
                else:
                    # Count is the same, just update data - now 11 steps in update_invoice_sheet_data_with_progress  
                    self.total_steps += 11  # Clear + Resize + Format + Insert + Special + Merge + Format Copy + Delete + EF Merge + Payment Highlight + External Data Access
                    self.progress_dialog.setMaximum(self.total_steps)
                    
                    # Update sheet data with detailed progress
                    if self.update_invoice_sheet_data_with_progress(existing_file_id, client_id, batch_number, file_urls_helper, is_new_file=False):
                        self.close_progress()
                        
                        QMessageBox.information(
                            self.parent, 
                            "Data Updated", 
                            f"Invoice data for batch {batch_number} has been updated successfully.\n\nFile: {existing_filename}\nTotal records: {existing_count}"
                        )
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
                else:
                    self.close_progress()
                    QMessageBox.warning(self.parent, "Partial Success", f"Invoice file created but failed to populate data.\n\nFile: {invoice_filename}\nFile ID: {new_file_id}")
            
            
        except Exception as e:
            self.close_progress()
            QMessageBox.critical(self.parent, "Sync Error", f"Error during sync: {str(e)}")
    
    def find_invoice_template(self):
        """Find Invoice_Template file in Template folder"""
        try:
            # Search for Template folder
            template_results = self.drive_service.files().list(
                q="name = 'Template' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name)",
                pageSize=10
            ).execute()
            
            template_folders = template_results.get('files', [])
            if not template_folders:
                return None
            
            template_folder_id = template_folders[0]['id']
            
            # Search for Invoice_Template file in Template folder
            invoice_results = self.drive_service.files().list(
                q=f"name = 'Invoice_Template' and '{template_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=10
            ).execute()
            
            invoice_files = invoice_results.get('files', [])
            if not invoice_files:
                return None
            
            template_file_id = invoice_files[0]['id']
            template_mime_type = invoice_files[0]['mimeType']
            
            return template_file_id
            
        except Exception as e:
            return None
    
    def find_existing_invoice(self, target_folder_id, client_name, batch_number):
        """Find existing invoice file for the same client and batch number
        Returns: (file_id, filename, file_count) or (None, None, 0) if not found"""
        try:
            # Clean client name for search pattern
            clean_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_client_name = clean_client_name.replace(' ', '_')

            # Search pattern: Invoice_ClientName_BatchNumber_*
            search_pattern = f"Invoice_{clean_client_name}_{batch_number}_"

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
                        return (file_id, filename, current_count)
                return (None, None, 0)
            else:
                return (None, None, 0)
        except Exception as e:
            return (None, None, 0)
    
    def rename_existing_invoice(self, file_id, new_filename):
        """Rename existing invoice file to reflect updated count"""
        try:
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
            return updated_file_id
        except Exception as e:
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
                    return 0
            return 0
        except Exception as e:
            return 0
    
    def create_folder_structure(self, client_id, client_name, batch_number):
        """Create folder structure: INVOICE/client_id/year/month based on batch creation date"""
        try:
            from datetime import datetime

            # Get batch creation date from database
            batch_created_at = self.db_helper.get_batch_created_date(batch_number, client_id)

            if not batch_created_at:
                return None

            # Parse the database timestamp
            if isinstance(batch_created_at, str):
                try:
                    batch_date = datetime.strptime(batch_created_at, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        batch_date = datetime.strptime(batch_created_at, "%Y-%m-%d")
                    except ValueError:
                        return None
            else:
                batch_date = batch_created_at

            year = batch_date.strftime("%Y")
            month = batch_date.strftime("%B")  # Full month name like "August"

            # Step 1: Check/Create client folder inside INVOICE
            client_folder_id = self.get_or_create_folder(str(client_id), self.invoice_folder_id)
            if not client_folder_id:
                return None

            # Step 2: Check/Create year folder inside client folder
            year_folder_id = self.get_or_create_folder(year, client_folder_id)
            if not year_folder_id:
                return None

            # Step 3: Check/Create month folder inside year folder
            month_folder_id = self.get_or_create_folder(month, year_folder_id)
            if not month_folder_id:
                return None

            return month_folder_id

        except Exception as e:
            return None
    
    def get_or_create_folder(self, folder_name, parent_folder_id):
        """Get existing folder or create new one"""
        try:
            results = self.drive_service.files().list(
                q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                return folder_id
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            return folder_id
        except Exception as e:
            return None
    
    def generate_invoice_filename(self, client_name, batch_number, total_files):
        """Generate invoice filename: Invoice_clientname_batchnumber_YYYY_Month_DD_totalfiles"""
        from datetime import datetime
        current_date = datetime.now()
        year = current_date.strftime("%Y")
        month = current_date.strftime("%B")
        day = current_date.strftime("%d")
        clean_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_client_name = clean_client_name.replace(' ', '_')
        filename = f"Invoice_{clean_client_name}_{batch_number}_{year}_{month}_{day}_{total_files}"
        return filename
    
    def copy_template_to_target(self, template_file_id, target_folder_id, new_filename):
        """Copy template file to target folder with new name"""
        try:
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
            return new_file_id
        except Exception as e:
            return None
    
    def get_invoice_share_link(self, client_id, client_name, batch_number):
        """Get shareable read-only link for invoice file"""
        try:
            if not self.drive_service:
                if not self.init_google_drive_connection():
                    return None
            if not self.ensure_folders_exist():
                return None
            target_folder_id = self.create_folder_structure(client_id, client_name, batch_number)
            if not target_folder_id:
                return None
            existing_file_id, existing_filename, existing_count = self.find_existing_invoice(target_folder_id, client_name, batch_number)
            if not existing_file_id:
                return None
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.drive_service.permissions().create(
                fileId=existing_file_id,
                body=permission,
                fields='id'
            ).execute()
            file_info = self.drive_service.files().get(
                fileId=existing_file_id,
                fields='webViewLink, name'
            ).execute()
            share_link = file_info.get('webViewLink')
            return share_link
        except Exception as e:
            return None

    def update_invoice_sheet_data(self, file_id, client_id, batch_number):
        """Update invoice sheet with batch data starting from B39"""
        try:
            batch_data = self.db_helper.get_all_files_by_batch_and_client_with_details(batch_number, client_id)
            if not batch_data:
                return False
            if not self.clear_invoice_data_range(file_id):
                return False
            required_rows = 40 + len(batch_data)
            if not self.ensure_sheet_size(file_id, required_rows):
                return False
            formatted_data = self.format_data_for_sheet(batch_data, batch_number)
            if not formatted_data:
                return False
            sheet_name = self.get_invoice_sheet_name(file_id)
            if not sheet_name:
                return False
            range_name = f"{sheet_name}!B40:J{39 + len(formatted_data)}"
            body = {
                'values': formatted_data
            }
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            self.merge_filename_cells(file_id, len(formatted_data))
            self.copy_template_row_formatting(file_id, len(formatted_data))
            self.delete_template_row(file_id)
            return True
        except Exception as e:
            return False

    def update_invoice_sheet_data_with_progress(self, file_id, client_id, batch_number, file_urls_helper=None, is_new_file=False):
        """Update invoice sheet with batch data - with detailed progress tracking"""
        try:
            # Retrieve all files data for this batch and client
            batch_data = self.db_helper.get_all_files_by_batch_and_client_with_details(batch_number, client_id)
            # If no data found, abort
            if not batch_data:
                return False

            # Step 1: Clear existing data from B39 downwards
            # This ensures old data is removed before inserting new batch
            if not self.update_progress("Clearing existing invoice data..."):
                return False
            if not self.clear_invoice_data_range(file_id):
                return False

            # Step 2: Ensure the sheet has enough rows for the new data
            # This prevents out-of-bounds errors when inserting
            if not self.update_progress("Ensuring adequate sheet size..."):
                return False
            required_rows = 40 + len(batch_data)
            if not self.ensure_sheet_size(file_id, required_rows):
                return False

            # Step 3: Format data for sheet insertion
            # Converts database records to the format expected by the sheet
            if not self.update_progress("Formatting batch data for insertion..."):
                return False
            formatted_data = self.format_data_for_sheet(batch_data, batch_number)
            if not formatted_data:
                return False

            # Step 4: Insert data starting from B40 (row 40)
            # Data is inserted below the template row (row 39)
            if not self.update_progress("Inserting batch data into spreadsheet..."):
                return False
            sheet_name = self.get_invoice_sheet_name(file_id)
            if not sheet_name:
                return False
            range_name = f"{sheet_name}!B40:J{39 + len(formatted_data)}"
            body = {'values': formatted_data}
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            # Step 5: Update special invoice cells (batch info, client data, payment info)
            if not self.update_progress("Updating special invoice cells..."):
                return False
            if not self.update_invoice_special_cells(file_id, client_id, batch_number, len(batch_data), file_urls_helper, is_new_file):
                return False

            # Step 6: Merge EF cells for client/payment info
            # Ensures proper formatting for merged cells
            if not self.update_progress("Merging client information cells..."):
                return False
            if not self.merge_ef_cells(file_id):
                return False

            # Step 7: Highlight payment method cell if available
            # Visually marks the selected payment method
            if not self.update_progress("Applying payment method highlighting..."):
                return False
            if file_urls_helper:
                payment_method = file_urls_helper.get_payment_method()
                if payment_method and payment_method != "":
                    self.highlight_payment_method_cell(file_id, payment_method)

            # Step 8: Merge filename cells (C-D-E) for each data row
            if not self.update_progress("Merging filename cells..."):
                return False
            if not self.merge_filename_cells(file_id, len(formatted_data)):
                return False

            # Step 9: Copy formatting from template row (row 39) to all data rows
            if not self.update_progress("Copying template formatting..."):
                return False
            if not self.copy_template_row_formatting(file_id, len(formatted_data)):
                return False

            # Step 10: Delete template row (row 39) after all data and formatting is complete
            if not self.update_progress("Cleaning up template row..."):
                return False
            if not self.delete_template_row(file_id):
                return False

            # All steps completed successfully
            return True

        except Exception:
            # If any error occurs, return False to indicate failure
            return False

    def update_invoice_special_cells(self, spreadsheet_id, client_id, batch_number, total_files, file_urls_helper=None, is_new_file=False):
        """Update special invoice cells with batch info, client data, and payment information"""
        try:
            from datetime import datetime
            # Get the sheet name for cell updates
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                return False
            # Retrieve client name from database
            client_name = ""
            try:
                client_data = self.db_helper.get_client_by_id(client_id)
                if client_data:
                    client_name = client_data.get('client_name', '')
            except:
                client_name = "Unknown Client"
            # Prepare cell updates for batch info, client, and payment
            cell_updates = []
            current_date = datetime.now()
            date_format = current_date.strftime("%Y%b%d")
            c4_value = f"{batch_number}/{date_format}/{total_files}"
            cell_updates.append({
                'range': f"{sheet_name}!C4",
                'values': [[c4_value]]
            })
            cell_updates.append({
                'range': f"{sheet_name}!E9:F9",
                'values': [[client_name, ""]]
            })
            if is_new_file:
                # Add creation date for new files
                batch_creation_date = self.db_helper.get_batch_created_date(batch_number, client_id)
                if batch_creation_date:
                    from datetime import datetime
                    created_datetime = datetime.fromisoformat(batch_creation_date.replace("Z", "+00:00") if batch_creation_date.endswith("Z") else batch_creation_date)
                    creation_date = created_datetime.strftime("%m/%d/%Y")
                else:
                    raise ValueError(f"Batch creation date not found for batch {batch_number} and client {client_id}")
                cell_updates.append({
                    'range': f"{sheet_name}!E10:F10",
                    'values': [[creation_date, ""]]
                })
            if file_urls_helper:
                payment_status = file_urls_helper.get_payment_status()
                payment_method = file_urls_helper.get_payment_method()
                if payment_status:
                    cell_updates.append({
                        'range': f"{sheet_name}!E15:F15",
                        'values': [[payment_status, ""]]
                    })
                if payment_status == "Paid":
                    payment_date = current_date.strftime("%m/%d/%Y")
                    cell_updates.append({
                        'range': f"{sheet_name}!E16:F16",
                        'values': [[payment_date, ""]]
                    })
            # Apply all prepared cell updates
            if cell_updates:
                for update in cell_updates:
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=update['range'],
                        valueInputOption='USER_ENTERED',
                        body={'values': update['values']}
                    ).execute()
            # Highlight payment method cell if available
            if file_urls_helper:
                payment_method = file_urls_helper.get_payment_method()
                if payment_method and payment_method != "":
                    self.highlight_payment_method_cell(spreadsheet_id, payment_method)
            return True
        except Exception:
            return False

    def highlight_payment_method_cell(self, spreadsheet_id, payment_method):
        """Highlight selected payment method cell in sheet by clearing all and setting green background."""
        try:
            # Mapping of payment methods to their corresponding cell references in the sheet
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

            sheet_id = 0  # Assumes the Invoice sheet is the first sheet (sheetId=0)
            import re

            requests = []

            # Clear background color for all payment method cells to reset their state
            for method, cell_ref in payment_cell_map.items():
                match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                if match:
                    col_letters = match.group(1)
                    row_number = int(match.group(2))
                    # Convert column letters (e.g., 'C') to zero-based column index
                    col_index = 0
                    for char in col_letters:
                        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
                    col_index -= 1
                    row_index = row_number - 1
                    # Add request to clear background color (set to white)
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

            # Highlight the selected payment method cell with a green background
            target_cell = payment_cell_map.get(payment_method)
            if target_cell:
                match = re.match(r'([A-Z]+)(\d+)', target_cell)
                if match:
                    col_letters = match.group(1)
                    row_number = int(match.group(2))
                    col_index = 0
                    for char in col_letters:
                        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
                    col_index -= 1
                    row_index = row_number - 1
                    # Add request to set green background color for the selected cell
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

            # Execute all formatting requests in a single batch update
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()

            return True
        except Exception as e:
            return False
            
        except Exception as e:
            print(f"Error highlighting payment method cell: {e}")
            return False

    def merge_ef_cells(self, spreadsheet_id):
        """Merge E-F cells for rows 9, 10, 14, 15, 16."""
        try:
            sheet_id = 0  # Assumes Invoice is the first sheet

            # 0-based row indices for rows 9, 10, 14, 15, 16
            merge_rows = [8, 9, 13, 14, 15]

            requests = []
            for row_index in merge_rows:
                # Prepare merge request for columns E (4) to F (5), exclusive end at 6
                merge_request = {
                    'mergeCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': row_index,
                            'endRowIndex': row_index + 1,
                            'startColumnIndex': 4,
                            'endColumnIndex': 6
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                }
                requests.append(merge_request)

            # Send all merge requests in a single batch update
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()

            return True

        except Exception as e:
            return False

    def get_invoice_sheet_name(self, spreadsheet_id):
        """Get invoice sheet name or first sheet if not found."""
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='sheets.properties.title'
            ).execute()

            # Search for a sheet named 'Invoice'
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == 'Invoice':
                    return 'Invoice'

            # If 'Invoice' sheet is not found, return the first sheet's name if available
            if spreadsheet.get('sheets'):
                first_sheet_name = spreadsheet['sheets'][0]['properties']['title']
                return first_sheet_name

            # Return None if no sheets are found
            return None

        except Exception:
            # Return None if an error occurs while retrieving the sheet name
            return None

    def clear_invoice_data_range(self, spreadsheet_id):
        """Clear invoice data from B40 downwards, preserving template row 39"""
        try:
            # Get the actual sheet name to ensure the correct range is targeted
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                # Sheet name could not be determined, abort clearing
                return False

            # Define the range to clear: B40:J1000 (rows below template row 39)
            clear_range = f"{sheet_name}!B40:J1000"

            # Clear the specified range in the sheet, leaving template row untouched
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=clear_range
            ).execute()

            return True

        except Exception:
            # If any error occurs during clearing, return False
            return False

    def format_data_for_sheet(self, batch_data, batch_number):
        """Format batch data for Google Sheets insertion"""
        try:
            # Prepare rows for sheet insertion, merging filename across C-D-E columns
            formatted_rows = []
            for i, item in enumerate(batch_data, 1):
                # item: (file_id, filename, date, root, path, status_id, category_id, subcategory_id, category_name, subcategory_name, url_value, provider_name, price_value, currency)
                filename = item[1] or ""
                date = item[2] or ""
                category_name = item[8] or ""
                subcategory_name = item[9] or ""
                url_value = item[10] or ""
                price_value = item[12]

                # Convert price to string, handle integer/float
                price = ""
                if price_value is not None:
                    if isinstance(price_value, (int, float)) and price_value == int(price_value):
                        price = str(int(price_value))
                    else:
                        price = str(price_value)

                # Row structure: [No, Filename(C), "", "", Category, Subcategory, Batch, URL, Price]
                # Filename will be merged across C-D-E columns
                row = [
                    i,                    # B: No
                    filename,             # C: Filename (merged C-D-E)
                    "",                   # D: (merged)
                    "",                   # E: (merged)
                    category_name,        # F: Category
                    subcategory_name,     # G: Subcategory
                    batch_number,         # H: Batch Number
                    url_value,            # I: URL
                    price                 # J: Price
                ]
                formatted_rows.append(row)
            return formatted_rows
        except Exception as e:
            # Return empty list if formatting fails
            return []

    def merge_filename_cells(self, spreadsheet_id, data_rows_count):
        """Merge C-D-E cells for filename in each data row"""
        try:
            # Prepare batch requests to merge columns C, D, and E for each data row starting from row 40
            requests = []
            for i in range(data_rows_count):
                row_index = 39 + i  # Row 40 is index 39
                merge_request = {
                    'mergeCells': {
                        'range': {
                            'sheetId': 0,  # Assumes Invoice is the first sheet
                            'startRowIndex': row_index,
                            'endRowIndex': row_index + 1,
                            'startColumnIndex': 2,  # Column C
                            'endColumnIndex': 5     # Up to column E (exclusive)
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                }
                requests.append(merge_request)
            # Execute all merge requests in a single batch update
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
            return True
        except Exception:
            return False

    def copy_template_row_formatting(self, spreadsheet_id, data_rows_count):
        """Copy template row formatting to data rows"""
        try:
            # If there are no data rows, nothing to format
            if data_rows_count == 0:
                return True

            # Prepare batch requests to copy formatting from template row (row 39, B-J)
            requests = []
            source_range = {
                'sheetId': 0,           # Invoice sheet assumed as first sheet
                'startRowIndex': 38,    # Row 39 (0-based)
                'endRowIndex': 39,
                'startColumnIndex': 1,  # Column B
                'endColumnIndex': 10    # Up to column J (exclusive)
            }

            # For each data row, copy formatting from template row
            for i in range(data_rows_count):
                target_row_index = 39 + i  # Data rows start at row 40 (0-based 39)
                target_range = {
                    'sheetId': 0,
                    'startRowIndex': target_row_index,
                    'endRowIndex': target_row_index + 1,
                    'startColumnIndex': 1,
                    'endColumnIndex': 10
                }
                # Add copyPaste request for formatting only
                copy_format_request = {
                    'copyPaste': {
                        'source': source_range,
                        'destination': target_range,
                        'pasteType': 'PASTE_FORMAT',
                        'pasteOrientation': 'NORMAL'
                    }
                }
                requests.append(copy_format_request)

            # Execute all formatting requests in a single batch update
            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()

            return True

        except Exception:
            # Return False if formatting fails
            return False

    def delete_template_row(self, spreadsheet_id):
        """Delete template row 39 after data insertion"""
        try:
            # Prepare a request to delete row 39 (0-indexed = 38) from the Invoice sheet
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': 0,  # Assumes Invoice is the first sheet
                        'dimension': 'ROWS',
                        'startIndex': 38,  # Row 39 (0-indexed)
                        'endIndex': 39     # Exclusive, so only row 39
                    }
                }
            }]
            # Execute the delete request to remove the template row
            body = {'requests': requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return True
        except Exception:
            # Return False if the row could not be deleted
            return False

    def ensure_sheet_size(self, spreadsheet_id, required_rows, required_cols=11):
        """Ensure Invoice sheet has enough rows and columns"""
        try:
            # Retrieve current sheet properties for the Invoice sheet
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='sheets.properties'
            ).execute()
            # Find the Invoice sheet by name, or use the first sheet if not found
            invoice_sheet = None
            for sheet in spreadsheet.get('sheets', []):
                sheet_title = sheet['properties']['title']
                if sheet_title == 'Invoice':
                    invoice_sheet = sheet
                    break
            if not invoice_sheet:
                if spreadsheet.get('sheets'):
                    invoice_sheet = spreadsheet['sheets'][0]
                else:
                    # No sheets found in the spreadsheet
                    return False
            sheet_id = invoice_sheet['properties']['sheetId']
            current_rows = invoice_sheet['properties']['gridProperties']['rowCount']
            current_cols = invoice_sheet['properties']['gridProperties']['columnCount']
            # Determine if the sheet needs to be expanded
            needs_expansion = False
            new_rows = current_rows
            new_cols = current_cols
            if current_rows < required_rows:
                new_rows = required_rows + 10  # Add buffer rows
                needs_expansion = True
            if current_cols < required_cols:
                new_cols = required_cols + 2  # Add buffer columns
                needs_expansion = True
            if needs_expansion:
                # Prepare a request to update the sheet size
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
                # Execute the request to resize the sheet
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
            return True
        except Exception:
            # Return False if the sheet could not be resized
            return False

    def upload_payment_proof(self, client_id, client_name, batch_number, image_file_path):
        """Upload payment proof image to invoice folder and insert into K2:K24 cell"""
        try:
            # Show progress dialog with detailed steps for user feedback
            from PySide6.QtWidgets import QProgressDialog, QMessageBox
            from PySide6.QtCore import QCoreApplication

            progress = QProgressDialog("Preparing upload...", "Cancel", 0, 9, self.parent)
            progress.setWindowTitle("Upload Payment Proof")
            progress.setModal(True)
            progress.setValue(0)
            progress.show()
            QCoreApplication.processEvents()

            try:
                # Step 1: Connect to Google Drive
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

                # Step 2: Create or get the correct folder structure for the invoice
                progress.setLabelText("Creating folder structure...")
                progress.setValue(2)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False
                target_folder_id = self.create_folder_structure(client_id, client_name, batch_number)
                if not target_folder_id:
                    progress.close()
                    return False

                # Step 3: Upload the image file to Google Drive
                progress.setLabelText("Uploading image to Google Drive...")
                progress.setValue(3)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False
                image_file_id = self.upload_image_to_drive(image_file_path, target_folder_id, client_name, batch_number)
                if not image_file_id:
                    progress.close()
                    return False

                # Step 4: Set image permissions to public for embedding
                progress.setLabelText("Setting image permissions...")
                progress.setValue(4)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False

                # Step 5: Find the invoice spreadsheet file for this batch and client
                progress.setLabelText("Locating invoice spreadsheet...")
                progress.setValue(5)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False
                existing_file_id, existing_filename, existing_count = self.find_existing_invoice_for_payment_proof(
                    target_folder_id, client_name, batch_number
                )
                if not existing_file_id:
                    progress.close()
                    return False

                # Step 6: Prepare spreadsheet for image insertion
                progress.setLabelText("Preparing spreadsheet for image insertion...")
                progress.setValue(6)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False

                # Step 7: Insert the image into K2 cell using IMAGE formula
                progress.setLabelText("Inserting image using IMAGE formula...")
                progress.setValue(7)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False
                if not self.insert_image_into_invoice_cell(existing_file_id, image_file_id):
                    progress.close()
                    return False

                # Step 8: Update payment proof upload date in E14:F14
                progress.setLabelText("Updating payment proof date...")
                progress.setValue(8)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    return False
                self.update_payment_proof_date(existing_file_id)

                # Step 9: Complete the process
                progress.setLabelText("Upload complete!")
                progress.setValue(9)
                QCoreApplication.processEvents()
                progress.close()
                return True

            except Exception:
                progress.close()
                return False

        except Exception:
            return False

    def find_existing_invoice_for_payment_proof(self, target_folder_id, client_name, batch_number):
        """Find existing invoice file for payment proof upload."""
        try:
            # Use the same logic as find_existing_invoice to locate the invoice file in the target folder
            return self.find_existing_invoice(target_folder_id, client_name, batch_number)
        except Exception:
            # Return (None, None, 0) if any error occurs during the search
            return (None, None, 0)

    def upload_image_to_drive(self, image_file_path, target_folder_id, client_name, batch_number):
        """Upload payment proof image to Google Drive and set public permissions"""
        try:
            import os
            from googleapiclient.http import MediaFileUpload

            # Generate a unique filename for the payment proof image
            image_filename = f"Payment_Proof_{client_name.replace(' ', '_')}_{batch_number}_{os.path.basename(image_file_path)}"

            # Prepare metadata for the file upload
            file_metadata = {
                'name': image_filename,
                'parents': [target_folder_id]
            }

            # Create a media upload object for the image file
            media = MediaFileUpload(
                image_file_path,
                resumable=True
            )

            # Upload the image file to Google Drive
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name'
            ).execute()

            image_file_id = file.get('id')

            # Set the uploaded image to be publicly readable for embedding in Google Sheets
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.drive_service.permissions().create(
                fileId=image_file_id,
                body=permission
            ).execute()

            return image_file_id

        except Exception as e:
            return None

    def insert_image_into_invoice_cell(self, spreadsheet_id, image_file_id):
        """Insert payment proof image into K2 cell using IMAGE formula"""
        try:
            # Get the sheet name for the invoice
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                # Abort if sheet name cannot be determined
                return False

            # Construct the public image URL for Google Drive
            image_url = f"https://drive.google.com/uc?export=view&id={image_file_id}"

            # Prepare the IMAGE formula for Google Sheets (mode 1: fit to cell)
            image_formula = f'=IMAGE("{image_url}", 1)'

            # Define the target cell range (K2) for image insertion
            range_name = f"{sheet_name}!K2"
            body = {
                'values': [[image_formula]]
            }

            # Update the cell with the IMAGE formula
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            # Merge K2:K24 to provide a larger display area for the image
            self.merge_image_display_area(spreadsheet_id)

            return True

        except Exception:
            # Return False if any error occurs during image insertion
            return False

    def merge_image_display_area(self, spreadsheet_id):
        """Merge K2:K24 cells for image display"""
        try:
            # Merge K2:K24 (column K = index 10, rows 2-24 = indices 1-23) for a larger image area
            sheet_id = 0  # Assumes Invoice is the first sheet

            requests = [{
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,   # Row 2 (0-based)
                        'endRowIndex': 24,    # Row 24 (exclusive)
                        'startColumnIndex': 10,  # Column K (0-based)
                        'endColumnIndex': 11     # Only column K
                    },
                    'mergeType': 'MERGE_ALL'
                }
            }]

            # Send the merge request to Google Sheets API
            body = {'requests': requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            return True

        except Exception:
            # Return False if merging fails
            return False

    def update_payment_proof_date(self, spreadsheet_id):
        """Update payment proof upload date in E14:F14 cell"""
        try:
            from datetime import datetime

            # Get the sheet name for the invoice
            sheet_name = self.get_invoice_sheet_name(spreadsheet_id)
            if not sheet_name:
                # Abort if sheet name cannot be determined
                return False

            # Format the current date as m/d/yyyy for consistency with other date cells
            current_date = datetime.now()
            date_formatted = current_date.strftime("%m/%d/%Y")

            # Prepare the range and values for updating the merged E14:F14 cell
            range_name = f"{sheet_name}!E14:F14"
            body = {
                'values': [[date_formatted, ""]]
            }

            # Update the cell with the payment proof upload date
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            return True

        except Exception:
            # Return False if the update fails
            return False

    def get_payment_proof_upload_dialog(self, client_id, client_name, batch_number):
        """Show dialog to select and upload payment proof image"""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox

            # Open a file dialog for the user to select an image file as payment proof
            import os
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setNameFilter("Image files (*.png *.jpg *.jpeg *.gif *.bmp)")
            file_dialog.setWindowTitle("Select Payment Proof Image")
            file_dialog.setDirectory(os.path.expanduser("~"))

            # If the user selects a file and confirms
            if file_dialog.exec() == QFileDialog.Accepted:
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    image_file_path = selected_files[0]

                    # Attempt to upload the selected image as payment proof
                    success = self.upload_payment_proof(client_id, client_name, batch_number, image_file_path)

                    # Show a message box indicating the result of the upload
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

                    # Always return False to prevent the dialog from being called again
                    return False

            # Return False if no file was selected or dialog was cancelled
            return False

        except Exception as e:
            # Show a critical error message if an exception occurs during the upload process
            QMessageBox.critical(
                self.parent,
                "Error",
                f"An error occurred during upload: {str(e)}"
            )
            return False