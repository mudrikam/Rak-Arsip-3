import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

class GeminiHelper:
    def __init__(self, config_manager, db_manager=None):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.db_context = None  # Pre-fetched database context for thread safety
        basedir = Path(__file__).parent.parent
        env_path = basedir / ".env"
        
        # Create default .env if it doesn't exist
        if not env_path.exists():
            self._create_default_env(env_path)
        
        if env_path.exists():
            load_dotenv(env_path)
        self.load_ai_config()
    
    def _create_default_env(self, env_path):
        """Create default .env file with standard settings."""
        try:
            default_content = """DEVELOPMENT=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_TOKENS=5000
GEMINI_TEMPERATURE=0.7
GOOGLE_DRIVE_CREDENTIALS_PATH=
"""
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
            print(f"Created default .env file at {env_path}")
        except Exception as e:
            print(f"Error creating default .env file: {e}")
    
    def set_db_context(self, context):
        """Set pre-fetched database context to avoid SQLite threading issues."""
        self.db_context = context
        print(f"DEBUG: Database context set with {len(context.get('pockets', []))} pockets")
        
    def load_ai_config(self):
        try:
            basedir = Path(__file__).parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if not ai_config_path.exists():
                raise Exception(f"AI config file not found at {ai_config_path}")
            
            with open(ai_config_path, 'r', encoding='utf-8') as f:
                self.ai_config = json.load(f)
                
        except Exception as e:
            print(f"CRITICAL ERROR loading AI config: {e}")
            raise e
            
    def generate_name_from_image(self, image_path):
        try:
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise Exception("Gemini API key not configured in .env")
            
            print(f"DEBUG: API Key loaded: {api_key[:20]}...{api_key[-5:]} (length: {len(api_key)})")
            
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            prompt = self.ai_config.get("prompts", {}).get("name_generation")
            
            if not prompt:
                raise Exception("name_generation prompt not found in ai_config.json")
            
            try:
                import google.genai as genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=self.get_mime_type(image_path)
                )
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        image_part,
                        prompt
                    ]
                )
                generated_name = response.text.strip()
                sanitized_name = self.sanitize_name(generated_name)
                return sanitized_name
            except ImportError:
                raise Exception("Google GenAI library not installed. Install with: pip install google-genai")
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
    
    def analyze_invoice(self, image_path, max_retries=3, retry_delay=5):
        try:
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise Exception("Gemini API key not configured in .env")
            
            print(f"DEBUG: API Key loaded: {api_key[:20]}...{api_key[-5:]} (length: {len(api_key)})")
            
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            prompt = self.ai_config.get("prompts", {}).get("invoice_analysis")
            
            if not prompt:
                raise Exception("invoice_analysis prompt not found in ai_config.json")
            
            context_data = {}
            
            print(f"\nDEBUG: Checking context sources...")
            print(f"  db_context (pre-fetched): {self.db_context is not None}")
            print(f"  db_manager (direct access): {self.db_manager is not None}")
            
            # Use pre-fetched context if available (thread-safe)
            if self.db_context:
                try:
                    print("DEBUG: Using pre-fetched database context (thread-safe)...")
                    
                    pockets = self.db_context.get('pockets', [])
                    categories = self.db_context.get('categories', [])
                    currencies = self.db_context.get('currencies', [])
                    locations = self.db_context.get('locations', [])
                    statuses = self.db_context.get('statuses', [])
                    
                    print(f"DEBUG: Context has {len(pockets)} pockets, {len(categories)} categories, {len(currencies)} currencies")
                    
                    context_data = {
                        "available_options": {
                            "pockets": [{"id": p['id'], "name": p['name']} for p in pockets],
                            "categories": [{"id": c['id'], "name": c['name']} for c in categories],
                            "currencies": [{"id": c['id'], "code": c['code']} for c in currencies],
                            "locations": [{"id": l['id'], "name": l['name']} for l in locations],
                            "transaction_statuses": [{"id": s['id'], "name": s['name']} for s in statuses],
                            "transaction_types": ["income", "expense", "transfer"],
                            "item_types": ["Physical", "Digital", "Service", "Subscription", "Other"]
                        }
                    }
                    
                    print(f"DEBUG: Context data created! Pockets: {len(context_data['available_options']['pockets'])}, Categories: {len(context_data['available_options']['categories'])}")
                    
                except Exception as e:
                    print(f"ERROR processing pre-fetched context: {e}")
                    import traceback
                    traceback.print_exc()
            # Fallback: try direct db_manager access (may fail in thread)
            elif self.db_manager and hasattr(self.db_manager, 'wallet_helper'):
                try:
                    print("WARNING: Using direct db_manager access (may fail in threads)...")
                    
                    pockets = self.db_manager.wallet_helper.get_all_pockets()
                    categories = self.db_manager.wallet_helper.get_all_categories()
                    currencies = self.db_manager.wallet_helper.get_all_currencies()
                    locations = self.db_manager.wallet_helper.get_all_locations()
                    statuses = self.db_manager.wallet_helper.get_all_transaction_statuses()
                    
                    context_data = {
                        "available_options": {
                            "pockets": [{"id": p['id'], "name": p['name']} for p in pockets],
                            "categories": [{"id": c['id'], "name": c['name']} for c in categories],
                            "currencies": [{"id": c['id'], "code": c['code']} for c in currencies],
                            "locations": [{"id": l['id'], "name": l['name']} for l in locations],
                            "transaction_statuses": [{"id": s['id'], "name": s['name']} for s in statuses],
                            "transaction_types": ["income", "expense", "transfer"],
                            "item_types": ["Physical", "Digital", "Service", "Subscription", "Other"]
                        }
                    }
                    
                    print(f"DEBUG: Context data created! Pockets: {len(context_data['available_options']['pockets'])}")
                    
                except Exception as e:
                    print(f"ERROR getting database options: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("WARNING: No context available - neither pre-fetched nor db_manager!")
            
            if context_data:
                context_json = json.dumps(context_data, indent=2, ensure_ascii=False)
                full_prompt = prompt + "\n\n" + context_json
            else:
                full_prompt = prompt
            
            print("\n" + "="*80)
            print("=== RAW PROMPT SENT TO GEMINI ===")
            print("="*80)
            print(full_prompt)
            print("="*80)
            print("=== END RAW PROMPT ===")
            print("="*80 + "\n")
            
            print("\n=== DEBUG: Analyzing Invoice ===")
            print(f"Image: {image_path}")
            print(f"Model: {model}")
            print(f"Prompt length: {len(full_prompt)} characters")
            
            try:
                import google.genai as genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=self.get_mime_type(image_path)
                )
                
                last_exception = None
                for attempt in range(1, max_retries + 1):
                    try:
                        response = client.models.generate_content(
                            model=model,
                            contents=[
                                image_part,
                                full_prompt
                            ]
                        )
                        raw_response = response.text.strip()
                        print("\n=== RAW GEMINI RESPONSE ===")
                        print(raw_response)
                        print("=== END RAW RESPONSE ===\n")
                        
                        cleaned_response = raw_response
                        if cleaned_response.startswith("```json"):
                            cleaned_response = cleaned_response[7:]
                        if cleaned_response.startswith("```"):
                            cleaned_response = cleaned_response[3:]
                        if cleaned_response.endswith("```"):
                            cleaned_response = cleaned_response[:-3]
                        cleaned_response = cleaned_response.strip()
                        
                        # Remove any extra closing braces or characters after valid JSON
                        # Try to find the end of the JSON object
                        brace_count = 0
                        json_end = -1
                        for i, char in enumerate(cleaned_response):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0 and json_end < len(cleaned_response):
                            print(f"Truncating response from {len(cleaned_response)} to {json_end} characters")
                            cleaned_response = cleaned_response[:json_end]
                        
                        try:
                            analysis_data = json.loads(cleaned_response)
                            print("\n=== PARSED JSON DATA ===")
                            print(json.dumps(analysis_data, indent=2))
                            print("=== END PARSED DATA ===\n")
                            return analysis_data
                        except json.JSONDecodeError as je:
                            print(f"JSON Parse Error: {je}")
                            print(f"Cleaned response: {cleaned_response}")
                            raise Exception(f"Failed to parse AI response as JSON: {str(je)}")
                    except Exception as e:
                        last_exception = e
                        error_str = str(e)
                        if "503 UNAVAILABLE" in error_str or "model is overloaded" in error_str:
                            print(f"Gemini model overloaded (attempt {attempt}/{max_retries}), retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"Error analyzing invoice: {e}")
                            raise e
                print(f"Error analyzing invoice after {max_retries} retries: {last_exception}")
                raise last_exception
            except ImportError:
                raise Exception("Google GenAI library not installed. Install with: pip install google-genai")
        except Exception as e:
            print(f"Error analyzing invoice: {e}")
            import traceback
            traceback.print_exc()
            raise e
