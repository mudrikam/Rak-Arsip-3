from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QFileDialog, QMessageBox, QApplication, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage, QGuiApplication, QIcon
import qtawesome as qta
import os
import shutil
import uuid
from pathlib import Path
from helpers.gemini_helper import GeminiHelper
from helpers.show_statusbar_helper import show_statusbar_message
import textwrap

class ImageDropLabel(QLabel):
    image_dropped = Signal(str)
    image_pasted = Signal(QImage)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 200)
        self.setMaximumHeight(16777215)
        self.setText("Drop image here or click to select")
        self.setWordWrap(True)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select_image()
            
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if file_path:
            self.image_dropped.emit(file_path)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.image_dropped.emit(file_path)
            event.acceptProposedAction()

    def keyPressEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_V:
            clipboard = QGuiApplication.clipboard()
            image = clipboard.image()
            if not image.isNull():
                self.image_pasted.emit(image)
                event.accept()
                return
        super().keyPressEvent(event)

class NameGenerationThread(QThread):
    name_generated = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, image_path, gemini_helper):
        super().__init__()
        self.image_path = image_path
        self.gemini_helper = gemini_helper
        
    def run(self):
        try:
            generated_name = self.gemini_helper.generate_name_from_image(self.image_path)
            if generated_name:
                self.name_generated.emit(generated_name)
            else:
                self.error_occurred.emit("Failed to generate name from image (no name returned by Gemini API)")
        except Exception as e:
            self.error_occurred.emit(f"Failed to generate name: {e}")

class GenerateNameDialog(QDialog):
    def start_api_btn_blink(self):
        from PySide6.QtCore import QTimer
        self._api_blink_state = False
        if hasattr(self, '_api_blink_timer') and self._api_blink_timer:
            self._api_blink_timer.stop()
        self._api_blink_timer = QTimer(self)
        self._api_blink_timer.timeout.connect(self._toggle_api_btn_blink)
        self._api_blink_timer.start(350)

    def stop_api_btn_blink(self):
        if hasattr(self, '_api_blink_timer') and self._api_blink_timer:
            self._api_blink_timer.stop()
            self._api_blink_timer = None
        self.test_api_btn.setStyleSheet("")
        self._api_blink_state = False

    def _toggle_api_btn_blink(self):
        if not hasattr(self, '_api_blink_state'):
            self._api_blink_state = False
        self._api_blink_state = not self._api_blink_state
        if self._api_blink_state:
            self.test_api_btn.setStyleSheet("background-color: rgba(255, 207, 36, 0.4);")
        else:
            self.test_api_btn.setStyleSheet("")
    name_generated = Signal(str)
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Generate Project Name from Image")
        # Use the same icon as AboutDialog for consistency
        from PySide6.QtGui import QIcon
        from pathlib import Path
        icon_path = Path(__file__).parent.parent.parent / "res" / "rakikon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            self.setWindowIcon(qta.icon("fa6s.folder-tree"))
        self.setMinimumSize(400, 360)
        self.setMaximumHeight(400)
        self.setModal(True)
        
        self.temp_image_path = None
        self.gemini_helper = GeminiHelper(config_manager)
        
        self.setup_ui()
        self.setup_temp_folder()
        
    def setup_temp_folder(self):
        try:
            ai_config = self.config_manager.get("ai_config")
            self.temp_folder = ai_config.get("temp_folder")
        except:
            self.temp_folder = "temp/images"
        basedir = Path(__file__).parent.parent.parent
        self.temp_path = basedir / self.temp_folder
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        self.image_frame = QFrame()
        self.image_frame.setFrameShape(QFrame.StyledPanel)
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(4)

        self.image_label = ImageDropLabel()
        self.image_label.image_dropped.connect(self.load_image)
        self.image_label.image_pasted.connect(self.paste_image)
        image_layout.addWidget(self.image_label)
        self.image_frame.setLayout(image_layout)
        layout.addWidget(self.image_frame)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 15px; color: #1976d2;")
        self.result_label.setMaximumHeight(40)
        layout.addWidget(self.result_label)

        self.char_count_label = QLabel("")
        self.char_count_label.setAlignment(Qt.AlignCenter)
        self.char_count_label.setStyleSheet("font-size: 12px; color: #1976d2;")
        self.char_count_label.setMaximumHeight(20)
        layout.addWidget(self.char_count_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.generate_btn = QPushButton("Generate Name from Image")
        self.generate_btn.setIcon(qta.icon("fa6s.wand-magic-sparkles"))
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_name)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setIcon(qta.icon("fa6s.paste"))
        self.paste_btn.clicked.connect(self.on_paste_clicked)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(qta.icon("fa6s.xmark"))
        self.clear_btn.clicked.connect(self.clear_image)

        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.paste_btn)
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)

        dialog_buttons = QHBoxLayout()
        self.test_api_btn = QPushButton()
        self.test_api_btn.setIcon(qta.icon("fa6s.plug-circle-check"))
        self.test_api_btn.setToolTip("Test Gemini API Key")
        self.test_api_btn.clicked.connect(self.test_gemini_api)
        self.api_status_label = QLabel("")
        self.api_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        dialog_buttons.addWidget(self.test_api_btn)
        dialog_buttons.addWidget(self.api_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(18)
        dialog_buttons.addWidget(self.progress_bar)

        dialog_buttons.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setIcon(qta.icon("fa6s.check"))
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(qta.icon("fa6s.xmark"))
        self.cancel_btn.clicked.connect(self.reject)

        dialog_buttons.addWidget(self.ok_btn)
        dialog_buttons.addWidget(self.cancel_btn)
        layout.addLayout(dialog_buttons)

        self.generated_name = ""
        self.setLayout(layout)

    def test_gemini_api(self):
        try:
            ai_config = self.gemini_helper.ai_config
            api_key = ai_config.get("gemini", {}).get("api_key", "")
            if not api_key:
                self.api_status_label.setText("API Key is empty.")
                self.api_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                show_statusbar_message(self, "Gemini API Key is empty.")
                return
            try:
                import google.genai as genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=ai_config.get("gemini", {}).get("model", "gemini-2.0-flash"),
                    contents=["Say hello"]
                )
                if hasattr(response, "text") and response.text:
                    self.api_status_label.setText("Gemini API is active.")
                    self.api_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
                    show_statusbar_message(self, "Gemini API is active.")
                else:
                    self.api_status_label.setText("No response from Gemini API.")
                    self.api_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                    show_statusbar_message(self, "No response from Gemini API.")
            except ImportError:
                self.api_status_label.setText("google-genai not installed.")
                self.api_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                show_statusbar_message(self, "google-genai not installed.")
            except Exception as e:
                self.api_status_label.setText(f"Error: {e}")
                self.api_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                show_statusbar_message(self, f"Gemini API error: {e}")
        except Exception as e:
            self.api_status_label.setText(f"Error: {e}")
            self.api_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            show_statusbar_message(self, f"Gemini API error: {e}")

    def on_paste_clicked(self):
        clipboard = QGuiApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            self.paste_image(image)
            show_statusbar_message(self, "Image pasted from clipboard.")
        else:
            QMessageBox.warning(self, "Paste Image", "Clipboard does not contain an image.")
            show_statusbar_message(self, "Clipboard does not contain an image.")

    def showEvent(self, event):
        super().showEvent(event)
        self.image_label.setFocus()

    def load_image(self, file_path):
        try:
            temp_filename = f"{uuid.uuid4()}{Path(file_path).suffix}"
            self.temp_image_path = self.temp_path / temp_filename
            shutil.copy2(file_path, self.temp_image_path)
            pixmap = QPixmap(str(self.temp_image_path))
            if not pixmap.isNull():
                label_width = self.image_label.width()
                if label_width < 10:
                    label_width = 400
                scaled_pixmap = pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
                self.generate_btn.setEnabled(True)
                show_statusbar_message(self, f"Image loaded: {file_path}")
            else:
                QMessageBox.warning(self, "Error", "Failed to load image")
                self.clear_image()
                show_statusbar_message(self, "Failed to load image.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")
            self.clear_image()
            show_statusbar_message(self, f"Failed to load image: {e}")

    def paste_image(self, image):
        try:
            temp_filename = f"{uuid.uuid4()}.png"
            temp_path = self.temp_path / temp_filename
            image.save(str(temp_path), "PNG")
            self.temp_image_path = temp_path
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                label_width = self.image_label.width()
                if label_width < 10:
                    label_width = 400
                scaled_pixmap = pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
                self.generate_btn.setEnabled(True)
                show_statusbar_message(self, "Image pasted and loaded.")
                self.generate_name()
            else:
                QMessageBox.warning(self, "Error", "Failed to paste image")
                self.clear_image()
                show_statusbar_message(self, "Failed to paste image.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to paste image: {e}")
            self.clear_image()
            show_statusbar_message(self, f"Failed to paste image: {e}")
            
    def clear_image(self):
        self.image_label.clear()
        self.image_label.setText("Drop image here or click to select")
        self.generate_btn.setEnabled(False)
        self.ok_btn.setEnabled(False)
        self.result_label.setText("")
        self.generated_name = ""
        if self.temp_image_path and self.temp_image_path.exists():
            try:
                self.temp_image_path.unlink()
                self.temp_image_path = None
            except:
                pass
        show_statusbar_message(self, "Image cleared.")

    def generate_name(self):
        if not self.temp_image_path or not self.temp_image_path.exists():
            QMessageBox.warning(self, "Error", "No image selected")
            show_statusbar_message(self, "No image selected for name generation.")
            return
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")
        self.progress_bar.setVisible(True)
        self.result_label.setText("")
        self.start_api_btn_blink()
        self.generation_thread = NameGenerationThread(str(self.temp_image_path), self.gemini_helper)
        self.generation_thread.name_generated.connect(self.on_name_generated)
        self.generation_thread.error_occurred.connect(self.on_generation_error)
        self.generation_thread.start()
        show_statusbar_message(self, "Generating name from image...")

    def on_name_generated(self, name):
        self.stop_api_btn_blink()
        self.generated_name = name
        char_count = len(name)
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Name from Image")
        self.ok_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.result_label.setStyleSheet("font-size: 15px; color: #1976d2;")
        self.result_label.setText(self._wrap_text(name, 32))
        if 40 <= char_count <= 50:
            self.char_count_label.setStyleSheet("font-size: 12px; color: white;")
        elif char_count > 50:
            self.char_count_label.setStyleSheet("font-size: 12px; color: yellow;")
        else:
            self.char_count_label.setStyleSheet("font-size: 12px; color: #1976d2;")
        self.char_count_label.setText(f"Character count: {char_count}")
        show_statusbar_message(self, f"Name generated: {name} ({char_count} chars)")

    def on_generation_error(self, error):
        self.stop_api_btn_blink()
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Name from Image")
        self.progress_bar.setVisible(False)
        self.result_label.setStyleSheet("font-size: 12px; color: #d32f2f;")
        self.result_label.setText(error)
        self.char_count_label.setText("")
        show_statusbar_message(self, f"Name generation error: {error}")

    def _wrap_text(self, text, width):
        if not text:
            return ""
        lines = textwrap.wrap(text, width=width)
        return "\n".join(lines)
        
    def get_generated_name(self):
        return self.generated_name
        
    def get_temp_image_path(self):
        return str(self.temp_image_path) if self.temp_image_path else None
        
    def move_image_to_project(self, project_path, project_name):
        if not self.temp_image_path or not self.temp_image_path.exists():
            return None
        try:
            preview_folder = Path(project_path) / "Preview"
            preview_folder.mkdir(exist_ok=True)
            file_extension = self.temp_image_path.suffix
            final_image_path = preview_folder / f"{project_name}{file_extension}"
            shutil.move(str(self.temp_image_path), str(final_image_path))
            self.temp_image_path = None
            show_statusbar_message(self, f"Image moved to project: {final_image_path}")
            return str(final_image_path)
        except Exception as e:
            print(f"Error moving image to project: {e}")
            show_statusbar_message(self, f"Error moving image to project: {e}")
            return None
            
    def closeEvent(self, event):
        if self.temp_image_path and self.temp_image_path.exists():
            try:
                self.temp_image_path.unlink()
            except:
                pass
        super().closeEvent(event)
