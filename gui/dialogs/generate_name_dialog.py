from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage, QGuiApplication
import qtawesome as qta
import os
import shutil
import uuid
from pathlib import Path
from helpers.gemini_helper import GeminiHelper

class ImageDropLabel(QLabel):
    image_dropped = Signal(str)
    image_pasted = Signal(QImage)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(300, 200)
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
                self.error_occurred.emit("Failed to generate name from image")
        except Exception as e:
            self.error_occurred.emit(str(e))

class GenerateNameDialog(QDialog):
    name_generated = Signal(str)
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Generate Project Name from Image")
        self.setWindowIcon(qta.icon("fa6s.star"))
        self.setMinimumSize(400, 500)
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
    
        self.image_frame = QFrame()
        self.image_frame.setFrameShape(QFrame.StyledPanel)
        image_layout = QVBoxLayout(self.image_frame)
        
        self.image_label = ImageDropLabel()
        self.image_label.image_dropped.connect(self.load_image)
        self.image_label.image_pasted.connect(self.paste_image)
        image_layout.addWidget(self.image_label)
        
        layout.addWidget(self.image_frame)
        
        button_layout = QHBoxLayout()
        
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

    def on_paste_clicked(self):
        clipboard = QGuiApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            self.paste_image(image)
        else:
            QMessageBox.warning(self, "Paste Image", "Clipboard does not contain an image.")

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
                scaled_pixmap = pixmap.scaled(280, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
                self.generate_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to load image")
                self.clear_image()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")
            self.clear_image()

    def paste_image(self, image):
        try:
            temp_filename = f"{uuid.uuid4()}.png"
            temp_path = self.temp_path / temp_filename
            image.save(str(temp_path), "PNG")
            self.temp_image_path = temp_path
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(280, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
                self.generate_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to paste image")
                self.clear_image()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to paste image: {e}")
            self.clear_image()
            
    def clear_image(self):
        self.image_label.clear()
        self.image_label.setText("Drop image here or click to select")
        self.generate_btn.setEnabled(False)
        self.ok_btn.setEnabled(False)
        self.generated_name = ""
        if self.temp_image_path and self.temp_image_path.exists():
            try:
                self.temp_image_path.unlink()
                self.temp_image_path = None
            except:
                pass
                
    def generate_name(self):
        if not self.temp_image_path or not self.temp_image_path.exists():
            QMessageBox.warning(self, "Error", "No image selected")
            return
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")
        self.generation_thread = NameGenerationThread(str(self.temp_image_path), self.gemini_helper)
        self.generation_thread.name_generated.connect(self.on_name_generated)
        self.generation_thread.error_occurred.connect(self.on_generation_error)
        self.generation_thread.start()
        
    def on_name_generated(self, name):
        self.generated_name = name
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Name from Image")
        self.ok_btn.setEnabled(True)
        QMessageBox.information(self, "Success", f"Generated name: {name}")
        
    def on_generation_error(self, error):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Name from Image")
        QMessageBox.critical(self, "Error", f"Failed to generate name: {error}")
        
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
            return str(final_image_path)
        except Exception as e:
            print(f"Error moving image to project: {e}")
            return None
            
    def closeEvent(self, event):
        if self.temp_image_path and self.temp_image_path.exists():
            try:
                self.temp_image_path.unlink()
            except:
                pass
        super().closeEvent(event)
