#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - LLM Handler Module
Handles interactions with Google Gemini API using the genai.Client method.
Loads prompt from external file with proper brace escaping and supports configurable model and generation parameters.
Aligned with config.py settings for hygiene categories and cache duration.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from cachetools import TTLCache
import hashlib

# Import Google Gemini library
try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    class MockGenAI:
        class Client:
            def __init__(self, *args, **kwargs): pass
            class Models:
                def generate_content(self, *args, **kwargs):
                    if not all(k in ['model', 'contents'] for k in kwargs):
                        pass
                    if any(k in ['temperature', 'max_output_tokens', 'top_p', 'generation_config'] for k in kwargs):
                        raise TypeError(f"Models.generate_content() got an unexpected keyword argument '{next(k for k in kwargs if k not in ['model', 'contents'])}'")
                    raise NotImplementedError("google-genai library not installed")
            models = Models()
        @staticmethod
        def Client(*args, **kwargs):
            return MockGenAI.Client()
    genai = MockGenAI
    logging.warning("google-genai library not found. LLM features will be unavailable.")

# Import configuration
try:
    import config
except ImportError:
    class MockConfig:
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        ENABLE_LLM_REPORTS = os.environ.get("ENABLE_LLM_REPORTS", "true").lower() == "true"
        HYGIENE_CATEGORIES = [
            'account_security', 'data_sharing', 'device_security', 'social_media', 'browsing_habits'
        ]
        CACHE_DURATION = 3600
        LLM_MODEL_NAME = "gemini-2.0-flash"
        LLM_FALLBACK_MODEL = "gemini-1.5-flash-001"
        LLM_TEMPERATURE = None  # Default to None to match test setup
        LLM_MAX_TOKENS = None   # Default to None to match test setup
    config = MockConfig()
    logging.warning("config.py not found, using environment variables or defaults for LLM handler.")

# Set up logging
logger = logging.getLogger(__name__)

# --- Global Variables ---
_llm_initialized: bool = False
_genai_client: Optional["genai.Client"] = None
_cache = TTLCache(maxsize=100, ttl=getattr(config, 'CACHE_DURATION', 3600))

# --- Initialization ---

def initialize_llm() -> bool:
    """
    Initialize the LLM service using genai.Client and the API key from config.

    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    global _llm_initialized, _genai_client

    _llm_initialized = False
    _genai_client = None

    if not GOOGLE_GENAI_AVAILABLE:
        logger.error("google-genai library is not installed. Cannot initialize LLM.")
        return False

    try:
        api_key = getattr(config, 'GEMINI_API_KEY', None)
        if api_key:
            _genai_client = genai.Client(api_key=api_key)
            logger.info("genai.Client initialized successfully.")
            _llm_initialized = True
        else:
            logger.warning("No Gemini API key found in configuration. LLM features disabled.")
            _llm_initialized = False
    except Exception as e:
        logger.error(f"Failed to initialize genai.Client: {str(e)}", exc_info=True)
        _llm_initialized = False
        _genai_client = None

    if not hasattr(config, 'LLM_MODEL_NAME'):
        logger.info(f"Using MockConfig defaults: LLM_MODEL_NAME={getattr(config, 'LLM_MODEL_NAME', 'N/A')}, "
                   f"LLM_FALLBACK_MODEL={getattr(config, 'LLM_FALLBACK_MODEL', 'N/A')}")

    return _llm_initialized

# --- Availability Check ---

def is_llm_available() -> bool:
    """
    Check if the LLM service library is installed, initialized, and enabled in config.

    Returns:
        bool: True if LLM is available, False otherwise.
    """
    enabled_in_config = getattr(config, 'ENABLE_LLM_REPORTS', False)
    return GOOGLE_GENAI_AVAILABLE and _llm_initialized and _genai_client is not None and enabled_in_config

# --- Core Functionality ---

def generate_hygiene_recommendations(
    overall_score: int,
    category_scores: Dict[str, int],
    strengths: List[str],
    weaknesses: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Generates personalized digital hygiene recommendations using the initialized genai.Client.

    Args:
        overall_score (int): Overall hygiene score (0-100).
        category_scores (dict): Scores for each category (e.g., {"account_security": 75}).
        strengths (list): List of identified strengths.
        weaknesses (list): List of identified weaknesses.

    Returns:
        dict: Recommendations and action plan in JSON format, or None if failed.
    """
    global _genai_client

    if not is_llm_available():
        logger.warning("LLM service not available. Cannot generate recommendations.")
        return None

    # Check cache
    cache_key = hashlib.md5(json.dumps([overall_score, category_scores, strengths, weaknesses], sort_keys=True).encode()).hexdigest()
    if cache_key in _cache:
        logger.info("Returning cached LLM recommendations.")
        return _cache[cache_key]

    # Load prompt from file
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        prompt_path = os.path.join(project_root, 'data', 'llm_hygiene_prompt.json')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
        prompt_template = prompt_data.get('prompt_template', '')
        if not prompt_template:
            logger.error(f"LLM prompt file {prompt_path} is missing 'prompt_template' key.")
            return None
    except FileNotFoundError:
        logger.error(f"LLM prompt file not found at {prompt_path}. Using fallback prompt.")
        prompt_template = """
Ești un expert în securitate digitală. Generează recomandări pentru un utilizator cu:
- Scor general: {overall_score}/100
- Scoruri categorii: {category_scores_json}
- Puncte forte: {strengths_list}
- Puncte slabe: {weaknesses_list}

Returnează un JSON cu recomandări și plan de acțiune în română, folosind ton politicos.
"""
    except Exception as e:
        logger.error(f"Error loading LLM prompt file: {str(e)}", exc_info=True)
        return None

    # Validate prompt template for balanced braces
    brace_count = 0
    for char in prompt_template:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        if brace_count < 0:
            logger.error("Unbalanced braces in prompt template. Aborting.")
            return None
    if brace_count != 0:
        logger.error("Mismatched braces in prompt template. Aborting.")
        return None

    # Format prompt
    try:
        prompt = prompt_template.format(
            overall_score=overall_score,
            category_scores_json=json.dumps(category_scores, indent=2, ensure_ascii=False),
            strengths_list=json.dumps(strengths, indent=2, ensure_ascii=False),
            weaknesses_list=json.dumps(weaknesses, indent=2, ensure_ascii=False)
        )
        logger.debug(f"Generated LLM prompt (length: {len(prompt)} chars):\n{prompt[:500]}...")
    except KeyError as ke:
        logger.error(f"KeyError formatting prompt: {str(ke)}. Problematic template snippet:\n{prompt_template[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Error formatting prompt: {str(e)}", exc_info=True)
        return None

    try:
        model_name = getattr(config, 'LLM_MODEL_NAME', 'gemini-2.0-flash')
        logger.info(f"Sending request to model '{model_name}'.")

        if _genai_client is None:
            logger.error("LLM client object is None. Cannot make request.")
            return None

        # Validate model availability
        available_models = _genai_client.list_models() if hasattr(_genai_client, 'list_models') else []
        available_model_names = [m.name for m in available_models] if available_models else []
        if model_name not in available_model_names:
            logger.warning(f"Model '{model_name}' not available. Trying fallback model.")
            model_name = getattr(config, 'LLM_FALLBACK_MODEL', 'gemini-1.5-flash-001')

        # Prepare API call
        kwargs = {"model": model_name, "contents": prompt}
        temperature = getattr(config, 'LLM_TEMPERATURE', None)
        max_tokens = getattr(config, 'LLM_MAX_TOKENS', None)
        if temperature is not None or max_tokens is not None:
            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            kwargs["generation_config"] = generation_config

        response = _genai_client.models.generate_content(**kwargs)
        logger.info("Received response from Gemini.")

        # Log token usage if available
        if hasattr(response, 'usage_metadata'):
            token_info = response.usage_metadata
            logger.info(f"Token usage: prompt={token_info.get('prompt_token_count', 'N/A')}, "
                       f"response={token_info.get('candidates_token_count', 'N/A')}, "
                       f"total={token_info.get('total_token_count', 'N/A')}")

        # Extract and parse JSON
        if hasattr(response, 'text') and response.text:
            parsed_json = _extract_json_from_llm_response(response.text)
            if parsed_json:
                _cache[cache_key] = parsed_json
                return parsed_json
        else:
            block_reason = None
            if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                block_reason = response.prompt_feedback.block_reason
            elif hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != 'STOP':
                block_reason = response.candidates[0].finish_reason
            if block_reason:
                logger.warning(f"Gemini request blocked or failed. Reason: {block_reason}")
            else:
                logger.warning("LLM response received, but it contains no text content.")
                logger.debug(f"Full LLM Response structure: {response}")
            return None

    except AttributeError as ae:
        if 'generate_content' in str(ae):
            logger.error(f"AttributeError calling generate_content: {ae}. Is 'models' attribute correct?", exc_info=True)
        else:
            logger.error(f"AttributeError during client call: {ae}", exc_info=True)
        # Try fallback model
        fallback_model = getattr(config, 'LLM_FALLBACK_MODEL', 'gemini-1.5-flash-001')
        if fallback_model and fallback_model != model_name:
            logger.info(f"Retrying with fallback model '{fallback_model}'.")
            kwargs["model"] = fallback_model
            try:
                response = _genai_client.models.generate_content(**kwargs)
                if hasattr(response, 'text') and response.text:
                    parsed_json = _extract_json_from_llm_response(response.text)
                    if parsed_json:
                        _cache[cache_key] = parsed_json
                        return parsed_json
            except Exception as e:
                logger.error(f"Error with fallback model: {str(e)}", exc_info=True)
        return None
    except TypeError as te:
        logger.error(f"TypeError during client call: {te}. Likely an unexpected argument.", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error generating hygiene recommendations via LLM: {str(e)}", exc_info=True)
        return None

# --- Helper Function ---

def _extract_json_from_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts a JSON object from the LLM's raw text response.
    Handles potential markdown fences and parsing errors.

    Args:
        response_text: The raw string response from the LLM.

    Returns:
        The parsed dictionary if successful, None otherwise.
    """
    if not response_text:
        logger.warning("LLM response text is empty, cannot extract JSON.")
        return None
    try:
        processed_text = response_text.strip()
        if processed_text.startswith("```json"):
            processed_text = processed_text[7:]
            if processed_text.endswith("```"):
                processed_text = processed_text[:-3]
            processed_text = processed_text.strip()
        json_start = processed_text.find('{')
        json_end = processed_text.rfind('}') + 1
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_string = processed_text[json_start:json_end]
            parsed_json = json.loads(json_string)
            # Validate JSON structure
            required_keys = {"recommendations", "action_plan"}
            action_plan_keys = {"immediate", "short_term", "long_term"}
            missing_keys = required_keys - set(parsed_json.keys())
            if missing_keys:
                logger.warning(f"Parsed JSON missing required keys: {missing_keys}")
                logger.debug(f"Parsed JSON content: {parsed_json}")
                return None
            if not isinstance(parsed_json["recommendations"], list):
                logger.warning("Parsed JSON 'recommendations' is not a list.")
                return None
            if not isinstance(parsed_json["action_plan"], dict):
                logger.warning("Parsed JSON 'action_plan' is not a dict.")
                return None
            missing_action_keys = action_plan_keys - set(parsed_json["action_plan"].keys())
            if missing_action_keys:
                logger.warning(f"Parsed JSON 'action_plan' missing keys: {missing_action_keys}")
                return None
            # Validate recommendation categories
            valid_categories = set(getattr(config, 'HYGIENE_CATEGORIES', []))
            for rec in parsed_json["recommendations"]:
                if rec.get("category") not in valid_categories:
                    logger.warning(f"Invalid category '{rec.get('category')}' in recommendation. Valid: {valid_categories}")
                    return None
            return parsed_json
        else:
            logger.warning("Could not find valid JSON object delimiters '{' and '}' in LLM response.")
            logger.debug(f"Processed text for JSON extraction: {processed_text}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        log_snippet = processed_text[(json_start if 'json_start' in locals() and json_start != -1 else 0):(json_end if 'json_end' in locals() and json_end != -1 else len(processed_text))]
        logger.debug(f"Problematic text snippet for JSON parsing: {log_snippet[:500]}...")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during JSON extraction: {e}", exc_info=True)
        return None

# --- Example Usage (Optional - for testing this module directly) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Attempting to initialize LLM for standalone test...")
    if not getattr(config, 'GEMINI_API_KEY', None) and "GEMINI_API_KEY" not in os.environ:
        print("\nERROR: Set GEMINI_API_KEY environment variable or ensure config.py has it.\n")
        llm_init_success = False
    else:
        if "GEMINI_API_KEY" in os.environ:
            config.GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
        llm_init_success = initialize_llm()

    logger.info(f"LLM Initialization attempt result: {llm_init_success}")

    if llm_init_success:
        logger.info("LLM Initialized successfully for test.")
        test_scores = {
            "account_security": 35, "data_sharing": 50, "device_security": 60,
            "social_media": 40, "browsing_habits": 70
        }
        test_strengths = ["Folosește actualizări regulate pe dispozitive", "Evită Wi-Fi public nesigur"]
        test_weaknesses = ["Parole slabe sau refolosite", "Nu folosește autentificare cu 2 factori (2FA)", "Setări de confidențialitate social media permisive"]
        test_overall = 51

        logger.info("Attempting to generate hygiene recommendations...")
        recommendations_data = generate_hygiene_recommendations(
            overall_score=test_overall,
            category_scores=test_scores,
            strengths=test_strengths,
            weaknesses=test_weaknesses
        )

        if recommendations_data:
            logger.info("Successfully received recommendations data:")
            print(json.dumps(recommendations_data, indent=2, ensure_ascii=False))
        else:
            logger.error("Failed to generate recommendations (returned None).")
    else:
        logger.warning("LLM Initialization failed or skipped. Cannot run recommendation generation test.")