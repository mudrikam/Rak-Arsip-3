"""
Image Helper Module
Handles image compression, resizing, and conversion for wallet features.
"""

import os
import io
from datetime import datetime
from PIL import Image


class ImageHelper:
    """Helper class for image processing operations."""
    
    @staticmethod
    def compress_and_resize_image(image_path_or_bytes, max_width=800, quality=80):
        """
        Compress and resize image to JPG format.
        
        Args:
            image_path_or_bytes: Path to image file or bytes data
            max_width: Maximum width (default 800px)
            quality: JPEG quality (default 80%)
        
        Returns:
            bytes: Compressed JPG image as bytes
        """
        try:
            if isinstance(image_path_or_bytes, (str, os.PathLike)):
                img = Image.open(image_path_or_bytes)
            else:
                img = Image.open(io.BytesIO(image_path_or_bytes))
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
        
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    @staticmethod
    def save_image_to_blob(image_path_or_bytes, max_width=800, quality=80):
        """
        Convert image to blob for database storage.
        
        Args:
            image_path_or_bytes: Path to image file or bytes data
            max_width: Maximum width (default 800px)
            quality: JPEG quality (default 80%)
        
        Returns:
            bytes: Image blob ready for database storage
        """
        return ImageHelper.compress_and_resize_image(image_path_or_bytes, max_width, quality)
    
    @staticmethod
    def save_image_to_file(image_path_or_bytes, output_path, max_width=800, quality=80):
        """
        Save image to file system with compression and resize.
        
        Args:
            image_path_or_bytes: Path to image file or bytes data
            output_path: Destination file path
            max_width: Maximum width (default 800px)
            quality: JPEG quality (default 80%)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            image_bytes = ImageHelper.compress_and_resize_image(image_path_or_bytes, max_width, quality)
            if not image_bytes:
                return False
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            return True
        
        except Exception as e:
            print(f"Error saving image to file: {e}")
            return False
    
    @staticmethod
    def generate_transaction_image_path(basedir, transaction_id=None):
        """
        Generate path for transaction image.
        
        Args:
            basedir: Base directory path
            transaction_id: Transaction ID (optional)
        
        Returns:
            str: Full path for image file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        dir_path = os.path.join(basedir, "images", "transactions", timestamp)
        
        if transaction_id:
            filename = f"{transaction_id}_{timestamp}.jpg"
        else:
            filename = f"temp_{timestamp}.jpg"
        
        return os.path.join(dir_path, filename)
    
    @staticmethod
    def blob_to_pixmap(blob_data):
        """
        Convert blob data to QPixmap for display.
        
        Args:
            blob_data: Image blob from database
        
        Returns:
            QPixmap: Image ready for display in Qt
        """
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import QByteArray
        
        if not blob_data:
            return QPixmap()
        
        byte_array = QByteArray(blob_data)
        pixmap = QPixmap()
        pixmap.loadFromData(byte_array)
        return pixmap
