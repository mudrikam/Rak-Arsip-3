from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, QLabel, 
    QPushButton, QLineEdit, QSpinBox, QMessageBox, QFileDialog
)
import qtawesome as qta
from pathlib import Path
import json
import shutil
import os
import tempfile
from dotenv import load_dotenv, set_key


class PreferencesActionsHelper:
    """Helper class for Action Options tab in Preferences window"""
    
    def __init__(self, parent, config_manager, db_config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.db_config_manager = db_config_manager
        
    def create_action_options_tab(self):
        """Create and return the Action Options tab widget"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Action Options")
        group_layout = QVBoxLayout(group)
        
        self.parent.date_check = QCheckBox("Date - Add date folders automatically")
        self.parent.date_check.setIcon(qta.icon("fa6s.calendar"))
        
        self.parent.markdown_check = QCheckBox("Markdown - Generate markdown files")
        self.parent.markdown_check.setIcon(qta.icon("fa6b.markdown"))
        
        self.parent.open_explorer_check = QCheckBox("Open Explorer - Open folder after creation")
        self.parent.open_explorer_check.setIcon(qta.icon("fa6s.folder-open"))
        
        self.parent.sanitize_name_check = QCheckBox("Sanitize Name - Clean file names automatically")
        self.parent.sanitize_name_check.setIcon(qta.icon("fa6s.broom"))
        
        group_layout.addWidget(self.parent.date_check)
        group_layout.addWidget(self.parent.markdown_check)
        group_layout.addWidget(self.parent.open_explorer_check)
        group_layout.addWidget(self.parent.sanitize_name_check)
        
        # Operational percentage option
        opr_row = QHBoxLayout()
        self.parent.operational_percentage_label = QLabel("Operational Percentage (Opr):")
        self.parent.operational_percentage_spin = QSpinBox()
        self.parent.operational_percentage_spin.setMinimum(0)
        self.parent.operational_percentage_spin.setMaximum(100)
        self.parent.operational_percentage_spin.setSuffix(" %")
        opr_row.addWidget(self.parent.operational_percentage_label)
        opr_row.addWidget(self.parent.operational_percentage_spin)
        group_layout.addLayout(opr_row)
        
        group.setLayout(group_layout)
        layout.addWidget(group)

        gemini_group = QGroupBox("Gemini API Key")
        gemini_layout = QVBoxLayout(gemini_group)
        gemini_row = QHBoxLayout()
        self.parent.gemini_api_label = QLabel("API Key:")
        self.parent.gemini_api_edit = QLineEdit()
        self.parent.gemini_api_edit.setEchoMode(QLineEdit.Password)
        self.parent.gemini_api_edit.setPlaceholderText("Enter Gemini API Key")
        self.parent.gemini_api_edit.setMinimumWidth(300)
        self.parent.gemini_api_edit.setText(self._get_gemini_api_key())
        self.parent.gemini_api_show_btn = QPushButton(qta.icon("fa6s.eye"), "")
        self.parent.gemini_api_show_btn.setCheckable(True)
        self.parent.gemini_api_show_btn.setToolTip("Show/Hide API Key")
        self.parent.gemini_api_show_btn.setFixedWidth(32)
        self.parent.gemini_api_show_btn.clicked.connect(self.toggle_gemini_api_visibility)
        gemini_row.addWidget(self.parent.gemini_api_label)
        gemini_row.addWidget(self.parent.gemini_api_edit)
        gemini_row.addWidget(self.parent.gemini_api_show_btn)
        gemini_layout.addLayout(gemini_row)

        self.parent.gemini_test_btn = QPushButton("Test Gemini API", self.parent)
        self.parent.gemini_test_btn.setIcon(qta.icon("fa6s.plug-circle-check"))
        self.parent.gemini_test_btn.clicked.connect(self.test_gemini_api)
        self.parent.gemini_status_label = QLabel("")
        self.parent.gemini_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        gemini_status_row = QHBoxLayout()
        gemini_status_row.addWidget(self.parent.gemini_test_btn)
        gemini_status_row.addWidget(self.parent.gemini_status_label)
        gemini_status_row.addStretch()
        gemini_layout.addLayout(gemini_status_row)
        gemini_group.setLayout(gemini_layout)
        layout.addWidget(gemini_group)

        # Google Drive API section
        gdrive_group = QGroupBox("Google Drive API")
        gdrive_layout = QVBoxLayout(gdrive_group)
        
        # Credentials file path
        gdrive_path_row = QHBoxLayout()
        self.parent.gdrive_path_label = QLabel("Credentials JSON:")
        self.parent.gdrive_path_edit = QLineEdit()
        self.parent.gdrive_path_edit.setPlaceholderText("Path to Google Drive credentials JSON file")
        self.parent.gdrive_path_edit.setMinimumWidth(300)
        self.parent.gdrive_path_edit.setReadOnly(True)
        self.parent.gdrive_open_btn = QPushButton("Open")
        self.parent.gdrive_open_btn.setIcon(qta.icon("fa6s.folder-open"))
        self.parent.gdrive_open_btn.clicked.connect(self.open_gdrive_credentials)
        
        gdrive_path_row.addWidget(self.parent.gdrive_path_label)
        gdrive_path_row.addWidget(self.parent.gdrive_path_edit)
        gdrive_path_row.addWidget(self.parent.gdrive_open_btn)
        gdrive_layout.addLayout(gdrive_path_row)
        
        # Test button and status
        gdrive_test_row = QHBoxLayout()
        self.parent.gdrive_test_btn = QPushButton("Test Connection")
        self.parent.gdrive_test_btn.setIcon(qta.icon("fa6s.plug-circle-check"))
        self.parent.gdrive_test_btn.clicked.connect(self.test_gdrive_connection)
        self.parent.gdrive_status_label = QLabel("")
        self.parent.gdrive_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        
        gdrive_test_row.addWidget(self.parent.gdrive_test_btn)
        gdrive_test_row.addWidget(self.parent.gdrive_status_label)
        gdrive_test_row.addStretch()
        gdrive_layout.addLayout(gdrive_test_row)
        
        gdrive_group.setLayout(gdrive_layout)
        layout.addWidget(gdrive_group)

        # Cache Management section
        cache_group = QGroupBox("Cache Management")
        cache_layout = QVBoxLayout(cache_group)
        
        cache_info_label = QLabel("Clear cached data to free up disk space")
        cache_info_label.setStyleSheet("color: #666; font-style: italic;")
        cache_layout.addWidget(cache_info_label)
        
        cache_buttons_row = QHBoxLayout()
        
        self.parent.clear_thumbnail_cache_btn = QPushButton("Clear Thumbnail Cache")
        self.parent.clear_thumbnail_cache_btn.setIcon(qta.icon("fa6s.image"))
        self.parent.clear_thumbnail_cache_btn.clicked.connect(self.clear_thumbnail_cache)
        
        self.parent.clear_database_cache_btn = QPushButton("Clear Database Cache")
        self.parent.clear_database_cache_btn.setIcon(qta.icon("fa6s.database"))
        self.parent.clear_database_cache_btn.clicked.connect(self.clear_database_cache)
        
        self.parent.clear_all_cache_btn = QPushButton("Clear All Cache")
        self.parent.clear_all_cache_btn.setIcon(qta.icon("fa6s.trash-can"))
        self.parent.clear_all_cache_btn.clicked.connect(self.clear_all_cache)
        
        cache_buttons_row.addWidget(self.parent.clear_thumbnail_cache_btn)
        cache_buttons_row.addWidget(self.parent.clear_database_cache_btn)
        cache_buttons_row.addWidget(self.parent.clear_all_cache_btn)
        cache_layout.addLayout(cache_buttons_row)
        
        self.parent.cache_status_label = QLabel("")
        self.parent.cache_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        cache_layout.addWidget(self.parent.cache_status_label)
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        layout.addStretch()
        return tab
        
    def toggle_gemini_api_visibility(self):
        """Toggle Gemini API key visibility"""
        if self.parent.gemini_api_show_btn.isChecked():
            self.parent.gemini_api_edit.setEchoMode(QLineEdit.Normal)
            self.parent.gemini_api_show_btn.setIcon(qta.icon("fa6s.eye-slash"))
        else:
            self.parent.gemini_api_edit.setEchoMode(QLineEdit.Password)
            self.parent.gemini_api_show_btn.setIcon(qta.icon("fa6s.eye"))

    def _get_gemini_api_key(self):
        """Get Gemini API key from environment variables"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            env_path = basedir / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            return os.getenv("GEMINI_API_KEY", "")
        except Exception:
            pass
        return ""

    def _get_gdrive_credentials_path(self):
        """Get Google Drive service account credentials path from environment variables"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            env_path = basedir / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "")
            if path:
                path = path.strip("'\"")
            return path
        except Exception:
            pass
        return ""

    def _set_gemini_api_key(self, api_key):
        """Set Gemini API key in .env file"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            env_path = basedir / ".env"
            set_key(str(env_path), "GEMINI_API_KEY", api_key)
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to save Gemini API key: {e}")

    def _set_gdrive_credentials_path(self, credentials_path):
        """Set Google Drive credentials path in .env file"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            env_path = basedir / ".env"
            set_key(str(env_path), "GOOGLE_DRIVE_CREDENTIALS_PATH", credentials_path)
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to save Google Drive credentials path: {e}")

    def test_gemini_api(self):
        """Test Gemini API connection"""
        api_key = self.parent.gemini_api_edit.text().strip()
        if not api_key:
            self.parent.gemini_status_label.setText("API Key is empty.")
            self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            return
        try:
            import google.genai as genai
            from google.genai import types
            
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            print(f"DEBUG: Testing with model: {model}")
            print(f"DEBUG: API Key: {api_key[:20]}...{api_key[-5:]}")
            
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=["Say hello"]
            )
            if hasattr(response, "text") and response.text:
                # API responded successfully — save key to .env so other parts use it
                try:
                    self._set_gemini_api_key(api_key)
                    # reload env to ensure current process sees the new value
                    basedir = Path(__file__).parent.parent.parent.parent
                    env_path = basedir / ".env"
                    if env_path.exists():
                        load_dotenv(env_path, override=True)
                    self.parent.gemini_status_label.setText("Gemini API is active and saved to .env")
                    self.parent.gemini_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
                except Exception as save_err:
                    self.parent.gemini_status_label.setText("Gemini active (not saved)")
                    self.parent.gemini_status_label.setStyleSheet("color: #f57c00; font-weight: bold;")
                    QMessageBox.warning(self.parent, "Warning", f"API is active but failed to save to .env: {save_err}")
            else:
                self.parent.gemini_status_label.setText("No response from Gemini API.")
                self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except ImportError:
            self.parent.gemini_status_label.setText("google-genai not installed.")
            self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except Exception as e:
            self.parent.gemini_status_label.setText(f"Error: {e}")
            self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def open_gdrive_credentials(self):
        """Open file dialog to select Google Drive credentials JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Google Drive Credentials JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.parent.gdrive_path_edit.setText(file_path)
            self.parent.gdrive_status_label.setText("File selected. Click Test to validate.")
            self.parent.gdrive_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
            # Save path to configuration
            self._set_gdrive_credentials_path(file_path)

    def test_gdrive_connection(self):
        """Test Google Drive API connection and copy credentials if valid"""
        json_path = self.parent.gdrive_path_edit.text().strip()
        
        if not json_path:
            self.parent.gdrive_status_label.setText("Please select a credentials JSON file first.")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            return
            
        if not Path(json_path).exists():
            self.parent.gdrive_status_label.setText("Selected file does not exist.")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            return
        
        try:
            # Test the credentials
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Load and validate JSON structure
            with open(json_path, 'r', encoding='utf-8') as f:
                credentials_data = json.load(f)
            
            # Check if it's a service account file
            if 'type' not in credentials_data or credentials_data['type'] != 'service_account':
                self.parent.gdrive_status_label.setText("Invalid service account JSON file.")
                self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                return
            
            # Create credentials and test connection
            scopes = ['https://www.googleapis.com/auth/drive.metadata.readonly']
            credentials = service_account.Credentials.from_service_account_file(
                json_path, scopes=scopes
            )
            
            service = build('drive', 'v3', credentials=credentials)
            
            # Test by listing files (limit to 1 to minimize API usage)
            results = service.files().list(pageSize=1, fields="files(id, name)").execute()
            
            # If we get here, the credentials are valid
            self._copy_credentials_to_config(json_path)
            self.parent.gdrive_status_label.setText("Connection successful! Credentials copied to configs/")
            self.parent.gdrive_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            
        except ImportError:
            self.parent.gdrive_status_label.setText("Google API libraries not installed.")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except FileNotFoundError:
            self.parent.gdrive_status_label.setText("Credentials file not found.")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except json.JSONDecodeError:
            self.parent.gdrive_status_label.setText("Invalid JSON file format.")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except Exception as e:
            self.parent.gdrive_status_label.setText(f"Connection failed: {str(e)[:50]}...")
            self.parent.gdrive_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def _copy_credentials_to_config(self, source_path):
        """Copy valid credentials file to configs folder and save path to .env"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            configs_dir = basedir / "configs"
            configs_dir.mkdir(exist_ok=True)
            
            target_path = configs_dir / "credentials_config.json"
            
            import time
            max_retries = 3
            for retry in range(max_retries):
                try:
                    with open(source_path, 'r', encoding='utf-8') as src:
                        content = src.read()
                    with open(target_path, 'w', encoding='utf-8') as dst:
                        dst.write(content)
                    break
                except PermissionError:
                    if retry < max_retries - 1:
                        time.sleep(0.5)
                    else:
                        raise
            
            self._set_gdrive_credentials_path(str(target_path))
            self.parent.gdrive_path_edit.setText(str(target_path))
            
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to copy credentials: {e}")

    def _get_cache_path(self, cache_key):
        """Get cache path from db config"""
        try:
            cache_path = self.db_config_manager.get(f"system_caching.{cache_key}")
            if cache_path:
                temp_dir = Path(tempfile.gettempdir())
                return temp_dir / cache_path
            return None
        except Exception:
            return None

    def _clear_cache_directory(self, cache_path):
        """Clear a cache directory and return number of files deleted"""
        if not cache_path or not cache_path.exists():
            return 0
        
        files_deleted = 0
        try:
            for item in cache_path.iterdir():
                if item.is_file():
                    item.unlink()
                    files_deleted += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    files_deleted += 1
        except Exception as e:
            raise Exception(f"Failed to clear cache: {e}")
        
        return files_deleted

    def clear_thumbnail_cache(self):
        """Clear thumbnail cache"""
        try:
            cache_path = self._get_cache_path("projects_thumbnail_cache")
            if not cache_path:
                self.parent.cache_status_label.setText("Thumbnail cache path not configured")
                self.parent.cache_status_label.setStyleSheet("color: #f57c00; font-weight: bold;")
                return
            
            files_deleted = self._clear_cache_directory(cache_path)
            self.parent.cache_status_label.setText(f"Thumbnail cache cleared ({files_deleted} items)")
            self.parent.cache_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            
        except Exception as e:
            self.parent.cache_status_label.setText(f"Error: {str(e)[:50]}...")
            self.parent.cache_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def clear_database_cache(self):
        """Clear database cache"""
        try:
            cache_path = self._get_cache_path("database_cache")
            if not cache_path:
                self.parent.cache_status_label.setText("Database cache path not configured")
                self.parent.cache_status_label.setStyleSheet("color: #f57c00; font-weight: bold;")
                return
            
            files_deleted = self._clear_cache_directory(cache_path)
            self.parent.cache_status_label.setText(f"Database cache cleared ({files_deleted} items)")
            self.parent.cache_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            
        except Exception as e:
            self.parent.cache_status_label.setText(f"Error: {str(e)[:50]}...")
            self.parent.cache_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def clear_all_cache(self):
        """Clear all cache directories"""
        try:
            total_deleted = 0
            
            thumbnail_path = self._get_cache_path("projects_thumbnail_cache")
            if thumbnail_path:
                total_deleted += self._clear_cache_directory(thumbnail_path)
            
            database_path = self._get_cache_path("database_cache")
            if database_path:
                total_deleted += self._clear_cache_directory(database_path)
            
            if total_deleted > 0:
                self.parent.cache_status_label.setText(f"All cache cleared ({total_deleted} items)")
                self.parent.cache_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            else:
                self.parent.cache_status_label.setText("No cache items found")
                self.parent.cache_status_label.setStyleSheet("color: #f57c00; font-weight: bold;")
                
        except Exception as e:
            self.parent.cache_status_label.setText(f"Error: {str(e)[:50]}...")
            self.parent.cache_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def load_action_options_data(self):
        """Load action options data from configuration"""
        try:
            self.parent.date_check.setChecked(self.config_manager.get("action_options.date"))
            self.parent.markdown_check.setChecked(self.config_manager.get("action_options.markdown"))
            self.parent.open_explorer_check.setChecked(self.config_manager.get("action_options.open_explorer"))
            self.parent.sanitize_name_check.setChecked(self.config_manager.get("action_options.sanitize_name"))
            self.parent.operational_percentage_spin.setValue(int(self.config_manager.get("operational_percentage")))
        except:
            pass
        
        # Load API keys and credentials
        self.parent.gemini_api_edit.setText(self._get_gemini_api_key())
        self.parent.gemini_status_label.setText("")
        
        # Load Google Drive credentials path
        gdrive_path = self._get_gdrive_credentials_path()
        self.parent.gdrive_path_edit.setText(gdrive_path)
        if gdrive_path:
            self.parent.gdrive_status_label.setText("Credentials configured.")
            self.parent.gdrive_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
        else:
            self.parent.gdrive_status_label.setText("")
        
        # Clear cache status label
        self.parent.cache_status_label.setText("")
        
    def save_action_options_data(self):
        """Save action options data to configuration"""
        self.config_manager.set("action_options.date", self.parent.date_check.isChecked())
        self.config_manager.set("action_options.markdown", self.parent.markdown_check.isChecked())
        self.config_manager.set("action_options.open_explorer", self.parent.open_explorer_check.isChecked())
        self.config_manager.set("action_options.sanitize_name", self.parent.sanitize_name_check.isChecked())
        self.config_manager.set("operational_percentage", self.parent.operational_percentage_spin.value())
        self._set_gemini_api_key(self.parent.gemini_api_edit.text().strip())
