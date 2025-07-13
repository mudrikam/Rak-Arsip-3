import os
import json
from pathlib import Path

class GeminiHelper:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.load_ai_config()
        
    def load_ai_config(self):
        try:
            basedir = Path(__file__).parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if ai_config_path.exists():
                with open(ai_config_path, 'r', encoding='utf-8') as f:
                    self.ai_config = json.load(f)
            else:
                self.ai_config = {
                    "gemini": {
                        "api_key": "",
                        "model": "gemini-2.5-flash",
                        "max_tokens": 100,
                        "temperature": 0.7
                    },
                    "prompts": {
                        "name_generation": "Based on this image, generate a creative, descriptive project name in English. The name should be 3-5 words maximum, suitable for a design project folder. Use underscores instead of spaces. Just return the name without explanation."
                    }
                }
        except Exception as e:
            print(f"Error loading AI config: {e}")
            self.ai_config = {}
            
    def generate_name_from_image(self, image_path):
        try:
            gemini_config = self.ai_config.get("gemini", {})
            api_key = gemini_config.get("api_key", "")
            if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
                raise Exception("Gemini API key not configured in ai_config.json")
            model = gemini_config.get("model", "gemini-2.5-flash")
            prompt = self.ai_config.get("prompts", {}).get("name_generation", "Generate a project name for this image")
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                client = genai.GenerativeModel(model)
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                # Use dict for image part, not types.Part
                image_part = {
                    "mime_type": self.get_mime_type(image_path),
                    "data": image_bytes
                }
                response = client.generate_content(
                    [image_part, prompt]
                )
                generated_name = response.text.strip()
                sanitized_name = self.sanitize_name(generated_name)
                return sanitized_name
            except ImportError:
                raise Exception("Google GenAI library not installed. Install with: pip install google-generativeai")
        except Exception as e:
            print(f"Error generating name from image: {e}")
            raise e
            
    def get_mime_type(self, image_path):
        extension = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        return mime_types.get(extension, 'image/jpeg')
        
    def sanitize_name(self, name):
        name = name.strip()
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        if name.startswith("'") and name.endswith("'"):
            name = name[1:-1]
        forbidden_chars = '<>:"/\\|?*#&$%@!^()[]{};=+`~\''
        sanitized = "".join(c if c not in forbidden_chars else "_" for c in name)
        sanitized = sanitized.replace(" ", "_")
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        sanitized = sanitized.strip("_")
        return sanitized if sanitized else "Generated_Project"