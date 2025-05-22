#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - Anti-Dox Toolkit Module
This module provides tools to generate GDPR data erasure request templates based on the ANAF model.
"""

import logging
from typing import Dict, List

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Configure handlers only if not already configured
if not logger.handlers:
    file_handler = logging.FileHandler('identity_guardian.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Supported data types
SUPPORTED_DATA_TYPES = [
    'full_name', 'home_address', 'phone_number', 'email_address',
    'social_media_profiles', 'photos', 'government_id', 'financial_information'
]

# Supported reasons for erasure
SUPPORTED_REASONS = {
    'en': {
        'no_longer_necessary': 'The data is no longer necessary for the purpose it was collected or processed',
        'withdraw_consent': 'I withdraw my consent',
        'object_processing': 'I object to the processing under Article 21(1) GDPR',
        'unlawful_processing': 'The data was processed unlawfully',
        'legal_obligation': 'Compliance with a legal obligation',
        'other': 'Other reasons under GDPR'
    },
    'ro': {
        'no_longer_necessary': 'Datele nu mai sunt necesare pentru scopul pentru care au fost colectate sau prelucrate',
        'withdraw_consent': 'Îmi retrag consimțământul',
        'object_processing': 'Mă opun prelucrării în temeiul Articolului 21 alin. (1) GDPR',
        'unlawful_processing': 'Datele au fost prelucrate ilegal',
        'legal_obligation': 'Respectarea unei obligații legale',
        'other': 'Alte motive conform GDPR'
    }
}

# Templates for GDPR requests based on ANAF model
TEMPLATES = {
    'en': {
        'subject': 'Request for Erasure of Personal Data under GDPR (Article 17)',
        'body': """To: [Name of the Data Controller]
[Address of the Data Controller]

I, [Your Full Name], with [Optional: ID Number, e.g., Passport or National ID], residing at [Your Address], phone [Optional: Phone Number], email [Optional: Email Address], pursuant to Article 17 of Regulation (EU) 2016/679 (General Data Protection Regulation), request the erasure of my personal data from your records.

The specific personal data I request to be erased are: {data_types}

The reason for this request is: {reason}

I have attached the following documents to support my request (original or copy):
- [List any attached documents, e.g., copy of ID, proof of address]

Please send confirmation of the actions taken to:
[Optional: Your Address]
[Optional: Your Email Address]
[Optional: Preferred Correspondence Service]

Date: [Date]
Signature: [Signature]

Sincerely,
[Your Full Name]"""
    },
    'ro': {
        'subject': 'Cerere de ștergere a datelor cu caracter personal conform GDPR (Articolul 17)',
        'body': """Către: [Denumirea operatorului de date]
[Adresa operatorului]

Subsemnatul/Subsemnata [Nume și Prenume], cu cod numeric personal [CNP, opțional], domiciliul/reședința în [Adresa], telefon [Telefon, opțional], 
adresă de e-mail [E-mail, opțional], în temeiul Articolului 17 din Regulamentul (UE) 2016/679 al Parlamentului European și al 
Consiliului din 27 aprilie 2016 privind protecția persoanelor fizice în ceea ce privește prelucrarea datelor cu caracter personal și 
privind libera circulație a acestor date (Regulamentul general privind protecția datelor), vă rog să dispuneți măsurile legale pentru ca 
datele cu caracter personal care mă privesc: {data_types} să fie șterse din evidențele dumneavoastră.

Motivul acestei solicitări este: {reason}

Anexez în original/copie următoarele acte ce constituie temeiul cererii mele:
- [Listați documentele anexate, ex. copie CI, dovadă adresă]

Vă rog să transmiteți informațiile privind măsurile solicitate în baza Regulamentului (UE) 2016/679 la următoarea adresă:
[Adresa, opțional]
[Adresa de e-mail, opțional]
[Serviciu de corespondență preferat, opțional]

Data: [Data]
Semnătura: [Semnătura]

Cu respect,
[Nume și Prenume]"""
    }
}

# Critical information about the erasure process, formatted with bullet points
CRITICAL_INFO = {
    'en': """Important information regarding your GDPR data erasure request:
• Organizations have the right to request additional information to verify your identity, such as a copy of your ID or other proof of identity.
• Ensure your request is justified under GDPR; organizations may refuse erasure if the data is required for legal obligations (e.g., tax or contractual purposes).
• Provide specific details, such as URLs or locations where your data appears, to help the organization process your request efficiently.
• The organization must respond within 30 days, as required by GDPR.""",
    'ro': """Informații importante privind cererea dumneavoastră de ștergere a datelor conform GDPR:
• Organizațiile au dreptul de a solicita informații suplimentare pentru a vă verifica identitatea, cum ar fi o copie a actului de identitate sau alte dovezi.
• Asigurați-vă că solicitarea este justificată conform GDPR; organizațiile pot refuza ștergerea dacă datele sunt necesare pentru obligații legale (ex. fiscale sau contractuale).
• Furnizați detalii specifice, cum ar fi URL-uri sau locații unde apar datele dumneavoastră, pentru a facilita procesarea cererii.
• Organizația trebuie să răspundă în termen de 30 de zile, conform GDPR."""
}

def translate_data_type(data_type: str, language: str) -> str:
    """
    Translate technical data type names to human-readable terms in the specified language.

    Args:
        data_type (str): The technical name of the data type.
        language (str): The language for translation ('en' or 'ro').

    Returns:
        str: Human-readable name for the data type in the specified language.
    """
    translations = {
        'en': {
            'full_name': 'full name',
            'home_address': 'home address',
            'phone_number': 'phone number',
            'email_address': 'email address',
            'social_media_profiles': 'social media profiles',
            'photos': 'personal photos',
            'government_id': 'identification documents/ID number',
            'financial_information': 'financial information'
        },
        'ro': {
            'full_name': 'nume complet',
            'home_address': 'adresă de domiciliu',
            'phone_number': 'număr de telefon',
            'email_address': 'adresă de email',
            'social_media_profiles': 'profiluri de social media',
            'photos': 'fotografii personale',
            'government_id': 'acte de identitate/CNP',
            'financial_information': 'informații financiare'
        }
    }
    return translations.get(language, {}).get(data_type, data_type)

def generate_gdpr_request(language: str, data_types: List[str], reason: str) -> Dict[str, str]:
    """
    Generate a GDPR data erasure request template in the specified language based on the ANAF model.

    Args:
        language (str): The language of the template ('en' or 'ro').
        data_types (List[str]): List of personal data types to be erased.
        reason (str): The key for the reason for the erasure request (e.g., 'no_longer_necessary').

    Returns:
        Dict[str, str]: Contains the formatted request with subject, body, and critical information.
    """
    if language not in TEMPLATES:
        logger.warning(f"Unsupported language: {language}")
        return {
            "status": "error",
            "message": "Limba nesuportată. Vă rugăm să selectați engleză sau română."
        }
    
    for data_type in data_types:
        if data_type not in SUPPORTED_DATA_TYPES:
            logger.warning(f"Unsupported data type: {data_type}")
            return {
                "status": "error",
                "message": f"Tipul de date '{data_type}' nu este suportat. Tipurile valide sunt: {', '.join(SUPPORTED_DATA_TYPES)}"
            }

    if reason not in SUPPORTED_REASONS[language]:
        logger.warning(f"Unsupported reason: {reason}")
        return {
            "status": "error",
            "message": f"Motivul '{reason}' nu este suportat. Motivele valide sunt: {', '.join(SUPPORTED_REASONS[language].keys())}"
        }

    template = TEMPLATES[language]
    critical_info = CRITICAL_INFO.get(language, "")
    
    # Translate and join data types
    translated_data_types = [translate_data_type(data_type, language) for data_type in data_types]
    data_types_text = ", ".join(translated_data_types)
    
    # Get reason text
    reason_text = SUPPORTED_REASONS[language][reason]
    
    # Replace placeholders in the template
    body = template['body'].format(data_types=data_types_text, reason=reason_text)
    
    logger.info(f"Successfully generated GDPR request for language='{language}', data_types={data_types}, reason='{reason}'")
    return {
        "status": "success",
        "subject": template['subject'],
        "body": body,
        "critical_info": critical_info
    }