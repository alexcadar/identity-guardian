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
from typing import Dict, Any, List, Optional

# Import configuration settings
try:
    import config
except ImportError:
    class MockConfig:
        HYGIENE_CATEGORIES = ["account_security", "data_sharing", "device_security", "social_media", "browsing_habits"]
        ENABLE_LLM_REPORTS = os.environ.get("ENABLE_LLM_REPORTS", "true").lower() == "true"
        CRITICAL_QUESTION_IDS = {"pass_reuse", "mfa_usage", "device_updates", "public_wifi", "download_habits"}
    config = MockConfig()
    logging.warning("config.py not found, using defaults for digital_hygiene module.")

# Import utilities
try:
    from utils.llm_handler import generate_hygiene_recommendations, is_llm_available, initialize_llm
except ImportError:
    logging.error("Failed to import from utils.llm_handler. LLM features will be disabled.")
    def generate_hygiene_recommendations(*args, **kwargs) -> Optional[Dict[str, Any]]: return None
    def is_llm_available() -> bool: return False
    def initialize_llm() -> bool: return False

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
        if base_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            file_path = os.path.join(project_root, 'data', 'chestionar.json')
        else:
            file_path = os.path.join(base_path, 'data', 'chestionar.json')

        logger.info(f"Attempting to load questionnaire from: {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"Questionnaire file not found at: {file_path}")
            alt_file_path = os.path.join(os.path.dirname(__file__), '../data/chestionar.json')
            if os.path.exists(alt_file_path):
                file_path = alt_file_path
                logger.info(f"Found questionnaire at alternative path: {file_path}")
            else:
                raise FileNotFoundError(f"Questionnaire file not found at primary path {file_path} or alternative {alt_file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            questionnaire_data = json.load(f)
            logger.info("Questionnaire loaded successfully.")

        # Validate questionnaire categories
        expected_categories = set(getattr(config, 'HYGIENE_CATEGORIES', []))
        actual_categories = set(questionnaire_data.keys())
        if not expected_categories.issubset(actual_categories):
            missing = expected_categories - actual_categories
            logger.warning(f"Questionnaire missing expected categories: {missing}")
        if not actual_categories.issubset(expected_categories):
            extra = actual_categories - expected_categories
            logger.warning(f"Questionnaire contains unexpected categories: {extra}")

        return questionnaire_data
    except FileNotFoundError as fnf_error:
        logger.error(f"{fnf_error}")
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
    if not questionnaire or not any(questionnaire.values()):
        logger.error("Questionnaire could not be loaded or is empty. Cannot process form.")
        return None

    hygiene_categories = getattr(config, 'HYGIENE_CATEGORIES', ["account_security", "data_sharing", "device_security", "social_media", "browsing_habits"])

    # Initialize the results structure
    processed_data = {
        "timestamp": datetime.now().isoformat(),
        "raw_responses": {},
        "category_scores": {cat: 0 for cat in hygiene_categories},
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
            processed_data["raw_responses"][category] = []
            continue

        category_responses_list = []
        questions_in_category = questionnaire[category]
        num_questions_in_cat = len(questions_in_category)

        if num_questions_in_cat == 0:
            logger.warning(f"No questions found for category '{category}' in questionnaire.")
            continue

        # Process responses using list comprehension
        category_raw_total = 0
        for question in questions_in_category:
            question_id = question.get("id")
            if not question_id:
                logger.warning(f"Question in category '{category}' is missing 'id'. Skipping.")
                continue

            response_str = form_data.get(question_id)
            if response_str is None:
                logger.debug(f"No response found in form_data for question '{question_id}'.")
                continue

            try:
                response_value = int(response_str)
                response_text = next((opt.get("text", "N/A") for opt in question.get("options", []) if opt.get("value") == response_value), "N/A")
                category_responses_list.append({
                    "question_id": question_id,
                    "question": question.get("question", "Întrebare lipsă"),
                    "value": response_value,
                    "response": response_text
                })
                category_raw_total += response_value
                total_questions_processed += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing response for question '{question_id}' (value: '{response_str}'): {e}")
                continue

        processed_data["category_raw_scores"][category] = category_raw_total
        processed_data["raw_responses"][category] = category_responses_list

        # Calculate normalized category score
        num_answered_in_cat = len(category_responses_list)
        if num_answered_in_cat > 0:
            min_possible = num_answered_in_cat
            max_possible = num_answered_in_cat * 4
            score_range = max_possible - min_possible
            if score_range > 0:
                normalized_score = ((category_raw_total - min_possible) / score_range) * 100
                normalized_score = max(0, min(100, round(normalized_score)))
                processed_data["category_scores"][category] = normalized_score
                all_normalized_scores.append(normalized_score)
            else:
                processed_data["category_scores"][category] = 100 if category_raw_total >= min_possible else 0

    # Calculate overall score
    if all_normalized_scores:
        processed_data["overall_score"] = round(sum(all_normalized_scores) / len(all_normalized_scores))
    else:
        logger.warning("No valid category scores calculated, overall score remains 0.")

    # Identify strengths and weaknesses
    processed_data.update(identify_strengths_weaknesses(processed_data))

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

    critical_question_ids = getattr(config, 'CRITICAL_QUESTION_IDS', {"pass_reuse", "mfa_usage", "device_updates", "public_wifi", "download_habits"})

    # Check category scores
    for category, score in processed_data.get("category_scores", {}).items():
        category_display = category.replace('_', ' ').title()
        if score >= 85:
            results["strengths"].append(f"Bune practici generale în {category_display}")
        elif score <= 40:
            results["weaknesses"].append(f"Practicile din {category_display} necesită atenție imediată")
        elif score <= 60:
            results["weaknesses"].append(f"Practicile din {category_display} pot fi îmbunătățite")

    # Analyze individual responses
    for category, responses in processed_data.get("raw_responses", {}).items():
        for response in responses:
            question_id = response.get("question_id")
            response_value = response.get("value")
            question_text = response.get("question", f"Întrebare ID: {question_id}")
            response_text_short = response.get("response", "").split('(')[0].strip()

            if question_id is None or response_value is None:
                continue

            is_critical = question_id in critical_question_ids
            weakness_prefix = f"Slăbiciune ({category.replace('_',' ')}): "
            strength_prefix = f"Punct forte ({category.replace('_',' ')}): "

            if is_critical and response_value == 1:
                results["weaknesses"].append(f"{weakness_prefix}Răspuns critic la '{question_text}' - {response_text_short}")
            elif is_critical and response_value == 2:
                results["weaknesses"].append(f"{weakness_prefix}Răspuns îngrijorător la '{question_text}' - {response_text_short}")
            elif not is_critical and response_value <= 2:
                results["weaknesses"].append(f"{weakness_prefix}Răspuns slab la '{question_text}' - {response_text_short}")
            if response_value == 4:
                results["strengths"].append(f"{strength_prefix}Răspuns excelent la '{question_text}'")
            elif response_value == 3:
                results["strengths"].append(f"{strength_prefix}Practică bună la '{question_text}'")

    results["strengths"] = list(dict.fromkeys(results["strengths"]))
    results["weaknesses"] = list(dict.fromkeys(results["weaknesses"]))
    results["weaknesses"].sort(key=lambda x: 0 if "critic" in x else (1 if "îngrijorător" in x else 2))
    results["strengths"] = results["strengths"][:7]
    results["weaknesses"] = results["weaknesses"][:7]

    return results

# --- Report Generation ---

def generate_hygiene_report(processed_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Generate a comprehensive hygiene report with recommendations structured for hygiene_report_detail.html.

    Args:
        processed_data (dict): The processed form data with scores and analysis, or None.

    Returns:
        dict: Complete hygiene report with recommendations structured for hygiene_report_detail.html, or None if input is invalid.
    """
    if not processed_data:
        logger.warning("No processed data provided to generate_hygiene_report.")
        return None

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
        "risk_level": "necunoscut",
        "risk_level_description": "Nivelul de risc nu a putut fi determinat.",
        "summary": "Rezumatul nu a putut fi generat.",
        "report_version": "1.2",  # Incremented version
        "verification_method": "Identity Guardian Digital Hygiene Assessment"
    }

    # Determine risk level
    score = report["overall_score"]
    if score >= 80:
        report["risk_level"] = "scăzut"
        report["risk_level_description"] = "Practicile tale de igienă digitală sunt în general bune, dar există întotdeauna loc de îmbunătățire."
    elif score >= 51:
        report["risk_level"] = "mediu"
        report["risk_level_description"] = "Practicile tale de igienă digitală necesită îmbunătățiri în anumite domenii pentru a reduce riscurile de securitate."
    else:
        report["risk_level"] = "ridicat"
        report["risk_level_description"] = "Practicile tale de igienă digitală prezintă vulnerabilități semnificative care necesită atenție imediată."

    # Add basic recommendations
    add_basic_recommendations(report, processed_data)

    # Attempt AI-powered recommendations
    if is_llm_available():
        logger.info("LLM service is available, attempting to generate AI recommendations.")
        try:
            ai_recommendations = generate_hygiene_recommendations(
                report["overall_score"],
                report.get("category_scores", {}),
                report.get("strengths", []),
                report.get("weaknesses", [])
            )
            if ai_recommendations and isinstance(ai_recommendations, dict):
                logger.info("Received recommendations structure from LLM.")
                existing_rec_texts = {r.get("recommendation", "").lower() for r in report["recommendations"]}
                for ai_rec in ai_recommendations.get("recommendations", []):
                    if isinstance(ai_rec, dict) and ai_rec.get("recommendation", "").lower() not in existing_rec_texts:
                        report["recommendations"].append(ai_rec)
                        existing_rec_texts.add(ai_rec.get("recommendation", "").lower())
                ai_action_plan = ai_recommendations.get("action_plan", {})
                if isinstance(ai_action_plan, dict):
                    for timeframe in ["immediate", "short_term", "long_term"]:
                        existing_actions = set(report["action_plan"].get(timeframe, []))
                        ai_actions = ai_action_plan.get(timeframe, [])
                        if isinstance(ai_actions, list):
                            for action in ai_actions:
                                if isinstance(action, str) and action not in existing_actions:
                                    report["action_plan"][timeframe].append(action)
                                    existing_actions.add(action)
            else:
                logger.warning(f"Invalid or no AI recommendations received: {ai_recommendations}")
        except Exception as e:
            logger.error(f"Error processing AI recommendations: {str(e)}", exc_info=True)
    else:
        logger.info("LLM service not available, relying on basic recommendations.")

    # Add fallback recommendations if needed
    if not report["recommendations"]:
        logger.info("No recommendations generated, adding fallback recommendations.")
        add_fallback_recommendations(report)

    # Finalize action plan
    finalize_action_plan(report)

    # Generate summary
    report["summary"] = generate_basic_report_summary(report)

    # Structure summary_data for template compatibility
    report["summary_data"] = {
        "score": report["overall_score"],
        "risk": report["risk_level"],
        "category_scores": report["category_scores"],
        "strengths": report["strengths"],
        "weaknesses": report["weaknesses"],
        "recommendations": report["recommendations"],
        "action_plan": report["action_plan"]
    }

    logger.info(f"Generated hygiene report successfully. Risk level: {report['risk_level']}, Overall score: {report['overall_score']}")
    return report

# --- Recommendation Helpers ---

def add_basic_recommendations(report: Dict[str, Any], processed_data: Dict[str, Any]):
    """
    Adds rule-based recommendations based on category scores and specific answers.

    Args:
        report (dict): The report dictionary to add recommendations to.
        processed_data (dict): The processed form data containing scores and raw_responses.
    """
    logger.debug("Adding basic recommendations based on rules.")
    recommendations_added = set()

    def add_rec(category, text, priority):
        if text.lower() not in recommendations_added:
            report["recommendations"].append({
                "category": category,
                "recommendation": text,
                "priority": priority
            })
            recommendations_added.add(text.lower())

    # Process critical weaknesses
    for weakness in report.get("weaknesses", []):
        if "critic" in weakness.lower():
            if "parol" in weakness.lower():
                add_rec("account_security", "Vă recomandăm să folosiți un manager de parole pentru a genera și stoca parole unice și complexe.", "high")
            if "mfa" in weakness.lower() or "2fa" in weakness.lower():
                add_rec("account_security", "Vă sugerăm să activați autentificarea cu doi factori (2FA) pe conturile critice (email, bancă, social media).", "high")
            if "actualizări" in weakness.lower():
                add_rec("device_security", "Vă recomandăm să instalați imediat toate actualizările de securitate pentru sistemul de operare și aplicații.", "high")
            if "wi-fi public" in weakness.lower():
                add_rec("browsing_habits", "Luați în considerare utilizarea unui VPN de încredere, cum ar fi NordVPN, pe rețele Wi-Fi publice.", "high")
            if "descărca" in weakness.lower():
                add_rec("browsing_habits", "Descărcați aplicații doar din magazine oficiale (Google Play, App Store) pentru a reduce riscurile.", "high")

    # Process specific question responses
    for category, responses in processed_data.get("raw_responses", {}).items():
        for response in responses:
            question_id = response.get("question_id")
            response_value = response.get("value")
            if question_id and response_value and response_value <= 2:
                if question_id == "public_wifi" and response_value <= 2:
                    add_rec("browsing_habits", "Evitați utilizarea Wi-Fi-ului public pentru activități sensibile fără un VPN securizat.", "high")
                elif question_id == "social_privacy" and response_value <= 2:
                    add_rec("social_media", "Vă sugerăm să setați profilurile de social media pe modul privat și să limitați informațiile vizibile public.", "medium")
                elif question_id == "app_permissions" and response_value <= 2:
                    add_rec("data_sharing", "Verificați și revocați permisiunile inutile acordate aplicațiilor mobile.", "medium")

    # Category-based recommendations
    category_scores = report.get("category_scores", {})
    if category_scores.get("account_security", 100) < 60:
        add_rec("account_security", "Revizuiți securitatea conturilor și folosiți parole unice.", "high")
        add_rec("account_security", "Considerați utilizarea unui manager de parole precum Bitwarden.", "high")
    if category_scores.get("data_sharing", 100) < 70:
        add_rec("data_sharing", "Limitați informațiile personale partajate online.", "medium")
    if category_scores.get("device_security", 100) < 60:
        add_rec("device_security", "Activați blocarea ecranului cu PIN sau amprentă pe toate dispozitivele.", "medium")
    if category_scores.get("social_media", 100) < 70:
        add_rec("social_media", "Dezactivați conturile sociale neutilizate pentru a reduce expunerea.", "low")
    if category_scores.get("browsing_habits", 100) < 70:
        add_rec("browsing_habits", "Folosiți un browser securizat, cum ar fi Firefox, cu setări stricte anti-tracking.", "medium")

def add_fallback_recommendations(report: Dict[str, Any]):
    """
    Adds generic fallback recommendations if no others were added.

    Args:
        report (dict): The report dictionary to add recommendations to.
    """
    logger.info("Executing fallback recommendations function.")
    if report.get("recommendations"):
        logger.debug("Recommendations already exist, skipping fallback.")
        return

    fallback_recs = [
        {"category": "account_security", "recommendation": "Vă recomandăm să folosiți parole unice și complexe.", "priority": "high"},
        {"category": "account_security", "recommendation": "Activați autentificarea cu doi factori (2FA) pe conturile importante.", "priority": "high"},
        {"category": "device_security", "recommendation": "Mențineți sistemul și aplicațiile actualizate.", "priority": "high"},
        {"category": "data_sharing", "recommendation": "Fiți atent la informațiile personale partajate online.", "priority": "medium"},
        {"category": "browsing_habits", "recommendation": "Evitați linkurile și atașamentele din surse nesigure.", "priority": "high"},
    ]
    report["recommendations"] = fallback_recs
    logger.info("Added generic fallback recommendations.")

def finalize_action_plan(report: Dict[str, Any]):
    """
    Cleans up the action plan: removes duplicates, ensures critical actions are included.

    Args:
        report (dict): The report dictionary containing the action plan.
    """
    action_plan = report.get("action_plan", {})
    recommendations = report.get("recommendations", [])

    for timeframe in ["immediate", "short_term", "long_term"]:
        if timeframe in action_plan and isinstance(action_plan[timeframe], list):
            action_plan[timeframe] = list(dict.fromkeys(action_plan[timeframe]))
        else:
            action_plan[timeframe] = []

    # Ensure all high-priority recommendations are in immediate
    if not action_plan["immediate"]:
        action_plan["immediate"] = [r["recommendation"] for r in recommendations if r.get("priority") == "high"]
    if not action_plan["short_term"]:
        action_plan["short_term"] = [r["recommendation"] for r in recommendations if r.get("priority") == "medium"][:2]
    if not action_plan["long_term"]:
        action_plan["long_term"] = [r["recommendation"] for r in recommendations if r.get("priority") == "low"][:2]
        if not action_plan["long_term"]:
            action_plan["long_term"].append("Revizuiți periodic setările de securitate și confidențialitate.")

    report["action_plan"] = action_plan

# --- Basic Summary Generator ---

def generate_basic_report_summary(report_data: Dict[str, Any]) -> str:
    """
    Generate a basic, human-readable summary of the hygiene report.

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
        for weakness in weaknesses[:3]:
            clean_weakness = weakness.split(':', 1)[-1].strip() if ':' in weakness else weakness
            summary += f"- {clean_weakness}\n"
        summary += "\n"

    immediate_actions = report_data.get('action_plan', {}).get('immediate', [])
    if immediate_actions:
        summary += "**Acțiuni Recomandate Urgent:**\n"
        for action in immediate_actions[:2]:
            summary += f"- {action}\n"

    return summary.strip()

# --- Entry point for testing ---

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Testing digital_hygiene module functions...")

    # Test Questionnaire Loading
    logger.info("\n--- Testing Questionnaire Loading ---")
    questionnaire_test = load_questionnaire()
    if questionnaire_test and any(questionnaire_test.values()):
        logger.info(f"Questionnaire loaded successfully. Categories: {list(questionnaire_test.keys())}")
    else:
        logger.error("Failed to load questionnaire for test.")
        exit()

    # Test Form Processing with dynamic test cases
    logger.info("\n--- Testing Form Processing ---")
    test_cases = [
        {
            "name": "Mixed Responses",
            "responses": {q["id"]: str((i % 2) + 2) for i, q in enumerate([q for cat in questionnaire_test.values() for q in cat])},
            "overrides": {"pass_reuse": "1", "mfa_usage": "4", "device_updates": "1"}
        },
        {
            "name": "Low Security",
            "responses": {q["id"]: "1" for q in [q for cat in questionnaire_test.values() for q in cat]},
            "overrides": {}
        }
    ]

    for test_case in test_cases:
        logger.info(f"\nTesting case: {test_case['name']}")
        test_form = test_case["responses"].copy()
        test_form.update(test_case["overrides"])
        processed_result = process_hygiene_form(test_form)
        if processed_result:
            logger.info(f"Form processed successfully. Overall Score: {processed_result['overall_score']}")
            logger.info(f"Category Scores: {processed_result['category_scores']}")
            logger.info(f"Strengths: {processed_result['strengths']}")
            logger.info(f"Weaknesses: {processed_result['weaknesses']}")
        else:
            logger.error("Failed to process form data.")

    # Test Report Generation
    logger.info("\n--- Testing Report Generation ---")
    if initialize_llm():
        logger.info("LLM initialized for testing.")
    else:
        logger.warning("LLM not available for testing.")

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