from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, QLabel, 
    QPushButton, QLineEdit, QSpinBox, QMessageBox
)
import qtawesome as qta
from pathlib import Path
import json


class PreferencesActionsHelper:
    """Helper class for Action Options tab in Preferences window"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
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
        """Get Gemini API key from configuration"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if ai_config_path.exists():
                with open(ai_config_path, "r", encoding="utf-8") as f:
                    ai_config = json.load(f)
                return ai_config.get("gemini", {}).get("api_key", "")
        except Exception:
            pass
        return ""

    def _set_gemini_api_key(self, api_key):
        """Set Gemini API key in configuration"""
        try:
            basedir = Path(__file__).parent.parent.parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if ai_config_path.exists():
                with open(ai_config_path, "r", encoding="utf-8") as f:
                    ai_config = json.load(f)
                if "gemini" not in ai_config:
                    ai_config["gemini"] = {}
                ai_config["gemini"]["api_key"] = api_key
                with open(ai_config_path, "w", encoding="utf-8") as f:
                    json.dump(ai_config, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to save Gemini API key: {e}")

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
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Say hello"]
            )
            if hasattr(response, "text") and response.text:
                self.parent.gemini_status_label.setText("Gemini API is active.")
                self.parent.gemini_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            else:
                self.parent.gemini_status_label.setText("No response from Gemini API.")
                self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except ImportError:
            self.parent.gemini_status_label.setText("google-genai not installed.")
            self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except Exception as e:
            self.parent.gemini_status_label.setText(f"Error: {e}")
            self.parent.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            
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
        self.parent.gemini_api_edit.setText(self._get_gemini_api_key())
        self.parent.gemini_status_label.setText("")
        
    def save_action_options_data(self):
        """Save action options data to configuration"""
        self.config_manager.set("action_options.date", self.parent.date_check.isChecked())
        self.config_manager.set("action_options.markdown", self.parent.markdown_check.isChecked())
        self.config_manager.set("action_options.open_explorer", self.parent.open_explorer_check.isChecked())
        self.config_manager.set("action_options.sanitize_name", self.parent.sanitize_name_check.isChecked())
        self.config_manager.set("operational_percentage", self.parent.operational_percentage_spin.value())
        self._set_gemini_api_key(self.parent.gemini_api_edit.text().strip())
