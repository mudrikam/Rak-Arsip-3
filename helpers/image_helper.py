"""
Image Helper Module
Handles image compression, resizing, and conversion for wallet features.
"""

import os
import io
from datetime import datetime
from PIL import Image
import hashlib
import hashlib
import shutil


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
        Generate path for transaction image organized in per-transaction folder.

        New structure (dev, no backward compatibility):
        basedir/images/transactions/invoices/<Year>/<MonthName>/<day>/<transaction_id>/invoice_<transaction_id>_<YYYYmmdd_HHMMSS>_<hash>.jpg

        If transaction_id is None, files are placed under a tmp folder:
        basedir/images/transactions/invoices/tmp/<invoice_tmp_<timestamp>_<hash>.jpg>
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        if transaction_id:
            year = now.strftime("%Y")
            month = now.strftime("%B")
            day = str(now.day)
            dir_path = os.path.join(basedir, "images", "transactions", "invoices", year, month, day, str(transaction_id))
            prefix = f"invoice_{transaction_id}"
        else:
            dir_path = os.path.join(basedir, "images", "transactions", "invoices", "tmp")
            prefix = "invoice_tmp"

        os.makedirs(dir_path, exist_ok=True)

        # compute hash based on timestamp (or content elsewhere) for filename uniqueness
        short_hash = hashlib.sha1(timestamp.encode('utf-8')).hexdigest()[:8]
        filename = f"{prefix}_{timestamp}_{short_hash}.jpg"
        return os.path.join(dir_path, filename)

    @staticmethod
    def _compute_hash_for_source(src):
        """Compute short sha1 hash for a file path or bytes.

        Returns first 8 hex chars.
        """
        try:
            if isinstance(src, (str, os.PathLike)):
                with open(src, 'rb') as f:
                    data = f.read()
            elif isinstance(src, (bytes, bytearray)):
                data = bytes(src)
            else:
                return '00000000'
            return hashlib.sha1(data).hexdigest()[:8]
        except Exception:
            return '00000000'

    @staticmethod
    def generate_invoice_image_path(basedir, transaction_id, invoice_id, src_path_or_bytes, timestamp=None):
        """Generate managed path for a transaction invoice image using invoice_id.

        Directory: basedir/images/transactions/invoices/<Year>/<MonthName>/<day>/<transaction_id>/
        Filename: invoice_<invoice_id>_<YYYYmmdd_HHMMSS>_<hash>.jpg
        """
        now = datetime.now() if timestamp is None else timestamp
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        year = now.strftime("%Y")
        month = now.strftime("%B")
        day = str(now.day)

        dir_path = os.path.join(basedir, "images", "transactions", "invoices", year, month, day, str(transaction_id))
        os.makedirs(dir_path, exist_ok=True)

        h = ImageHelper._compute_hash_for_source(src_path_or_bytes)
        filename = f"invoice_{invoice_id}_{timestamp_str}_{h}.jpg"
        return os.path.join(dir_path, filename)

    @staticmethod
    def generate_location_image_path(basedir, location_id, src_path_or_bytes=None, timestamp=None):
        """Generate managed path for a location image using location_id.

        Directory: basedir/images/locations/<Year>/<MonthName>/<day>/<location_id>/
        Filename: location_<location_id>_<YYYYmmdd_HHMMSS>_<hash>.jpg

        If src_path_or_bytes is None, a timestamp-based short hash will be used.
        """
        now = datetime.now() if timestamp is None else timestamp
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        year = now.strftime("%Y")
        month = now.strftime("%B")
        day = str(now.day)

        if location_id is None:
            # Pre-insert temporary storage for uploaded images. Keep a clear 'tmp' marker
            # so caller (e.g., add_location) can detect and move the file after DB insert.
            dir_path = os.path.join(basedir, "images", "locations", "tmp")
            os.makedirs(dir_path, exist_ok=True)
            h = hashlib.sha1(timestamp_str.encode('utf-8')).hexdigest()[:8]
            filename = f"location_tmp_{timestamp_str}_{h}.jpg"
            return os.path.join(dir_path, filename)

        # Proper per-date per-id location folder
        dir_path = os.path.join(basedir, "images", "locations", year, month, day, str(location_id))
        os.makedirs(dir_path, exist_ok=True)

        if src_path_or_bytes:
            h = ImageHelper._compute_hash_for_source(src_path_or_bytes)
        else:
            h = hashlib.sha1(timestamp_str.encode('utf-8')).hexdigest()[:8]

        filename = f"location_{location_id}_{timestamp_str}_{h}.jpg"
        return os.path.join(dir_path, filename)

    @staticmethod
    def is_path_in_transaction_images(basedir, path):
        """
        Return True if the given path is inside the app's transaction images invoices folder.

        This is used to determine whether an image file already lives under the
        application's managed images directory (so it doesn't need to be re-saved).
        """
        if not path:
            return False
        try:
            abs_basedir = os.path.abspath(basedir)
            abs_path = os.path.abspath(path)
            # normalize and compare commonprefix safely
            images_root = os.path.join(abs_basedir, "images", "transactions", "invoices")
            images_root = os.path.abspath(images_root)
            # Ensure the path starts with images_root
            return os.path.commonpath([images_root, abs_path]) == images_root
        except Exception:
            return False

    @staticmethod
    def is_path_in_subfolder(basedir, path, *subfolders):
        """
        Check whether a path lives under a specific subfolder of basedir.

        Example: is_path_in_subfolder(basedir, path, 'images', 'locations')
                 -> True if path is inside basedir/images/locations
        """
        if not path:
            return False
        try:
            abs_basedir = os.path.abspath(basedir)
            abs_path = os.path.abspath(path)
            target_root = os.path.join(abs_basedir, *subfolders)
            target_root = os.path.abspath(target_root)
            return os.path.commonpath([target_root, abs_path]) == target_root
        except Exception:
            return False
    
    @staticmethod
    # NOTE: previous duplicate generate_location_image_path definition removed.

    @staticmethod
    def compute_hash_of_file(path, length=8):
        """Return hex sha1 of file content (first `length` chars)."""
        try:
            h = hashlib.sha1()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()[:length]
        except Exception:
            return None

    @staticmethod
    def move_image_to_location_folder(basedir, src_rel_or_abs, location_id):
        """
        Move existing image (absolute or relative to basedir) into the per-location folder
        and rename it using the desired naming convention. Returns new relative path or None.
        """
        try:
            # resolve absolute src
            if os.path.isabs(src_rel_or_abs):
                src_abs = src_rel_or_abs
            else:
                src_abs = os.path.join(basedir, src_rel_or_abs)

            if not os.path.exists(src_abs):
                return None

            # compute hash and build target path
            short_hash = ImageHelper.compute_hash_of_file(src_abs) or hashlib.sha1(str(os.path.getmtime(src_abs)).encode()).hexdigest()[:8]
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Move into per-date per-id folder (keep consistent with naming scheme)
            now_dt = datetime.now()
            year = now_dt.strftime("%Y")
            month = now_dt.strftime("%B")
            day = str(now_dt.day)
            dir_path = os.path.join(basedir, "images", "locations", year, month, day, str(location_id))
            os.makedirs(dir_path, exist_ok=True)
            filename = f"location_{location_id}_{now}_{short_hash}.jpg"
            dest_abs = os.path.join(dir_path, filename)

            # move (prefer rename)
            try:
                shutil.move(src_abs, dest_abs)
            except Exception:
                # fallback to copy+remove
                shutil.copy2(src_abs, dest_abs)
                try:
                    os.remove(src_abs)
                except Exception:
                    pass

            rel = os.path.relpath(dest_abs, basedir).replace('\\', '/')
            return rel
        except Exception as e:
            print(f"Error moving location image: {e}")
            return None
    
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
