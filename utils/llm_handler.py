#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - LLM Handler Module (Adaptat la Client API funcțional)
Handles interactions with Google Gemini API using the genai.Client method,
bazat pe testul funcțional furnizat. Parametrii extra de generare (temp, etc.)
NU sunt specificați în apelul API.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List

# Importăm biblioteca Google - stilul Client
try:
    from google import genai
    # Tipurile s-ar putea să nu mai fie necesare dacă nu folosim GenerationConfig
    # from google.genai import types as genai_types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    # Clase placeholder
    class MockGenAI:
        class Client:
            def __init__(self, *args, **kwargs): pass
            class Models:
                 def generate_content(self, *args, **kwargs):
                      # Verificăm doar argumentele de bază așteptate
                      if not all(k in ['model', 'contents'] for k in kwargs):
                            pass # Simulăm că merge dacă sunt doar astea
                      # Verificăm dacă se trimit parametrii interziși
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
    config = MockConfig()
    logging.warning("config.py not found, using environment variables or defaults for LLM handler.")

# Set up logging
logger = logging.getLogger(__name__)

# --- Global Variables ---
_llm_initialized: bool = False
# ---=== REINTRODUCEM CLIENTUL GLOBAL ===---
#_genai_client: Optional["genai.Client"] = None# ---=== SFÂRȘIT REINTRODUCERE ===---
_default_model_name: str = "gemini-1.5-flash-001" # Nume scurt

# --- Initialization ---

def initialize_llm() -> bool:
    """
    Initialize the LLM service using genai.Client and the API key from config.
    (Revenim la metoda Client)
    """
    global _llm_initialized, _genai_client # Adăugăm _genai_client în global

    _llm_initialized = False
    _genai_client = None # Resetăm clientul

    if not GOOGLE_GENAI_AVAILABLE:
        logger.error("google-genai library is not installed. Cannot initialize LLM.")
        return False

    try:
        api_key = getattr(config, 'GEMINI_API_KEY', None)
        if api_key:
            try:
                # ---=== REVENIM LA CREAREA CLIENTULUI ===---
                _genai_client = genai.Client(api_key=api_key)
                # ---=== SFÂRȘIT REVENIRE ===---
                logger.info("genai.Client initialized successfully.")
                _llm_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize genai.Client: {str(e)}", exc_info=True)
                _llm_initialized = False
                _genai_client = None
        else:
            logger.warning("No Gemini API key found in configuration. LLM features disabled.")
            _llm_initialized = False
    except Exception as e:
        logger.error(f"An unexpected error occurred during LLM initialization: {str(e)}", exc_info=True)
        _llm_initialized = False
        _genai_client = None

    return _llm_initialized

# --- Availability Check ---

def is_llm_available() -> bool:
    """
    Check if the LLM service library is installed, initialized (client exists),
    and LLM reports are enabled in config.
    (Reintroducem verificarea _genai_client)
    """
    enabled_in_config = getattr(config, 'ENABLE_LLM_REPORTS', False)
    # ---=== REINTRODUCEM VERIFICAREA CLIENTULUI ===---
    return GOOGLE_GENAI_AVAILABLE and _llm_initialized and _genai_client is not None and enabled_in_config
    # ---=== SFÂRȘIT REINTRODUCERE ===---

# --- Core Functionality ---

def generate_hygiene_recommendations(
    overall_score: int,
    category_scores: Dict[str, int],
    strengths: List[str],
    weaknesses: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Generates personalized digital hygiene recommendations using the initialized
    genai.Client and the models.generate_content method WITHOUT extra parameters.

    Args:
        #... (argumentele rămân la fel)

    Returns:
        #... (returul rămâne la fel: Optional[Dict])
    """
    global _genai_client, _default_model_name # Avem nevoie de client și model

    if not is_llm_available():
        logger.warning("LLM service not available. Cannot generate recommendations.")
        return None

    # Construct the detailed prompt (identic ca înainte)
    prompt = f"""
Ești un expert în securitate digitală și igienă online. Analizează următoarele date despre evaluarea unui utilizator:

Scor General: {overall_score}/100
Scoruri pe Categorii:
{json.dumps(category_scores, indent=2, ensure_ascii=False)}
Puncte Forte Identificate:
{json.dumps(strengths, indent=2, ensure_ascii=False)}
Puncte Slabe Identificate:
{json.dumps(weaknesses, indent=2, ensure_ascii=False)}

**Sarcina Ta:**
Generează un set de recomandări personalizate și un plan de acțiune pentru a ajuta utilizatorul să-și îmbunătățească igiena digitală. Concentrează-te pe abordarea punctelor slabe.

**Formatul Obligatoriu de Răspuns:**
Returnează **doar** un obiect JSON valid, fără niciun alt text înainte sau după el. Structura JSON trebuie să fie exact aceasta:

{{
  "recommendations": [
    {{
      "category": "numele_categoriei_relevante",
      "recommendation": "Textul clar și specific al recomandării în limba română.",
      "priority": "high|medium|low"
    }}
  ],
  "action_plan": {{
    "immediate": [
      "Acțiune specifică 1, urgentă (corespunde priorității high)."
    ],
    "short_term": [
      "Acțiune specifică 1, de făcut în următoarele săptămâni (corespunde priorității medium)."
    ],
    "long_term": [
      "Acțiune specifică 1, de menținere sau cu impact pe termen lung (corespunde priorității low)."
    ]
  }}
}}

**Instrucțiuni Suplimentare:**
- Asigură-te că recomandările sunt direct legate de punctele slabe.
- Prioritizează recomandările: 'high' pentru riscuri majore, 'medium' pentru probleme importante, 'low' pentru bune practici generale.
- Planul de acțiune trebuie să reflecte prioritățile recomandărilor.
- Include între 4 și 6 recomandări în total.
- Include 1-2 acțiuni pentru fiecare secțiune a planului de acțiune (immediate, short_term, long_term).
- Folosește limba română.
"""

    try:
        # ---=== CORE ADAPTATION ===---
        # NU mai definim generation_config sau parametrii individuali

        logger.info(f"Sending request via Client.models.generate_content to model '{_default_model_name}' (using default generation parameters).")

        # Asigurăm că _genai_client nu e None
        if _genai_client is None:
             logger.error("LLM client object is None. Cannot make request.")
             return None

        # APELUL API - Folosind metoda din testul tău, FĂRĂ parametrii extra
        response = _genai_client.models.generate_content(
            model=_default_model_name, # Numele scurt al modelului
            contents=prompt
            # NU ADAUGĂM temperature, max_output_tokens, etc. aici!
        )
        # ---=== END CORE ADAPTATION ===---

        logger.info("Received response from Gemini.")

        # Extract and parse the JSON response (logica rămâne la fel)
        if hasattr(response, 'text') and response.text:
            parsed_json = _extract_json_from_llm_response(response.text)
            # Returnează JSON parsat sau None dacă parsarea eșuează
            return parsed_json
        else:
            # Handle cases where response is blocked or has no text
            block_reason = None
            if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                 block_reason = response.prompt_feedback.block_reason
            elif hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != 'STOP':
                 block_reason = response.candidates[0].finish_reason

            if block_reason:
                 logger.warning(f"Gemini request potentially blocked or failed. Reason: {block_reason}")
            else:
                logger.warning("LLM response received, but it contains no text content or text could not be extracted.")
                logger.debug(f"Full LLM Response structure: {response}")
            return None

    except AttributeError as ae:
         # Verificăm dacă eroarea este specifică metodei generate_content
         if 'generate_content' in str(ae):
              logger.error(f"AttributeError calling generate_content: {ae}. Is 'models' attribute correct?", exc_info=True)
         else:
              logger.error(f"AttributeError during client call: {ae}", exc_info=True)
         return None
    # Prindem TypeError în caz că se mai strecoară un argument neașteptat
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
    # ... (logica acestei funcții rămâne neschimbată) ...
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
            # Verificare structură JSON așteptată
            if isinstance(parsed_json, dict) and \
               "recommendations" in parsed_json and \
               isinstance(parsed_json["recommendations"], list) and \
               "action_plan" in parsed_json and \
               isinstance(parsed_json["action_plan"], dict) and \
               all(key in parsed_json["action_plan"] for key in ["immediate", "short_term", "long_term"]):
                 return parsed_json
            else:
                 logger.warning("Parsed JSON does not match the expected structure (recommendations list, action_plan dict with keys).")
                 logger.debug(f"Parsed JSON content: {parsed_json}")
                 return None
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
    # ... (logica de inițializare test rămâne la fel) ...
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

        logger.info("Attempting to generate hygiene recommendations (using Client method)...")
        recommendations_data = generate_hygiene_recommendations(
            overall_score=test_overall,
            category_scores=test_scores,
            strengths=test_strengths,
            weaknesses=test_weaknesses
        )

        if recommendations_data:
            logger.info("Successfully received recommendations data:")
            if isinstance(recommendations_data, dict) and "recommendations" in recommendations_data:
                 print(json.dumps(recommendations_data, indent=2, ensure_ascii=False))
            else:
                 logger.warning(f"Received data, but it's not the expected dictionary structure: {recommendations_data}")
        else:
            logger.error("Failed to generate recommendations (returned None).")

    else:
        logger.warning("LLM Initialization failed or skipped. Cannot run recommendation generation test.")