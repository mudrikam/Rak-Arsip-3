import os
import tempfile
import hashlib
from PIL import Image


class PropertiesThumbnailCaching:
    """Thumbnail cache for properties widget preview images."""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.cache_dir = self._get_cache_dir()
    
    def _get_cache_dir(self):
        """Get thumbnail cache directory from db config."""
        temp_dir = tempfile.gettempdir()
        if self.config_manager:
            cache_subpath = self.config_manager.get("system_caching.projects_thumbnail_cache")
            cache_dir = os.path.join(temp_dir, cache_subpath)
        else:
            cache_dir = os.path.join(temp_dir, "RakArsip", "projects_thumbnail_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    def _generate_cache_key(self, image_path):
        """Generate cache key from image path."""
        abs_path = os.path.abspath(image_path)
        path_hash = hashlib.sha256(abs_path.encode('utf-8')).hexdigest()
        return f"{path_hash}.jpg"
    
    def get_cached_thumbnail(self, image_path):
        """Get cached thumbnail path if exists."""
        cache_key = self._generate_cache_key(image_path)
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        if os.path.exists(cache_path):
            print(f"[Thumbnail Cache] Loaded from cache: {os.path.basename(image_path)}")
            return cache_path
        return None
    
    def create_thumbnail(self, image_path, max_size=500, quality=70):
        """Create thumbnail cache for image."""
        if not os.path.exists(image_path):
            print(f"[Thumbnail Cache] Image not found: {image_path}")
            return None
        
        cache_key = self._generate_cache_key(image_path)
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        try:
            img = Image.open(image_path)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int((max_size / width) * height)
                else:
                    new_height = max_size
                    new_width = int((max_size / height) * width)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            img.save(cache_path, format='JPEG', quality=quality, optimize=True)
            print(f"[Thumbnail Cache] Created new cache: {os.path.basename(image_path)}")
            return cache_path
        
        except Exception as e:
            print(f"[Thumbnail Cache] Error creating thumbnail for {image_path}: {e}")
            return None
    
    def get_or_create_thumbnail(self, image_path, max_size=500, quality=70):
        """Get cached thumbnail or create if not exists."""
        cached = self.get_cached_thumbnail(image_path)
        if cached:
            return cached
        
        return self.create_thumbnail(image_path, max_size, quality)
    
    def clear_cache(self):
        """Clear all cached thumbnails."""
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print("[Thumbnail Cache] Cache cleared")
        except Exception as e:
            print(f"[Thumbnail Cache] Error clearing cache: {e}")
