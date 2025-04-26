#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - Digital Hygiene Module
This module evaluates users' digital hygiene practices and provides personalized recommendations
for improving their online security posture.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional # Am adăugat tipuri lipsă

# Import configuration settings
try:
    import config
except ImportError:
    # Fallback sau handling dacă config.py nu e garantat să existe
    class MockConfig:
        HYGIENE_CATEGORIES = ["account_security", "data_sharing", "device_security", "social_media", "browsing_habits"]
        ENABLE_LLM_REPORTS = os.environ.get("ENABLE_LLM_REPORTS", "true").lower() == "true"
    config = MockConfig()
    logging.warning("config.py not found, using defaults for digital_hygiene module.")


# Import utilities - doar ce este necesar
try:
    from utils.llm_handler import generate_hygiene_recommendations, is_llm_available
except ImportError:
    logging.error("Failed to import from utils.llm_handler. LLM features will be disabled.")
    # Funcții placeholder pentru a evita erori ulterioare
    def generate_hygiene_recommendations(*args, **kwargs) -> Optional[Dict[str, Any]]: return None
    def is_llm_available() -> bool: return False


# Set up logging
logger = logging.getLogger(__name__)

# --- Questionnaire Loading ---

def load_questionnaire(base_path: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Load the hygiene questionnaire from JSON file.
    Tries to find the file relative to this script's location.

    Args:
        base_path (Optional[str]): Optional base path if not running from standard structure.

    Returns:
        dict: The questionnaire data structure, or empty structure on error.
    """
    try:
        # Determinăm calea relativ la fișierul curent
        if base_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Presupunem că 'data' este la același nivel cu directorul părintelui ('modules')
            # ex: project_root/data/chestionar.json , project_root/modules/digital_hygiene.py
            project_root = os.path.dirname(current_dir)
            file_path = os.path.join(project_root, 'data', 'chestionar.json')
        else:
             file_path = os.path.join(base_path, 'data', 'chestionar.json')


        logger.info(f"Attempting to load questionnaire from: {file_path}")
        if not os.path.exists(file_path):
             logger.error(f"Questionnaire file not found at calculated path: {file_path}")
             # Încercăm o cale alternativă, poate 'data' e în directorul curent (mai puțin probabil)
             alt_file_path = os.path.join(os.path.dirname(__file__), '../data/chestionar.json') # Calea originală
             if os.path.exists(alt_file_path):
                  file_path = alt_file_path
                  logger.info(f"Found questionnaire at alternative path: {file_path}")
             else:
                  raise FileNotFoundError(f"Questionnaire file not found at primary path {file_path} or alternative {alt_file_path}")


        with open(file_path, 'r', encoding='utf-8') as f:
            questionnaire_data = json.load(f)
            logger.info("Questionnaire loaded successfully.")
            return questionnaire_data
    except FileNotFoundError as fnf_error:
         logger.error(f"{fnf_error}")
         # Returnăm o structură goală validă
         return {cat: [] for cat in getattr(config, 'HYGIENE_CATEGORIES', [])}
    except json.JSONDecodeError as json_error:
         logger.error(f"Error decoding JSON questionnaire file: {json_error}")
         return {cat: [] for cat in getattr(config, 'HYGIENE_CATEGORIES', [])}
    except Exception as e:
        logger.error(f"Failed to load questionnaire due to unexpected error: {str(e)}", exc_info=True)
        return {cat: [] for cat in getattr(config, 'HYGIENE_CATEGORIES', [])}

# --- Form Processing ---

def process_hygiene_form(form_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Process the form submission from the hygiene questionnaire.

    Args:
        form_data (dict): The form data submitted by the user (values usually strings).

    Returns:
        dict: Processed data with scores, categorized responses, and analysis, or None if input is invalid.
    """
    if not form_data:
        logger.warning("Empty form data received in process_hygiene_form.")
        return None

    # Load the questionnaire structure
    questionnaire = load_questionnaire()
    if not questionnaire or not any(questionnaire.values()): # Verifică dacă chestionarul e gol
         logger.error("Questionnaire could not be loaded or is empty. Cannot process form.")
         return None

    # Get category list safely from config or default
    hygiene_categories = getattr(config, 'HYGIENE_CATEGORIES', ["account_security", "data_sharing", "device_security", "social_media", "browsing_habits"])

    # Initialize the results structure
    processed_data = {
        "timestamp": datetime.now().isoformat(),
        "raw_responses": {},
        "category_scores": {cat: 0 for cat in hygiene_categories}, # Inițializăm scorurile cu 0
        "category_raw_scores": {cat: 0 for cat in hygiene_categories},
        "overall_score": 0,
        "strengths": [],
        "weaknesses": []
    }

    all_normalized_scores = []
    total_questions_processed = 0

    # Process each category
    for category in hygiene_categories:
        if category not in questionnaire or not questionnaire[category]:
            logger.warning(f"Category '{category}' not found or is empty in questionnaire structure. Skipping.")
            processed_data["raw_responses"][category] = [] # Adăugăm lista goală pentru consistență
            continue # Trecem la următoarea categorie

        category_raw_total = 0
        category_responses_list = []
        questions_in_category = questionnaire[category]
        num_questions_in_cat = len(questions_in_category)

        if num_questions_in_cat == 0:
             logger.warning(f"No questions found for category '{category}' in questionnaire.")
             continue

        # Process each question in the category
        for question in questions_in_category:
            question_id = question.get("id")
            if not question_id:
                 logger.warning(f"Question in category '{category}' is missing 'id'. Skipping.")
                 continue

            # Get the user's response from form_data
            response_str = form_data.get(question_id)

            if response_str is not None:
                try:
                    # Convert the response to an integer value
                    response_value = int(response_str)

                    # Find the text of the selected option for clarity
                    response_text = "N/A"
                    for option in question.get("options", []):
                        if option.get("value") == response_value:
                            response_text = option.get("text", "N/A")
                            break

                    # Store the processed response
                    category_responses_list.append({
                        "question_id": question_id,
                        "question": question.get("question", "Întrebare lipsă"),
                        "value": response_value,
                        "response": response_text
                    })

                    # Update raw category score
                    category_raw_total += response_value
                    total_questions_processed += 1 # Contorizăm doar întrebările procesate

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing response for question '{question_id}' (value: '{response_str}'): {e}")
                    # Putem decide să omitem întrebarea sau să asignăm un scor default (ex: 1)
                    # Aici o omitem din calculul scorului
            else:
                logger.debug(f"No response found in form_data for question '{question_id}'.")
                # Putem decide să omitem întrebarea sau să asignăm un scor default (ex: 1)
                # Aici o omitem din calculul scorului

        # Store the raw category score (ex: range 3-12 if 3 questions)
        processed_data["category_raw_scores"][category] = category_raw_total
        processed_data["raw_responses"][category] = category_responses_list # Stocăm răspunsurile procesate

        # Calculate the normalized category score (0-100) only if questions were processed
        num_answered_in_cat = len(category_responses_list)
        if num_answered_in_cat > 0:
             # Min score possible for answered questions = num_answered * 1
             min_possible = num_answered_in_cat
             # Max score possible for answered questions = num_answered * 4
             max_possible = num_answered_in_cat * 4
             score_range = max_possible - min_possible

             if score_range > 0: # Evităm împărțirea la zero dacă e o singură opțiune teoretic
                normalized_score = ((category_raw_total - min_possible) / score_range) * 100
                normalized_score = max(0, min(100, round(normalized_score))) # Asigurăm 0-100
                processed_data["category_scores"][category] = normalized_score
                all_normalized_scores.append(normalized_score)
             else: # Cazul improbabil range 0
                 processed_data["category_scores"][category] = 100 if category_raw_total >= min_possible else 0

        # Dacă nicio întrebare din categorie nu a primit răspuns valid, scorul rămâne 0 (din inițializare)

    # Calculate the overall score as the average of all *calculated* normalized category scores
    if all_normalized_scores:
        processed_data["overall_score"] = round(sum(all_normalized_scores) / len(all_normalized_scores))
    else:
        logger.warning("No valid category scores calculated, overall score remains 0.")
        processed_data["overall_score"] = 0 # Rămâne 0 dacă nu avem scoruri

    # Identify strengths and weaknesses based on calculated scores and raw responses
    processed_data.update(identify_strengths_weaknesses(processed_data)) # Nu mai trimitem chestionarul

    logger.info(f"Processed hygiene form. Overall score: {processed_data['overall_score']}")
    return processed_data

# --- Strengths/Weaknesses Identification ---

def identify_strengths_weaknesses(processed_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Identify strengths and weaknesses based on the user's responses and calculated scores.

    Args:
        processed_data (dict): The processed form data containing scores and raw_responses.

    Returns:
        dict: Contains lists of identified 'strengths' and 'weaknesses'.
    """
    results = {
        "strengths": [],
        "weaknesses": []
    }

    # Define critical questions IDs (poate ar fi mai bine în config.py)
    critical_question_ids = {
        "pass_reuse", "mfa_usage", "device_updates", "public_wifi", "download_habits"
        # Am scos pass_manager, antivirus_usage, device_encryption pentru chestionarul redus
    }

    # Check each category's normalized score based on thresholds
    for category, score in processed_data.get("category_scores", {}).items():
        category_display = category.replace('_', ' ').title()
        if score >= 85: # Prag puțin mai mare pentru puncte forte
            results["strengths"].append(f"Bune practici generale în {category_display}")
        elif score <= 40: # Prag puțin mai mic pentru slăbiciuni majore
            results["weaknesses"].append(f"Practicile din {category_display} necesită atenție imediată")
        elif score <= 60: # Prag intermediar
            results["weaknesses"].append(f"Practicile din {category_display} pot fi îmbunătățite")

    # Analyze individual question responses stored in raw_responses
    for category, responses in processed_data.get("raw_responses", {}).items():
        for response in responses:
            question_id = response.get("question_id")
            response_value = response.get("value")
            question_text = response.get("question", f"Întrebare ID: {question_id}")
            response_text_short = response.get("response", "").split('(')[0].strip() # Text mai scurt

            if question_id is None or response_value is None:
                continue # Skip invalid response entries

            is_critical = question_id in critical_question_ids

            # Formatare mesaje
            weakness_prefix = f"Slăbiciune ({category.replace('_',' ')}): "
            strength_prefix = f"Punct forte ({category.replace('_',' ')}): "

            # Add severe weaknesses for critical security issues (score 1)
            if is_critical and response_value == 1:
                results["weaknesses"].append(f"{weakness_prefix}Răspuns critic la '{question_text}' - {response_text_short}")
            # Add important weaknesses for critical security issues (score 2)
            elif is_critical and response_value == 2:
                 results["weaknesses"].append(f"{weakness_prefix}Răspuns îngrijorător la '{question_text}' - {response_text_short}")
            # Add regular weaknesses (non-critical with low score)
            elif not is_critical and response_value <= 2: # Capturăm și 1 și 2 pentru non-critice
                results["weaknesses"].append(f"{weakness_prefix}Răspuns slab la '{question_text}' - {response_text_short}")

            # Add strengths for excellent security practices (score 4)
            if response_value == 4:
                results["strengths"].append(f"{strength_prefix}Răspuns excelent la '{question_text}'")
            # Putem adăuga și pentru scor 3 ca "bune practici"
            elif response_value == 3:
                 results["strengths"].append(f"{strength_prefix}Practică bună la '{question_text}'")


    # Eliminăm duplicatele păstrând ordinea (aproximativ)
    results["strengths"] = list(dict.fromkeys(results["strengths"]))
    results["weaknesses"] = list(dict.fromkeys(results["weaknesses"]))

    # Sortăm slăbiciunile pentru a le aduce pe cele critice/îngrijorătoare primele
    results["weaknesses"].sort(key=lambda x: 0 if "critic" in x else (1 if "îngrijorător" in x else 2))

    # Limităm numărul afișat (opțional)
    results["strengths"] = results["strengths"][:7]
    results["weaknesses"] = results["weaknesses"][:7]

    return results

# --- Report Generation ---

def generate_hygiene_report(processed_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Generate a comprehensive hygiene report with recommendations.

    Args:
        processed_data (dict): The processed form data with scores and analysis, or None.

    Returns:
        dict: Complete hygiene report with recommendations, or None if input is invalid.
    """
    if not processed_data:
        logger.warning("No processed data provided to generate_hygiene_report.")
        return None

    # Start building the report structure
    report = {
        "generated_at": datetime.now().isoformat(),
        "overall_score": processed_data.get("overall_score", 0),
        "category_scores": processed_data.get("category_scores", {}),
        "strengths": processed_data.get("strengths", []),
        "weaknesses": processed_data.get("weaknesses", []),
        "recommendations": [],
        "action_plan": {
            "immediate": [],
            "short_term": [],
            "long_term": []
        },
        "risk_level": "necunoscut", # Default
        "risk_level_description": "Nivelul de risc nu a putut fi determinat.",
        "summary": "Rezumatul nu a putut fi generat.", # Default summary
        "report_version": "1.1", # Incrementăm versiunea
        "verification_method": "Identity Guardian Digital Hygiene Assessment"
    }

    # Determine risk level based on overall score
    score = report["overall_score"]
    if score >= 80:
        report["risk_level"] = "scăzut"
        report["risk_level_description"] = "Practicile tale de igienă digitală sunt în general bune, dar există întotdeauna loc de îmbunătățire."
    elif score >= 51: # Ajustat pragul pentru mediu
        report["risk_level"] = "mediu"
        report["risk_level_description"] = "Practicile tale de igienă digitală necesită îmbunătățiri în anumite domenii pentru a reduce riscurile de securitate."
    else: # score <= 50
        report["risk_level"] = "ridicat"
        report["risk_level_description"] = "Practicile tale de igienă digitală prezintă vulnerabilități semnificative care necesită atenție imediată."

    # Add basic recommendations based on scores and weaknesses (important fallback)
    add_basic_recommendations(report, processed_data)

    # Attempt to get AI-powered recommendations if service is available
    if is_llm_available():
        logger.info("LLM service is available, attempting to generate AI recommendations.")
        try:
            # Asigurăm că trimitem doar datele necesare și valide
            ai_recommendations = generate_hygiene_recommendations(
                report["overall_score"],
                report.get("category_scores", {}), # Trimitem chiar dacă e gol
                report.get("strengths", []),
                report.get("weaknesses", [])
            )

            if ai_recommendations and isinstance(ai_recommendations, dict):
                logger.info("Received recommendations structure from LLM.")
                # Integrăm recomandările AI - adăugăm doar dacă nu există deja similare (opțional)
                ai_recs_list = ai_recommendations.get("recommendations", [])
                existing_rec_texts = {r.get("recommendation", "").lower() for r in report["recommendations"]}
                for ai_rec in ai_recs_list:
                     if isinstance(ai_rec, dict) and ai_rec.get("recommendation", "").lower() not in existing_rec_texts:
                         report["recommendations"].append(ai_rec)
                         existing_rec_texts.add(ai_rec.get("recommendation", "").lower()) # Adăugăm textul la set

                # Integrăm planul de acțiune AI - adăugăm doar dacă nu există deja
                ai_action_plan = ai_recommendations.get("action_plan", {})
                if isinstance(ai_action_plan, dict):
                    for timeframe in ["immediate", "short_term", "long_term"]:
                        existing_actions = set(report["action_plan"].get(timeframe, []))
                        ai_actions = ai_action_plan.get(timeframe, [])
                        if isinstance(ai_actions, list): # Verificăm că e listă
                             for action in ai_actions:
                                 if isinstance(action, str) and action not in existing_actions: # Verificăm că e string
                                     report["action_plan"][timeframe].append(action)
                                     existing_actions.add(action)
            elif ai_recommendations is None:
                 logger.warning("generate_hygiene_recommendations returned None (likely an error occurred).")
            else:
                 logger.warning(f"Received unexpected data type from generate_hygiene_recommendations: {type(ai_recommendations)}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while calling or processing AI recommendations: {str(e)}", exc_info=True)
    else:
        logger.info("LLM service not available, skipping AI recommendations.")

    # Add fallback recommendations if the list is still empty after basic and AI attempts
    if not report["recommendations"]:
        logger.info("No recommendations generated yet, adding fallback recommendations.")
        add_fallback_recommendations(report) # Folosim funcția de fallback

    # Curățăm și asigurăm consistența planului de acțiune
    finalize_action_plan(report)

    # --- Eliminăm generarea rezumatului LLM ---
    # Generăm un rezumat simplu, bazat pe datele existente
    report["summary"] = generate_basic_report_summary(report)

    logger.info(f"Generated hygiene report successfully. Risk level: {report['risk_level']}")
    return report

# --- Recommendation Helpers ---

def add_basic_recommendations(report: Dict[str, Any], processed_data: Dict[str, Any]):
    """
    Adds rule-based recommendations based on category scores and specific answers.
    This serves as a baseline and fallback.

    Args:
        report (dict): The report dictionary to add recommendations to.
        processed_data (dict): The processed form data containing scores and raw_responses.
    """
    logger.debug("Adding basic recommendations based on rules.")
    recommendations_added = set() # Folosim un set pentru a evita duplicatele de text

    def add_rec(category, text, priority):
        """Helper to add unique recommendations."""
        if text.lower() not in recommendations_added:
            report["recommendations"].append({
                "category": category,
                "recommendation": text,
                "priority": priority
            })
            recommendations_added.add(text.lower())

    # Prioritize based on critical weaknesses identified previously
    for weakness in report.get("weaknesses", []):
         if "critic" in weakness.lower():
             if "parol" in weakness.lower():
                 add_rec("account_security", "Folosește un manager de parole pentru a genera și stoca parole unice și complexe.", "high")
             if "mfa" in weakness.lower() or "2fa" in weakness.lower() or "doi factori" in weakness.lower():
                 add_rec("account_security", "Activează urgent autentificarea cu doi factori (2FA/MFA) pe conturile critice (email, bancă, social media).", "high")
             if "actualizări" in weakness.lower() or "update" in weakness.lower():
                 add_rec("device_security", "Instalează imediat toate actualizările de securitate disponibile pentru sistemul de operare și aplicații.", "high")
             if "wi-fi public" in weakness.lower():
                  add_rec("browsing_habits", "Evită complet folosirea Wi-Fi-ului public pentru activități sensibile sau folosește un VPN de încredere.", "high")
             if "descărca" in weakness.lower() or "download" in weakness.lower():
                  add_rec("browsing_habits", "Descarcă aplicații și fișiere doar din surse oficiale și de încredere.", "high")


    # Add recommendations based on category scores
    category_scores = report.get("category_scores", {})

    if category_scores.get("account_security", 100) < 60:
        add_rec("account_security", "Revizuiește securitatea tuturor conturilor tale online.", "high")
        add_rec("account_security", "Consideră folosirea unui manager de parole.", "high")
        add_rec("account_security", "Activează 2FA/MFA unde este posibil.", "high")

    if category_scores.get("data_sharing", 100) < 70:
        add_rec("data_sharing", "Limitează cantitatea de informații personale pe care o distribui online.", "medium")
        add_rec("data_sharing", "Verifică regulat permisiunile acordate aplicațiilor (locație, contacte, etc.).", "medium")

    if category_scores.get("device_security", 100) < 60:
        add_rec("device_security", "Asigură-te că toate dispozitivele tale au actualizările de securitate la zi.", "high")
        add_rec("device_security", "Folosește un antivirus/antimalware actualizat pe toate dispozitivele.", "medium")
        add_rec("device_security", "Activează blocarea ecranului (PIN, parolă, biometric) pe toate dispozitivele.", "medium")

    if category_scores.get("social_media", 100) < 70:
        add_rec("social_media", "Revizuiește și restrânge setările de confidențialitate pe profilurile tale sociale.", "medium")
        add_rec("social_media", "Fii precaut(ă) cu cine accepți ca prieten/urmăritor și ce informații postezi.", "medium")
        add_rec("social_media", "Dezactivează sau șterge conturile sociale vechi pe care nu le mai folosești.", "low")

    if category_scores.get("browsing_habits", 100) < 70:
        add_rec("browsing_habits", "Fii vigilent(ă) la tentativele de phishing (emailuri, mesaje suspecte).", "high")
        add_rec("browsing_habits", "Evită să dai clic pe linkuri sau să descarci atașamente din surse nesigure.", "high")
        add_rec("browsing_habits", "Folosește conexiuni securizate (HTTPS) și consideră un VPN, mai ales pe rețele publice.", "medium")


def add_fallback_recommendations(report: Dict[str, Any]):
    """
    Adds a minimal set of generic fallback recommendations if no other
    recommendations (basic or AI) were added.

    Args:
        report (dict): The report dictionary to add recommendations to.
    """
    logger.info("Executing fallback recommendations function.")
    if report.get("recommendations"): # Verifică dacă există deja recomandări
        logger.debug("Recommendations already exist, skipping fallback.")
        return

    fallback_recs = [
        {"category": "account_security", "recommendation": "Folosește parole unice și puternice.", "priority": "high"},
        {"category": "account_security", "recommendation": "Activează autentificarea cu 2 factori (2FA).", "priority": "high"},
        {"category": "device_security", "recommendation": "Actualizează regulat sistemul și aplicațiile.", "priority": "high"},
        {"category": "data_sharing", "recommendation": "Limitează distribuirea datelor personale online.", "priority": "medium"},
        {"category": "browsing_habits", "recommendation": "Fii atent la phishing și site-uri suspecte.", "priority": "high"},
    ]
    report["recommendations"] = fallback_recs
    logger.info("Added generic fallback recommendations.")


def finalize_action_plan(report: Dict[str, Any]):
    """
    Cleans up the action plan: removes duplicates, ensures basic actions exist if needed.

    Args:
        report (dict): The report dictionary containing the action plan.
    """
    action_plan = report.get("action_plan", {})
    recommendations = report.get("recommendations", [])

    for timeframe in ["immediate", "short_term", "long_term"]:
        # Eliminăm duplicatele păstrând ordinea aproximativă
        if timeframe in action_plan and isinstance(action_plan[timeframe], list):
             unique_actions = list(dict.fromkeys(action_plan[timeframe]))
             action_plan[timeframe] = unique_actions
        else:
             action_plan[timeframe] = [] # Asigurăm că e listă

    # Adăugăm acțiuni de bază dacă secțiunile sunt goale, mapate din recomandări
    if not action_plan["immediate"]:
        action_plan["immediate"].extend([r["recommendation"] for r in recommendations if r.get("priority") == "high"][:2]) # Primele 2 high
    if not action_plan["short_term"]:
         action_plan["short_term"].extend([r["recommendation"] for r in recommendations if r.get("priority") == "medium"][:2]) # Primele 2 medium
    if not action_plan["long_term"]:
         action_plan["long_term"].extend([r["recommendation"] for r in recommendations if r.get("priority") == "low"][:2]) # Primele 2 low
         # Adăugăm o acțiune generică dacă tot e goală
         if not action_plan["long_term"]:
              action_plan["long_term"].append("Revizuiește periodic setările de securitate și confidențialitate.")

    # Reasignăm planul curățat (poate nu e necesar dacă modificăm in-place, dar e mai sigur)
    report["action_plan"] = action_plan


# --- Basic Summary Generator (No LLM) ---

def generate_basic_report_summary(report_data: Dict[str, Any]) -> str:
    """
    Generate a basic, human-readable summary of the hygiene report without using LLM.

    Args:
        report_data: The complete hygiene report data.

    Returns:
        str: A formatted summary of the report.
    """
    score = report_data.get('overall_score', 0)
    risk_level = report_data.get('risk_level', 'necunoscut')
    risk_desc = report_data.get('risk_level_description', 'Evaluați practicile dvs.')

    summary = f"**Rezumat Igienă Digitală**\n\n"
    summary += f"Scorul tău general este **{score}/100**, indicând un nivel de risc **{risk_level.upper()}**. {risk_desc}\n\n"

    weaknesses = report_data.get('weaknesses', [])
    if weaknesses:
        summary += "**Principalele zone de îmbunătățit:**\n"
        for weakness in weaknesses[:3]: # Primele 3 slăbiciuni
            # Curățăm prefixul pentru afișare
            clean_weakness = weakness.split(':', 1)[-1].strip() if ':' in weakness else weakness
            summary += f"- {clean_weakness}\n"
        summary += "\n"

    immediate_actions = report_data.get('action_plan', {}).get('immediate', [])
    if immediate_actions:
        summary += "**Acțiuni Recomandate Urgent:**\n"
        for action in immediate_actions[:2]: # Primele 2 acțiuni imediate
             summary += f"- {action}\n"

    return summary.strip()


# --- Entry point for testing (optional) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Testing digital_hygiene module functions...")

    # 1. Test Questionnaire Loading
    logger.info("\n--- Testing Questionnaire Loading ---")
    questionnaire_test = load_questionnaire()
    if questionnaire_test and any(questionnaire_test.values()):
        logger.info(f"Questionnaire loaded successfully. Categories: {list(questionnaire_test.keys())}")
        # print(json.dumps(questionnaire_test, indent=2, ensure_ascii=False)) # Decomentează pentru a vedea structura
    else:
        logger.error("Failed to load questionnaire for test.")
        exit() # Oprim testul dacă nu avem chestionar

    # 2. Test Form Processing
    logger.info("\n--- Testing Form Processing ---")
    # Creăm un form_data de test (răspunsuri medii/mixte)
    test_form = {}
    q_count = 0
    for category, questions in questionnaire_test.items():
        for question in questions:
            # Simulăm un răspuns între 2 și 3
            test_form[question['id']] = str( (q_count % 2) + 2 )
            q_count += 1
    # Suprascriem câteva răspunsuri pentru a testa slăbiciuni/puncte forte
    if "pass_reuse" in test_form: test_form["pass_reuse"] = "1" # Slăbiciune critică
    if "mfa_usage" in test_form: test_form["mfa_usage"] = "4" # Punct forte
    if "device_updates" in test_form: test_form["device_updates"] = "1" # Slăbiciune critică

    processed_result = process_hygiene_form(test_form)
    if processed_result:
        logger.info("Form processed successfully.")
        logger.info(f"Overall Score: {processed_result['overall_score']}")
        logger.info(f"Category Scores: {processed_result['category_scores']}")
        logger.info(f"Strengths: {processed_result['strengths']}")
        logger.info(f"Weaknesses: {processed_result['weaknesses']}")
        # print("\nRaw Responses Sample:")
        # print(json.dumps(processed_result['raw_responses'].get('account_security', {}), indent=2, ensure_ascii=False))
    else:
        logger.error("Failed to process form data.")
        exit() # Oprim dacă procesarea eșuează

    # 3. Test Report Generation (include apel LLM dacă e inițializat)
    logger.info("\n--- Testing Report Generation ---")
    # Încercăm să inițializăm LLM Handler (necesită cheie API)
    try:
         from utils.llm_handler import initialize_llm
         llm_init_success = initialize_llm()
         logger.info(f"LLM Initialization attempt result: {llm_init_success}")
    except ImportError:
         logger.warning("Could not import initialize_llm from llm_handler.")
         llm_init_success = False


    final_report = generate_hygiene_report(processed_result)
    if final_report:
        logger.info("Report generated successfully.")
        print("\n--- FINAL REPORT (Sample) ---")
        print(f"Generated At: {final_report['generated_at']}")
        print(f"Overall Score: {final_report['overall_score']}")
        print(f"Risk Level: {final_report['risk_level']} - {final_report['risk_level_description']}")
        print("\nStrengths:")
        for s in final_report['strengths']: print(f"- {s}")
        print("\nWeaknesses:")
        for w in final_report['weaknesses']: print(f"- {w}")
        print("\nRecommendations:")
        for r in final_report['recommendations']: print(f"- [{r.get('priority','N/A').upper()}] ({r.get('category','N/A')}) {r.get('recommendation','N/A')}")
        print("\nAction Plan:")
        print(f"  Immediate: {final_report['action_plan']['immediate']}")
        print(f"  Short Term: {final_report['action_plan']['short_term']}")
        print(f"  Long Term: {final_report['action_plan']['long_term']}")
        print(f"\nSummary:\n{final_report['summary']}")
        print("--- END OF REPORT ---")
    else:
        logger.error("Failed to generate final report.")