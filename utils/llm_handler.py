#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - LLM Handler Module
Handles interactions with Google Gemini API.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from cachetools import TTLCache
import hashlib

# 1. Inițializează logger-ul modulului PRIMUL
logger = logging.getLogger(__name__)

# 2. Încearcă să imporți configurația principală și stabilește app_config_module
app_config_module = None # Va fi fie modulul config real, fie o instanță MockConfigLLM

logger.debug("llm_handler.py: Attempting to import main application config...")
try:
    # Prioritizează importul absolut, care funcționează când app.py rulează din rădăcină
    import config as actual_config_module
    app_config_module = actual_config_module
    logger.info(f"llm_handler.py: Successfully imported main application config using absolute 'import config'. Module: {app_config_module}")
except ImportError as e_abs:
    logger.error(f"llm_handler.py: FAILED to import main config using absolute 'import config'. Error: {e_abs}", exc_info=True)
    try:
        logger.debug("llm_handler.py: Attempting relative import 'from .. import config' as fallback...")
        from .. import config as relative_config_module
        app_config_module = relative_config_module
        logger.info(f"llm_handler.py: Successfully imported main config using relative 'from .. import config'. Module: {app_config_module}")
    except ImportError as e_rel:
        logger.error(f"llm_handler.py: FAILED to import main config using relative 'from .. import config'. Error: {e_rel}", exc_info=True)
        logger.warning("llm_handler.py: All attempts to import main config.py failed. Falling back to MockConfigLLM.")
        
        class MockConfigLLM:
            logger.info("llm_handler.py: Defining MockConfigLLM.")
            GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
            ENABLE_LLM_REPORTS = os.environ.get("ENABLE_LLM_REPORTS", "true").lower() == "true"
            LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gemini-1.5-flash-latest") # Un default stabil
            LLM_FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "gemini-1.5-pro-latest") # Un alt default stabil
            LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", 0.7))
            LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", 4096))
            CACHE_DURATION = int(os.environ.get("LLM_CACHE_DURATION", 3600))
            HYGIENE_CATEGORIES = json.loads(os.environ.get("HYGIENE_CATEGORIES", '["account_security", "data_sharing", "device_security", "social_media", "browsing_habits"]'))
        
        app_config_module = MockConfigLLM()

# Verificare finală dacă app_config_module este setat
if app_config_module is None:
    logger.critical("llm_handler.py: CRITICAL - app_config_module is None. This should not happen. LLM handler cannot function.")
    # Creează un mock de urgență pentru a preveni AttributeError în aval, deși problema e gravă
    class EmergencyMock:
        GEMINI_API_KEY = None; ENABLE_LLM_REPORTS = False; LLM_MODEL_NAME = "emergency_mock";
        LLM_FALLBACK_MODEL = "emergency_mock"; LLM_TEMPERATURE = 0.0; LLM_MAX_TOKENS = 1;
        CACHE_DURATION = 1; HYGIENE_CATEGORIES = []
    app_config_module = EmergencyMock()

# Loghează configurația efectivă cu care va opera acest modul
logger.info(f"llm_handler.py: Operating with config object: {type(app_config_module)} ({app_config_module})")
logger.info(f"  LLM_MODEL_NAME: '{getattr(app_config_module, 'LLM_MODEL_NAME', 'N/A')}'")
logger.info(f"  LLM_FALLBACK_MODEL: '{getattr(app_config_module, 'LLM_FALLBACK_MODEL', 'N/A')}'")
logger.info(f"  GEMINI_API_KEY Present: {bool(getattr(app_config_module, 'GEMINI_API_KEY', None))}")
logger.info(f"  ENABLE_LLM_REPORTS: {getattr(app_config_module, 'ENABLE_LLM_REPORTS', False)}")
logger.info(f"  LLM_TEMPERATURE: {getattr(app_config_module, 'LLM_TEMPERATURE', 'N/A')}")
logger.info(f"  LLM_MAX_TOKENS: {getattr(app_config_module, 'LLM_MAX_TOKENS', 'N/A')}")
logger.info(f"  CACHE_DURATION: {getattr(app_config_module, 'CACHE_DURATION', 'N/A')}")


# 3. Importă biblioteca google.generativeai DUPĂ ce app_config_module este stabilit
try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
    logger.info("llm_handler.py: google.generativeai library imported successfully.")
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    class MockGenerativeModel: # Mock pentru genai.GenerativeModel
        def generate_content(self, *args, **kwargs):
            logger.error("MockGenerativeModel.generate_content called - google.generativeai not installed.")
            raise NotImplementedError("google.generativeai not installed or mock in use")
        def start_chat(self, *args, **kwargs): # Adăugat pentru completitudine
            logger.error("MockGenerativeModel.start_chat called - google.generativeai not installed.")
            raise NotImplementedError("google.generativeai not installed or mock in use")

    class MockGenAIModule: # Mock pentru modulul genai
        def configure(self, *args, **kwargs): logger.info("MockGenAIModule.configure called.")
        def list_models(self): logger.info("MockGenAIModule.list_models called."); return []
        def GenerativeModel(self, model_name: str):
            logger.info(f"MockGenAIModule.GenerativeModel called for '{model_name}'.")
            return MockGenerativeModel()
        class types: # Mock pentru genai.types
            @staticmethod
            def GenerationConfig(**kwargs): return kwargs # Simplu
    genai = MockGenAIModule()
    logger.warning("llm_handler.py: google-generativeai library not found. LLM features will be based on mocks.")


# --- Variabile Globale Specifice LLM ---
_llm_service_initialized: bool = False # Redenumit pentru claritate
_active_generative_model: Optional[genai.GenerativeModel] = None
_active_model_name_used_for_api: Optional[str] = None # Numele trimis la genai.GenerativeModel()
_available_api_model_names: List[str] = [] # Numele de la API (cu 'models/')
_llm_cache = TTLCache(maxsize=100, ttl=getattr(app_config_module, 'CACHE_DURATION', 3600))


# --- Inițializarea Serviciului LLM ---
def initialize_llm() -> bool:
    global _llm_service_initialized, _active_generative_model, _active_model_name_used_for_api, _available_api_model_names

    logger.info("llm_handler.py: initialize_llm() called.")
    _llm_service_initialized = False
    _active_generative_model = None
    _active_model_name_used_for_api = None
    _available_api_model_names = []

    if not GOOGLE_GENAI_AVAILABLE:
        logger.error("llm_handler.py: google-generativeai library not available. Cannot initialize LLM service.")
        return False

    api_key = getattr(app_config_module, 'GEMINI_API_KEY', None)
    if not api_key:
        logger.warning("llm_handler.py: No GEMINI_API_KEY found in configuration. LLM service cannot be initialized.")
        return False

    try:
        genai.configure(api_key=api_key)
        logger.info("llm_handler.py: google.generativeai configured successfully with API key.")

        # Populează lista de modele disponibile
        try:
            models_from_api = genai.list_models()
            _available_api_model_names = [
                m.name for m in models_from_api if 'generateContent' in m.supported_generation_methods
            ]
            logger.info(f"llm_handler.py: Fetched available generative models from API: {_available_api_model_names}")
            if not _available_api_model_names:
                logger.warning("llm_handler.py: No generative models found available from the API after filtering.")
        except Exception as list_e:
            logger.error(f"llm_handler.py: Failed to list models from API: {list_e}", exc_info=True)
        
        _llm_service_initialized = True
        logger.info("llm_handler.py: LLM service initialization successful.")
    except Exception as e:
        logger.error(f"llm_handler.py: Failed to configure google.generativeai or list models: {e}", exc_info=True)
        _llm_service_initialized = False
    
    return _llm_service_initialized


# --- Verificarea Disponibilității Serviciului ---
def is_llm_available() -> bool:
    # Folosește variabila globală corectă
    enabled_in_config = getattr(app_config_module, 'ENABLE_LLM_REPORTS', False)
    # Verifică și dacă _llm_service_initialized este True
    available = GOOGLE_GENAI_AVAILABLE and _llm_service_initialized and enabled_in_config
    logger.debug(f"llm_handler.py: is_llm_available() -> {available} (Lib: {GOOGLE_GENAI_AVAILABLE}, Init: {_llm_service_initialized}, ConfigEnable: {enabled_in_config})")
    return available


# --- Helper pentru verificarea numelui modelului în lista API ---
def _is_model_name_in_api_list(model_name_from_config: str, api_model_list: List[str]) -> bool:
    if not model_name_from_config: return False
    expected_api_name = f"models/{model_name_from_config}" # Numele din config e FĂRĂ 'models/'
    return expected_api_name in api_model_list


# --- Helper pentru a obține/crea instanța modelului activ ---
def _get_active_generative_model() -> Optional[genai.GenerativeModel]:
    global _active_generative_model, _active_model_name_used_for_api, _available_api_model_names

    if _active_generative_model: # Returnează instanța cache-uită dacă există
        logger.debug(f"llm_handler.py: Returning cached active model instance: '{_active_model_name_used_for_api}'")
        return _active_generative_model

    if not _llm_service_initialized: # Ar trebui prins de is_llm_available()
        logger.error("llm_handler.py: LLM service not initialized. Cannot get model instance.")
        return None

    # Obține numele modelelor din app_config_module (care este config.py real sau MockConfigLLM)
    primary_config_name = getattr(app_config_module, 'LLM_MODEL_NAME', "gemini-1.5-flash-latest")
    fallback_config_name = getattr(app_config_module, 'LLM_FALLBACK_MODEL', "gemini-1.5-pro-latest")
    
    selected_model_for_api = None

    if _is_model_name_in_api_list(primary_config_name, _available_api_model_names):
        selected_model_for_api = primary_config_name
        logger.info(f"llm_handler.py: Primary model '{primary_config_name}' (verified as 'models/{primary_config_name}') is available. Selecting.")
    else:
        logger.warning(f"llm_handler.py: Primary model '{primary_config_name}' (expected as 'models/{primary_config_name}') not found in API list: {_available_api_model_names}. Trying fallback.")
        if _is_model_name_in_api_list(fallback_config_name, _available_api_model_names):
            selected_model_for_api = fallback_config_name
            logger.info(f"llm_handler.py: Fallback model '{fallback_config_name}' (verified as 'models/{fallback_config_name}') is available. Selecting.")
        else:
            logger.error(f"llm_handler.py: Fallback model '{fallback_config_name}' (expected as 'models/{fallback_config_name}') also not found in API list. Cannot select model.")
            return None

    if not selected_model_for_api:
        logger.error("llm_handler.py: No valid LLM model could be selected after checks.")
        return None

    try:
        logger.info(f"llm_handler.py: Attempting to initialize genai.GenerativeModel with: '{selected_model_for_api}'")
        # Folosim numele FĂRĂ 'models/' pentru a crea instanța modelului
        _active_generative_model = genai.GenerativeModel(selected_model_for_api)
        _active_model_name_used_for_api = selected_model_for_api
        logger.info(f"llm_handler.py: Successfully initialized genai.GenerativeModel: '{_active_model_name_used_for_api}'")
        return _active_generative_model
    except Exception as e:
        logger.error(f"llm_handler.py: Failed to initialize genai.GenerativeModel with '{selected_model_for_api}': {e}", exc_info=True)
        _active_generative_model = None
        _active_model_name_used_for_api = None
        return None


# --- Funcția Principală de Generare Recomandări ---
def generate_hygiene_recommendations(
    overall_score: int,
    category_scores: Dict[str, int],
    strengths: List[str],
    weaknesses: List[str]
) -> Optional[Dict[str, Any]]:

    logger.debug(f"llm_handler.py: generate_hygiene_recommendations called with score {overall_score}.")
    if not is_llm_available(): # Verifică la începutul funcției publice
        logger.warning("llm_handler.py: LLM service not available (checked by generate_hygiene_recommendations).")
        return None

    active_model = _get_active_generative_model()
    if not active_model:
        logger.error("llm_handler.py: Could not get an active LLM model instance for recommendations.")
        return None

    # Cheia cache include numele modelului folosit, pentru a permite schimbarea modelului
    cache_key_params = [_active_model_name_used_for_api, overall_score, category_scores, strengths, weaknesses]
    cache_key = hashlib.md5(json.dumps(cache_key_params, sort_keys=True).encode()).hexdigest()
    
    if cache_key in _llm_cache:
        logger.info(f"llm_handler.py: Returning cached LLM recommendations for model '{_active_model_name_used_for_api}'.")
        return _llm_cache[cache_key]

    # Load prompt (logica ta originală de încărcare prompt este bună)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir) # utils -> rădăcină
        prompt_path = os.path.join(project_root, 'data', 'llm_hygiene_prompt.json')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
        prompt_template = prompt_data.get('prompt_template', '')
        if not prompt_template:
            logger.error(f"llm_handler.py: LLM prompt file {prompt_path} is missing 'prompt_template' key.")
            return None
    except FileNotFoundError:
        logger.error(f"llm_handler.py: LLM prompt file not found at {prompt_path}. Cannot generate prompt.")
        return None # Important să returnezi None dacă promptul nu e găsit
    except Exception as e:
        logger.error(f"llm_handler.py: Error loading LLM prompt file: {e}", exc_info=True)
        return None

    # Format prompt (logica ta originală de formatare este bună)
    try:
        prompt = prompt_template.format(
            overall_score=overall_score,
            category_scores_json=json.dumps(category_scores, indent=2, ensure_ascii=False),
            strengths_list=json.dumps(strengths, indent=2, ensure_ascii=False),
            weaknesses_list=json.dumps(weaknesses, indent=2, ensure_ascii=False)
        )
        logger.debug(f"llm_handler.py: Generated LLM prompt for model '{_active_model_name_used_for_api}' (len: {len(prompt)}):\n{prompt[:300]}...")
    except Exception as e: # Prinde orice eroare de formatare
        logger.error(f"llm_handler.py: Error formatting LLM prompt: {e}", exc_info=True)
        return None
        
    try:
        # Obține parametrii de generare din app_config_module
        temperature = getattr(app_config_module, 'LLM_TEMPERATURE', None)
        max_tokens = getattr(app_config_module, 'LLM_MAX_TOKENS', None)
        
        gen_config_params = {}
        if temperature is not None: gen_config_params["temperature"] = float(temperature)
        if max_tokens is not None: gen_config_params["max_output_tokens"] = int(max_tokens)
        
        final_generation_config = genai.types.GenerationConfig(**gen_config_params) if gen_config_params else None

        logger.info(f"llm_handler.py: Sending request to model '{_active_model_name_used_for_api}' with gen_config: {gen_config_params if gen_config_params else 'None'}")
        
        response = active_model.generate_content(
            contents=prompt,
            generation_config=final_generation_config
        )
        logger.info(f"llm_handler.py: Received response from Gemini model '{_active_model_name_used_for_api}'.")

        # Log token usage (logica ta originală e bună)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            token_info = response.usage_metadata
            logger.info(f"  Token usage: prompt={getattr(token_info, 'prompt_token_count', 'N/A')}, "
                       f"candidates={getattr(token_info, 'candidates_token_count', 'N/A')}, "
                       f"total={getattr(token_info, 'total_token_count', 'N/A')}")

        # Procesează răspunsul (logica ta cu verificarea finish_reason este bună și ar trebui integrată aici)
        if not response.candidates:
            logger.warning(f"llm_handler.py: LLM response from model '{_active_model_name_used_for_api}' has no candidates.")
            if response.prompt_feedback: logger.warning(f"  Prompt Feedback: {response.prompt_feedback.block_reason}")
            return None

        candidate = response.candidates[0]
        finish_reason_enum = candidate.finish_reason
        finish_reason_name = finish_reason_enum.name # ex: "STOP", "MAX_TOKENS"

        logger.info(f"llm_handler.py: Candidate finish reason: {finish_reason_name} (Value: {finish_reason_enum.value})")

        if finish_reason_name == 'STOP':
            # Încearcă să accesezi response.text, dar fii pregătit pentru ValueError
            try:
                response_text_content = response.text 
                if not response_text_content: # Verificare suplimentară dacă .text e gol
                    logger.warning(f"llm_handler.py: response.text is empty despite finish_reason STOP for model '{_active_model_name_used_for_api}'.")
                    return None
                
                parsed_json = _extract_json_from_llm_response(response_text_content)
                if parsed_json:
                    _llm_cache[cache_key] = parsed_json
                    return parsed_json
                else:
                    logger.warning(f"llm_handler.py: Failed to extract JSON from response text (finish_reason STOP) for model '{_active_model_name_used_for_api}'.")
                    return None
            except ValueError as ve: # Eroarea specifică de la .text
                logger.error(f"llm_handler.py: ValueError accessing response.text for model '{_active_model_name_used_for_api}' (finish_reason: {finish_reason_name}): {ve}", exc_info=False) # exc_info=False pentru a nu fi prea verbos
                # Poți încerca să construiești textul manual din parts dacă e necesar și dacă structura e cunoscută
                # texts = [part.text for part in candidate.content.parts if hasattr(part, 'text')] ...
                return None
        else: # MAX_TOKENS, SAFETY, RECITATION, OTHER, UNSPECIFIED
            logger.warning(f"llm_handler.py: LLM generation for model '{_active_model_name_used_for_api}' did not finish with STOP. Reason: {finish_reason_name}.")
            if finish_reason_name == 'MAX_TOKENS':
                 logger.warning(f"  Consider increasing LLM_MAX_TOKENS (current in config: {getattr(app_config_module, 'LLM_MAX_TOKENS', 'N/A')}) or refining the prompt.")
            elif finish_reason_name == 'SAFETY':
                 logger.warning(f"  Safety ratings: {candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else 'N/A'}")
            logger.debug(f"  Full LLM Response structure: {response}")
            return None

    except Exception as e:
        logger.error(f"llm_handler.py: Unexpected error during LLM API call or response processing with model '{_active_model_name_used_for_api}': {e}", exc_info=True)
        return None


# --- Helper Function _extract_json_from_llm_response ---
def _extract_json_from_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    if not response_text:
        logger.warning("llm_handler.py: _extract_json_from_llm_response called with empty text.")
        return None
    logger.debug(f"llm_handler.py: Attempting to extract JSON from text (len: {len(response_text)}): '{response_text[:200]}...'")
    try:
        processed_text = response_text.strip()
        if processed_text.startswith("```json"):
            processed_text = processed_text[7:]
            if processed_text.endswith("```"):
                processed_text = processed_text[:-3]
            processed_text = processed_text.strip()
        
        # Căutare mai robustă a primului obiect JSON valid și complet
        json_start_index = -1
        brace_level = 0
        for i, char in enumerate(processed_text):
            if char == '{':
                if brace_level == 0:
                    json_start_index = i
                brace_level += 1
            elif char == '}':
                if brace_level > 0: # Asigură-te că nu e o acoladă închisă fără una deschisă
                    brace_level -= 1
                    if brace_level == 0 and json_start_index != -1:
                        # Am găsit un potențial obiect JSON complet
                        json_string_candidate = processed_text[json_start_index : i + 1]
                        try:
                            parsed_json = json.loads(json_string_candidate)
                            # --- Validarea ta originală a structurii JSON este bună ---
                            required_keys = {"recommendations", "action_plan"}
                            action_plan_keys = {"immediate", "short_term", "long_term"}
                            
                            if not required_keys.issubset(parsed_json.keys()):
                                logger.warning(f"llm_handler.py: Parsed JSON missing required keys. Found: {list(parsed_json.keys())}, Required: {required_keys}. Candidate: {json_string_candidate[:100]}...")
                                continue # Caută următorul JSON potențial dacă acesta nu e bun

                            if not isinstance(parsed_json.get("recommendations"), list) or \
                               not isinstance(parsed_json.get("action_plan"), dict):
                                logger.warning(f"llm_handler.py: Parsed JSON 'recommendations' or 'action_plan' has incorrect type. Candidate: {json_string_candidate[:100]}...")
                                continue

                            if not action_plan_keys.issubset(parsed_json["action_plan"].keys()):
                                logger.warning(f"llm_handler.py: Parsed JSON 'action_plan' missing keys. Found: {list(parsed_json['action_plan'].keys())}, Required: {action_plan_keys}. Candidate: {json_string_candidate[:100]}...")
                                continue
                            
                            valid_categories = set(getattr(app_config_module, 'HYGIENE_CATEGORIES', []))
                            all_recs_valid = True
                            for rec in parsed_json["recommendations"]:
                                if not isinstance(rec, dict) or rec.get("category") not in valid_categories:
                                    logger.warning(f"llm_handler.py: Invalid category '{rec.get('category')}' in recommendation. Valid: {valid_categories}. Rec: {rec}")
                                    all_recs_valid = False
                                    break
                            if not all_recs_valid:
                                continue
                            
                            logger.info("llm_handler.py: Successfully parsed and validated JSON from LLM response.")
                            return parsed_json # Am găsit un JSON valid și complet
                        except json.JSONDecodeError:
                            logger.debug(f"llm_handler.py: JSONDecodeError for substring: '{json_string_candidate[:100]}...'. Continuing search.")
                            # Continuă căutarea dacă un substring nu e valid
                # Dacă brace_level devine negativ sau json_start_index e -1 și întâlnim '}', e o problemă
                elif json_start_index != -1: # brace_level e 0 dar am avut un json_start valid
                    logger.debug(f"llm_handler.py: Resetting JSON search due to unexpected '}}' at index {i} while brace_level is 0.")
                    json_start_index = -1 # Resetează căutarea
                    brace_level = 0 # Asigură-te că e resetat

        logger.warning("llm_handler.py: Could not find a valid, complete JSON object in LLM response after parsing.")
        logger.debug(f"  Full processed text for JSON extraction: {processed_text[:500]}...")
        return None
    except Exception as e:
        logger.error(f"llm_handler.py: An unexpected error occurred during JSON extraction: {e}", exc_info=True)
        logger.debug(f"  Original response text for JSON extraction: {response_text[:500]}...")
        return None


# --- Example Usage (Optional - pentru testare directă) ---
if __name__ == '__main__':
    # Setează un format de logging mai detaliat pentru testare directă
    logging.basicConfig(
        level=logging.DEBUG, # Setează la DEBUG pentru a vedea toate mesajele
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger_main = logging.getLogger("llm_handler_standalone_test")

    logger_main.info("Attempting to initialize LLM for standalone test...")
    
    # Pentru testare directă, asigură-te că GEMINI_API_KEY este disponibil
    # app_config_module ar trebui să fie deja setat (fie config real, fie MockConfigLLM)
    if not getattr(app_config_module, 'GEMINI_API_KEY', None):
        logger_main.error("GEMINI_API_KEY not found in loaded configuration (app_config_module). "
                          "Set it in your main config.py or as an environment variable if using MockConfigLLM fallback.")
        llm_init_success = False
    else:
        llm_init_success = initialize_llm()

    logger_main.info(f"LLM Initialization attempt result: {llm_init_success}")

    if is_llm_available(): # Folosește funcția de verificare
        logger_main.info("LLM Initialized successfully and is available for test.")
        test_scores = {
            "account_security": 35, "data_sharing": 50, "device_security": 60,
            "social_media": 40, "browsing_habits": 70
        }
        test_strengths = ["Folosește actualizări regulate pe dispozitive", "Evită Wi-Fi public nesigur"]
        test_weaknesses = ["Parole slabe sau refolosite", "Nu folosește autentificare cu 2 factori (2FA)", "Setări de confidențialitate social media permisive"]
        test_overall = 51

        logger_main.info("Attempting to generate hygiene recommendations...")
        recommendations_data = generate_hygiene_recommendations(
            overall_score=test_overall,
            category_scores=test_scores,
            strengths=test_strengths,
            weaknesses=test_weaknesses
        )

        if recommendations_data:
            logger_main.info("Successfully received recommendations data:")
            # Folosește logger pentru output consistent, sau print dacă preferi
            logger_main.info(json.dumps(recommendations_data, indent=2, ensure_ascii=False))
        else:
            logger_main.error("Failed to generate recommendations (returned None). Check previous logs for details.")
    else:
        logger_main.warning("LLM Initialization failed or LLM is not available. Cannot run recommendation generation test.")