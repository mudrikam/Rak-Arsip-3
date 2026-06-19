import base64
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


class GeminiHelper:
    def __init__(self, config_manager, db_manager=None):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.db_context = None
        basedir = Path(__file__).parent.parent
        env_path = basedir / ".env"

        if not env_path.exists():
            self._create_default_env(env_path)

        if env_path.exists():
            load_dotenv(env_path, override=True)
        self.load_ai_config()

    def _create_default_env(self, env_path):
        """Create default .env file with standard settings."""
        try:
            default_content = """DEVELOPMENT=false
AI_PROVIDER=gemini
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_TOKENS=5000
GEMINI_TEMPERATURE=0.7
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
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

    def get_provider(self):
        provider = os.getenv("AI_PROVIDER", "").strip().lower()
        return provider or "gemini"

    def get_effective_api_key(self):
        provider = self.get_provider()
        if provider == "openai_compatible":
            return os.getenv("AI_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        return os.getenv("AI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()

    def get_effective_model(self):
        provider = self.get_provider()
        if provider == "openai_compatible":
            return os.getenv("AI_MODEL", "").strip() or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        return os.getenv("AI_MODEL", "").strip() or os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    def get_effective_base_url(self):
        provider = self.get_provider()
        if provider == "openai_compatible":
            return os.getenv("AI_BASE_URL", "").strip() or os.getenv("OPENAI_BASE_URL", "").strip()
        return os.getenv("AI_BASE_URL", "").strip()

    def test_connection(self, api_key=None, provider=None, model=None, base_url=None):
        provider = (provider or self.get_provider()).strip().lower()
        api_key = (api_key if api_key is not None else self.get_effective_api_key()).strip()
        model = (model if model is not None else self.get_effective_model()).strip()
        base_url = (base_url if base_url is not None else self.get_effective_base_url()).strip()

        if not api_key:
            raise Exception("API key is not configured")
        if not model:
            raise Exception("Model is not configured")

        if provider == "openai_compatible":
            self._call_openai_compatible(
                prompt_text="Say hello",
                model=model,
                api_key=api_key,
                base_url=base_url,
                image_path=None,
            )
            return True

        self._call_gemini(
            prompt_text="Say hello",
            model=model,
            api_key=api_key,
            image_path=None,
        )
        return True

    def generate_name_from_image(self, image_path):
        try:
            api_key = self.get_effective_api_key()
            provider = self.get_provider()
            if not api_key:
                raise Exception(f"API key for provider '{provider}' not configured in .env")

            model = self.get_effective_model()
            prompt = self.ai_config.get("prompts", {}).get("name_generation")

            if not prompt:
                raise Exception("name_generation prompt not found in ai_config.json")

            generated_name = self._generate_content(
                prompt_text=prompt,
                image_path=image_path,
                expect_json=False,
            )
            sanitized_name = self.sanitize_name(generated_name)
            return sanitized_name
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
            api_key = self.get_effective_api_key()
            provider = self.get_provider()
            if not api_key:
                raise Exception(f"API key for provider '{provider}' not configured in .env")

            model = self.get_effective_model()
            prompt = self.ai_config.get("prompts", {}).get("invoice_analysis")

            if not prompt:
                raise Exception("invoice_analysis prompt not found in ai_config.json")

            context_data = {}

            print(f"\nDEBUG: Checking context sources...")
            print(f"  db_context (pre-fetched): {self.db_context is not None}")
            print(f"  db_manager (direct access): {self.db_manager is not None}")

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
                except Exception as e:
                    print(f"ERROR processing pre-fetched context: {e}")
                    import traceback
                    traceback.print_exc()
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

            print("\n" + "=" * 80)
            print(f"=== RAW PROMPT SENT TO {provider.upper()} ===")
            print("=" * 80)
            print(full_prompt)
            print("=" * 80)
            print("=== END RAW PROMPT ===")
            print("=" * 80 + "\n")

            print("\n=== DEBUG: Analyzing Invoice ===")
            print(f"Image: {image_path}")
            print(f"Provider: {provider}")
            print(f"Model: {model}")
            print(f"Prompt length: {len(full_prompt)} characters")

            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    raw_response = self._generate_content(
                        prompt_text=full_prompt,
                        image_path=image_path,
                        expect_json=True,
                    )
                    print("\n=== RAW AI RESPONSE ===")
                    print(raw_response)
                    print("=== END RAW RESPONSE ===\n")

                    cleaned_response = self._clean_json_response(raw_response)
                    analysis_data = json.loads(cleaned_response)
                    print("\n=== PARSED JSON DATA ===")
                    print(json.dumps(analysis_data, indent=2))
                    print("=== END PARSED DATA ===\n")
                    return analysis_data
                except Exception as e:
                    last_exception = e
                    error_str = str(e)
                    if any(token in error_str for token in ["503 UNAVAILABLE", "model is overloaded", "429", "temporarily unavailable"]):
                        print(f"AI provider busy (attempt {attempt}/{max_retries}), retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    print(f"Error analyzing invoice: {e}")
                    raise e

            print(f"Error analyzing invoice after {max_retries} retries: {last_exception}")
            raise last_exception
        except Exception as e:
            print(f"Error analyzing invoice: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def _generate_content(self, prompt_text, image_path=None, expect_json=False):
        provider = self.get_provider()
        api_key = self.get_effective_api_key()
        model = self.get_effective_model()
        base_url = self.get_effective_base_url()

        if provider == "openai_compatible":
            return self._call_openai_compatible(prompt_text, model, api_key, base_url, image_path, expect_json)
        return self._call_gemini(prompt_text, model, api_key, image_path)

    def _call_gemini(self, prompt_text, model, api_key, image_path=None):
        try:
            import google.genai as genai
            from google.genai import types
        except ImportError:
            raise Exception("Google GenAI library not installed. Install with: pip install google-genai")

        client = genai.Client(api_key=api_key)
        contents = [prompt_text]
        if image_path:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=self.get_mime_type(image_path)
            )
            contents = [image_part, prompt_text]

        response = client.models.generate_content(model=model, contents=contents)
        response_text = getattr(response, "text", "")
        if not response_text:
            raise Exception("No response from Gemini API")
        return response_text.strip()

    def _call_openai_compatible(self, prompt_text, model, api_key, base_url, image_path=None, expect_json=False):
        if not base_url:
            raise Exception("Custom endpoint/base URL is required for OpenAI-compatible provider")

        normalized_base_url = base_url.rstrip('/')
        if not normalized_base_url.endswith('/v1'):
            normalized_base_url = normalized_base_url + '/v1'

        url = normalized_base_url + '/chat/completions'
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        content_parts = []
        if prompt_text:
            content_parts.append({"type": "text", "text": prompt_text})

        if image_path:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            mime_type = self.get_mime_type(image_path)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                }
            })

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts if image_path else prompt_text
                }
            ]
        }

        if expect_json:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise Exception("No choices returned by OpenAI-compatible endpoint")

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = "\n".join(part for part in text_parts if part).strip()

        if not content:
            raise Exception("No response content returned by OpenAI-compatible endpoint")
        return content.strip()

    def _clean_json_response(self, raw_response):
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        brace_count = 0
        json_end = -1
        for index, char in enumerate(cleaned_response):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = index + 1
                    break

        if json_end > 0 and json_end < len(cleaned_response):
            print(f"Truncating response from {len(cleaned_response)} to {json_end} characters")
            cleaned_response = cleaned_response[:json_end]

        return cleaned_response
