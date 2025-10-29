import os
import json
import time
from pathlib import Path

class GeminiHelper:
    def __init__(self, config_manager, db_manager=None):
        self.config_manager = config_manager
        self.db_manager = db_manager
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
                        "name_generation": "Based on this image, generate a creative, descriptive project name in English. The name should be 3-5 words maximum, suitable for a design project folder. Use underscores instead of spaces. Just return the name without explanation.",
                        "invoice_analysis": "Analyze this invoice/receipt image and extract transaction information. Return ONLY a valid JSON object without any markdown formatting, code blocks, or explanations. The JSON should have this exact structure: {\"transaction_details\": {\"name\": \"transaction name or empty string\", \"type\": \"income/expense/transfer or empty string\", \"pocket_id\": null, \"destination_pocket_id\": null, \"card_id\": null, \"currency_id\": null, \"location_id\": null, \"category_id\": null, \"status_id\": null}, \"items\": [{\"item_type\": \"product/service/digital or empty string\", \"sku\": \"sku or empty string\", \"item_name\": \"item name\", \"item_description\": \"description or empty string\", \"quantity\": 1, \"unit\": \"pcs/kg/etc or empty string\", \"amount\": 0.0, \"width\": 0.0, \"height\": 0.0, \"depth\": 0.0, \"weight\": 0.0, \"material\": \"material or empty string\", \"color\": \"color or empty string\", \"file_url\": \"url or empty string\", \"license_key\": \"key or empty string\", \"expiry_date\": \"date or empty string\", \"digital_type\": \"type or empty string\", \"note\": \"note or empty string\"}]}. For transaction_details: use exact ID values from the provided options lists. For items: extract all visible items with their quantities and prices. If data is not visible in image, use empty string or 0. Ensure valid JSON syntax."
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
            prompt = self.ai_config.get("prompts", {}).get("name_generation")
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
            gemini_config = self.ai_config.get("gemini", {})
            api_key = gemini_config.get("api_key", "")
            if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
                raise Exception("Gemini API key not configured in ai_config.json")
            model = gemini_config.get("model", "gemini-2.5-flash")
            prompt = self.ai_config.get("prompts", {}).get("invoice_analysis")
            
            if not prompt:
                prompt = "Analyze this invoice/receipt image and extract transaction information. Return ONLY a valid JSON object without any markdown formatting, code blocks, or explanations. The JSON should have this exact structure: {\"transaction_details\": {\"name\": \"transaction name or empty string\", \"type\": \"income/expense/transfer or empty string\", \"pocket_id\": null, \"destination_pocket_id\": null, \"card_id\": null, \"currency_id\": null, \"location_id\": null, \"category_id\": null, \"status_id\": null}, \"items\": [{\"item_type\": \"product/service/digital or empty string\", \"sku\": \"sku or empty string\", \"item_name\": \"item name\", \"item_description\": \"description or empty string\", \"quantity\": 1, \"unit\": \"pcs/kg/etc or empty string\", \"amount\": 0.0, \"width\": 0.0, \"height\": 0.0, \"depth\": 0.0, \"weight\": 0.0, \"material\": \"material or empty string\", \"color\": \"color or empty string\", \"file_url\": \"url or empty string\", \"license_key\": \"key or empty string\", \"expiry_date\": \"date or empty string\", \"digital_type\": \"type or empty string\", \"note\": \"note or empty string\"}]}. For transaction_details: use exact ID values from the provided options lists. For items: extract all visible items with their quantities and prices. If data is not visible in image, use empty string or 0. Ensure valid JSON syntax."
            
            context_parts = []
            
            if self.db_manager:
                try:
                    pockets = self.db_manager.wallet_helper.get_all_pockets()
                    categories = self.db_manager.wallet_helper.get_all_categories()
                    currencies = self.db_manager.wallet_helper.get_all_currencies()
                    locations = self.db_manager.wallet_helper.get_all_locations()
                    statuses = self.db_manager.wallet_helper.get_all_transaction_statuses()
                    
                    context_parts.append("\n\nAvailable options for transaction_details:")
                    
                    context_parts.append("\nPockets (use pocket_id):")
                    for pocket in pockets:
                        context_parts.append(f"  - id: {pocket['id']}, name: {pocket['name']}")
                    
                    context_parts.append("\nCategories (use category_id):")
                    for category in categories:
                        context_parts.append(f"  - id: {category['id']}, name: {category['name']}")
                    
                    context_parts.append("\nCurrencies (use currency_id):")
                    for currency in currencies:
                        context_parts.append(f"  - id: {currency['id']}, code: {currency['code']}, symbol: {currency['symbol']}")
                    
                    context_parts.append("\nLocations (use location_id):")
                    for location in locations:
                        context_parts.append(f"  - id: {location['id']}, name: {location['name']}")
                    
                    context_parts.append("\nTransaction Statuses (use status_id):")
                    for status in statuses:
                        context_parts.append(f"  - id: {status['id']}, name: {status['name']}")
                    
                    context_parts.append("\nTransaction types: income, expense, transfer")
                    context_parts.append("\nItem types: product, service, digital")
                    
                except Exception as e:
                    print(f"Error getting database options: {e}")
            
            full_prompt = prompt + "".join(context_parts)
            
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
