#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - Anti-Dox Toolkit Module
This module provides tools and resources to help users protect their personal information 
and respond to doxxing incidents.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

# Import configuration with fallback
try:
    import config
except ImportError:
    config = type('Config', (), {
        'SUPPORTED_PLATFORMS': [
            'google', 'facebook', 'twitter', 'instagram', 'linkedin',
            'reddit', 'data_brokers', 'people_search_sites'
        ],
        'SUPPORTED_DATA_TYPES': [
            'full_name', 'home_address', 'phone_number', 'email_address',
            'social_media_profiles', 'photos', 'government_id', 'financial_information'
        ]
    })()

# Optional: Import LLM handler for personalized content generation
try:
    from utils.llm_handler import is_llm_available, generate_hygiene_recommendations
    LLM_AVAILABLE = is_llm_available()
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("LLM handler not available. Using static templates only.")

# Set up logging
logger = logging.getLogger(__name__) # Când este importat, __name__ va fi 'modules.antidox'
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

def get_removal_guides() -> Dict[str, List[Dict[str, Union[str, List[Dict[str, str]]]]]]:
    """
    Generate comprehensive guides for removing personal information from various platforms.

    Returns:
        Dict[str, List[Dict[str, Union[str, List[Dict[str, str]]]]]]: A structured dictionary containing guides organized by categories.
    """
    logger.info("Generating removal guides for supported platforms")
    
    guides = {
        "data_brokers": [],
        "social_media": [],
        "search_engines": [],
        "general_resources": []
    }
    
    supported_platforms = getattr(config, 'SUPPORTED_PLATFORMS', [])
    
    # Data broker removal guides
    if 'data_brokers' in supported_platforms:
        guides["data_brokers"] = [
            {
                "name": "Acxiom",
                "description": "Unul dintre cei mai mari brokeri de date din lume.",
                "opt_out_url": "https://isapps.acxiom.com/optout/optout.aspx",
                "steps": [
                    {"step": "Accesați linkul de opt-out", "details": "Navigați la pagina de opt-out Acxiom"},
                    {"step": "Completați formularul cu informațiile dvs.", "details": "Introduceți numele, adresa, emailul"},
                    {"step": "Confirmați solicitarea prin email", "details": "Veți primi un email de confirmare care trebuie validat"}
                ]
            },
            {
                "name": "Experian",
                "description": "Birou de credit și broker de date consumer.",
                "opt_out_url": "https://www.experian.com/privacy/opting_out",
                "steps": [
                    {"step": "Accesați portalul de confidențialitate", "details": "Navigați la pagina de opt-out Experian"},
                    {"step": "Selectați opțiunea de excludere din marketing", "details": "Alegeți opțiunea de a vă elimina din listele de marketing"},
                    {"step": "Verificați identitatea", "details": "Va trebui să furnizați dovezi ale identității pentru procesare"}
                ]
            },
            {
                "name": "LexisNexis",
                "description": "Furnizor de informații legale și business analytics.",
                "opt_out_url": "https://optout.lexisnexis.com/",
                "steps": [
                    {"step": "Completați formularul online", "details": "Introduceți informațiile personale care doriți să fie eliminate"},
                    {"step": "Furnizați o copie a actului de identitate", "details": "Pentru verificare, va trebui să trimiteți copii ale documentelor"},
                    {"step": "Așteptați confirmarea", "details": "Procesul poate dura până la 30 de zile"}
                ]
            },
            {
                "name": "Oracle Data Cloud",
                "description": "Platformă de date pentru marketing și advertising.",
                "opt_out_url": "https://datacloudoptout.oracle.com/optout",
                "steps": [
                    {"step": "Accesați pagina de opt-out", "details": "Navigați la linkul Oracle Data Cloud"},
                    {"step": "Completați informațiile cerute", "details": "Furnizați emailul și alte informații solicitate"},
                    {"step": "Confirmați opțiunea de opt-out", "details": "Confirmați că doriți să fiți exclus din baza lor de date"}
                ]
            },
            {
                "name": "Whitepages",
                "description": "Serviciu de căutare persoane și verificare identitate.",
                "opt_out_url": "https://www.whitepages.com/suppression-requests",
                "steps": [
                    {"step": "Găsiți-vă profilul", "details": "Căutați-vă numele pentru a localiza profilul dvs."},
                    {"step": "Copiați URL-ul profilului", "details": "Copiați adresa completă a paginii profilului"},
                    {"step": "Completați formularul de eliminare", "details": "Furnizați URL-ul și motivul eliminării"},
                    {"step": "Verificați prin telefon/email", "details": "Confirmați solicitarea prin codul primit"}
                ]
            }
        ]
    
    # Social media removal guides
    if any(platform in supported_platforms for platform in ['facebook', 'twitter', 'instagram', 'linkedin', 'reddit']):
        guides["social_media"] = [
            {
                "name": "Facebook",
                "description": "Setări de confidențialitate și eliminare conținut.",
                "privacy_url": "https://www.facebook.com/settings?tab=privacy",
                "steps": [
                    {"step": "Accesați setările de confidențialitate", "details": "Navigați la Setări > Confidențialitate"},
                    {"step": "Limitați vizibilitatea profilului", "details": "Setați postările și informațiile personale la 'Doar prieteni'"},
                    {"step": "Verificați tagurile și mențiunile", "details": "Activați revizuirea tagurilor înainte de a apărea pe profil"},
                    {"step": "Folosiți instrumentul 'Descarcă informațiile'", "details": "Pentru a vedea ce date sunt stocate despre dvs."}
                ]
            },
            {
                "name": "Twitter/X",
                "description": "Protejarea contului și eliminarea informațiilor.",
                "privacy_url": "https://twitter.com/settings/privacy_and_safety",
                "steps": [
                    {"step": "Setați contul ca privat", "details": "Activați 'Protejați-vă postările' din setările de confidențialitate"},
                    {"step": "Dezactivați locația", "details": "Dezactivați adăugarea locației în tweet-uri"},
                    {"step": "Limitați descoperirea", "details": "Dezactivați găsirea contului prin email sau număr de telefon"},
                    {"step": "Verificați tweeturile vechi", "details": "Ștergeți postările cu informații personale"}
                ]
            },
            {
                "name": "Instagram",
                "description": "Setări confidențialitate și eliminare conținut.",
                "privacy_url": "https://www.instagram.com/accounts/privacy_and_security/",
                "steps": [
                    {"step": "Setați contul ca privat", "details": "Activați 'Cont privat' din setările de confidențialitate"},
                    {"step": "Verificați tagurile în poze", "details": "Activați revizuirea manuală a tagurilor"},
                    {"step": "Limitați comentariile", "details": "Restricționați cine poate comenta la postările dvs."},
                    {"step": "Verificați informațiile din bio", "details": "Eliminați date personale din biografie și postări"}
                ]
            },
            {
                "name": "LinkedIn",
                "description": "Protejarea profilului profesional.",
                "privacy_url": "https://www.linkedin.com/psettings/",
                "steps": [
                    {"step": "Ajustați vizibilitatea profilului", "details": "Setați cine poate vedea activitatea și detaliile profilului"},
                    {"step": "Verificați informațiile de contact", "details": "Limitați cine poate vedea emailul și telefonul"},
                    {"step": "Gestionați conexiunile", "details": "Revizuiți lista de conexiuni și eliminați persoanele necunoscute"},
                    {"step": "Controlați vizibilitatea companiei/școlii", "details": "Ajustați cât de multe detalii să fie vizibile despre educație și experiență"}
                ]
            },
            {
                "name": "Reddit",
                "description": "Anonimizarea contului și eliminarea postărilor.",
                "privacy_url": "https://www.reddit.com/settings/privacy",
                "steps": [
                    {"step": "Verificați istoricul postărilor", "details": "Ștergeți comentariile și postările cu informații personale"},
                    {"step": "Utilizați script-uri pentru eliminare în masă", "details": "Folosiți instrumente precum 'Reddit Overwrite' pentru a șterge istoricul"},
                    {"step": "Dezactivați opțiunile de personalizare", "details": "Dezactivați personalizarea bazată pe locație și interese"},
                    {"step": "Creați un cont nou", "details": "În cazuri extreme, abandonați contul actual și creați unul nou"}
                ]
            }
        ]
    
    # Search engine removal guides
    if 'google' in supported_platforms:
        guides["search_engines"] = [
            {
                "name": "Google",
                "description": "Eliminarea informațiilor personale din rezultatele de căutare.",
                "removal_url": "https://support.google.com/websearch/answer/9673730",
                "steps": [
                    {"step": "Accesați formularul de eliminare", "details": "Navigați la pagina de asistență Google pentru eliminarea informațiilor personale"},
                    {"step": "Selectați tipul de conținut", "details": "Alegeți categoria potrivită: informații personale, imagini explicite, etc."},
                    {"step": "Furnizați URL-urile exacte", "details": "Trebuie să furnizați linkurile exacte către paginile care conțin informațiile"},
                    {"step": "Explicați motivul eliminării", "details": "Descrieți de ce conținutul reprezintă un risc pentru dvs."},
                    {"step": "Furnizați informații de contact", "details": "Google vă va contacta referitor la solicitare"}
                ]
            },
            {
                "name": "Bing",
                "description": "Eliminarea conținutului din motorul de căutare Microsoft.",
                "removal_url": "https://www.bing.com/webmaster/tools/eu-privacy-request",
                "steps": [
                    {"step": "Folosiți formularul de solicitare", "details": "Accesați pagina de solicitare de eliminare Bing"},
                    {"step": "Furnizați URL-urile rezultatelor", "details": "Copiați adresele exacte ale rezultatelor problematice"},
                    {"step": "Oferiți detalii despre conținut", "details": "Explicați ce informații personale sunt expuse"},
                    {"step": "Furnizați informații de contact", "details": "Pentru a primi actualizări despre solicitare"}
                ]
            },
            {
                "name": "DuckDuckGo",
                "description": "Gestionarea informațiilor personale în rezultatele de căutare.",
                "info_url": "https://help.duckduckgo.com/duckduckgo-help-pages/results/sources/",
                "steps": [
                    {"step": "Înțelegeți limitările", "details": "DuckDuckGo utilizează rezultate de la Bing și alte surse"},
                    {"step": "Contactați sursele originale", "details": "Trebuie să contactați site-urile unde apar informațiile"},
                    {"step": "Solicitați eliminare la Bing", "details": "Urmați procedura de eliminare de la Bing"},
                    {"step": "Contactați echipa DuckDuckGo", "details": "Pentru cazuri specifice, folosiți formularul lor de contact"}
                ]
            }
        ]
    
    # General resources
    guides["general_resources"] = [
        {
            "name": "Plan de Urgență în Caz de Doxxing",
            "description": "Pași de urmat dacă sunteți victima unui incident de doxxing.",
            "steps": [
                {"step": "Documentați totul", "details": "Faceți capturi de ecran și păstrați linkuri către conținutul problematic"},
                {"step": "Contactați platformele", "details": "Raportați conținutul la site-urile unde a fost postat"},
                {"step": "Securizați-vă conturile", "details": "Schimbați parolele și activați autentificarea cu doi factori"},
                {"step": "Alertați instituțiile financiare", "details": "Dacă au fost expuse informații financiare, contactați banca"},
                {"step": "Contactați autoritățile", "details": "În cazuri grave, implicați poliția sau ANSPDCP"}
            ]
        },
        {
            "name": "Checklist Confidențialitate Online",
            "description": "Verificări regulate pentru a vă proteja identitatea online.",
            "steps": [
                {"step": "Verificați setările de confidențialitate", "details": "Revizuiți periodic setările rețelelor sociale"},
                {"step": "Căutați-vă numele online", "details": "Folosiți diverse motoare de căutare pentru a vedea ce informații sunt publice"},
                {"step": "Monitorizați conturile", "details": "Verificați activitatea conturilor pentru accesări neautorizate"},
                {"step": "Revizuiți aplicațiile conectate", "details": "Eliminați aplicațiile terțe care au acces la conturile dvs."},
                {"step": "Utilizați alerte Google", "details": "Creați alerte pentru numele dvs. pentru a fi notificat când apare online"}
            ]
        },
        {
            "name": "Resurse Legale",
            "description": "Informații despre drepturile legale privind protecția datelor.",
            "resources": [
                {"name": "GDPR - Dreptul la ștergere", "url": "https://www.dataprotection.ro/?page=Regulamentul_GDPR"},
                {"name": "ANSPDCP - Autoritatea Națională de Supraveghere", "url": "https://www.dataprotection.ro/"},
                {"name": "Legislație privind hărțuirea online", "url": "http://legislatie.just.ro/Public/DetaliiDocument/193949"}
            ]
        }
    ]
    
    return guides

def generate_gdpr_request(data_type: str, service: str) -> Dict[str, str]:
    """
    Generate a personalized GDPR removal request template for specific data types and services.

    Args:
        data_type (str): Type of personal data to be removed (e.g., 'full_name', 'home_address').
        service (str): The platform or service to send the request to (e.g., 'google', 'facebook').

    Returns:
        Dict[str, str]: Contains the formatted request with subject, body, instructions, and additional notes.
    """
    logger.info(f"Generating GDPR removal request for data_type='{data_type}' and service='{service}'")
    
    supported_data_types = getattr(config, 'SUPPORTED_DATA_TYPES', [])
    supported_platforms = getattr(config, 'SUPPORTED_PLATFORMS', [])
    
    if data_type not in supported_data_types:
        logger.warning(f"Unsupported data type: {data_type}")
        return {
            "status": "error",
            "message": f"Tipul de date '{data_type}' nu este suportat. Tipurile valide sunt: {', '.join(supported_data_types)}"
        }
    
    if service not in supported_platforms:
        logger.warning(f"Unsupported service: {service}, falling back to generic template")
        template_key = "generic"
    else:
        template_key = service
    
    # Define templates
    templates = {
        "generic": {
            "subject": "Solicitare de ștergere a datelor personale în baza GDPR (Articolul 17)",
            "body": """Stimate departament de confidențialitate,

Prin prezenta, solicit eliminarea imediată a datelor mele personale din baza dvs. de date, în conformitate cu Articolul 17 din Regulamentul General privind Protecția Datelor (GDPR).

Informații personale care apar pe platforma dvs.:
- Tip de date: {data_type}
- URL sau locația datelor (dacă se cunoaște): [Introduceți URL-ul sau secțiunea unde se află informațiile]
- Informații adiționale pentru identificare: [Furnizați detalii care să ajute la identificarea datelor]

În conformitate cu GDPR, aveți obligația legală de a răspunde în termen de 30 de zile. Vă rog să confirmati prin email când datele au fost eliminate.

Vă mulțumesc pentru promptitudine,

[Your name]
[Your contact information]""",
            "instructions": """
1. Personalizați șablonul cu informațiile specifice.
2. Trimiteți solicitarea la adresa de email dedicată protecției datelor a companiei.
3. Păstrați o copie a comunicării pentru evidență.
4. Urmăriți răspunsul în termen de 30 de zile.
""",
            "additional_notes": """
Notă: Pentru cetățenii UE, GDPR vă oferă dreptul de a solicita ștergerea datelor personale. Pentru non-UE, verificați legislația locală.
"""
        },
        "data_brokers": {
            "subject": "Solicitare de ștergere a datelor personale în baza GDPR (Articolul 17)",
            "body": """Stimate departament de confidențialitate,

Prin prezenta, solicit eliminarea imediată a datelor mele personale din baza dvs. de date și de pe site-ul dvs., în conformitate cu Articolul 17 din Regulamentul General privind Protecția Datelor (GDPR).

Informații personale care apar pe platforma dvs.:
- Tip de date: {data_type}
- URL sau locația datelor (dacă se cunoaște): [Introduceți URL-ul sau secțiunea unde se află informațiile]
- Informații adiționale pentru identificare: [Furnizați detalii care să ajute la identificarea datelor]

În conformitate cu GDPR, aveți obligația legală de a răspunde acestei solicitări în termen de 30 de zile. Vă rog să îmi confirmați prin email atunci când datele mele au fost eliminate complet.

Pentru verificarea identității mele, am atașat [menționați documentele furnizate, de exemplu o copie a cărții de identitate cu datele sensibile ascunse].

Vă mulțumesc pentru promptitudine,

[Your name]
[Your contact information]""",
            "instructions": """
1. Personalizați acest șablon cu informațiile dvs. specifice.
2. Atașați dovezi de identitate (cu datele sensibile ascunse).
3. Trimiteți solicitarea la adresa de email dedicată protecției datelor a companiei.
4. Păstrați o copie a comunicării pentru evidențele dvs.
5. Urmăriți răspunsul în termen de 30 de zile.
""",
            "additional_notes": """
Notă: Pentru cetățenii UE, GDPR vă oferă dreptul legal de a solicita ștergerea datelor personale. Pentru cetățenii din afara UE, vă puteți baza pe CCPA (California) sau alte legi locale privind protecția datelor.
"""
        },
        "facebook": {
            "subject": "Solicitare de eliminare a conținutului personal neautorizat",
            "body": """Către Echipa Facebook de Asistență,

Vă scriu pentru a solicita eliminarea urgentă a informațiilor mele personale care au fost postate fără consimțământul meu pe platforma dvs.

Detalii despre conținutul raportat:
- Tipul informațiilor: {data_type}
- URL-ul postării/conținutului: [Introduceți linkul exact]
- Numele utilizatorului/paginii care a postat conținutul: [Nume utilizator/pagină]
- Data aproximativă a postării: [Data]

Am încercat să rezolv această problemă folosind instrumentele de raportare ale platformei, dar conținutul rămâne public. Această expunere a informațiilor mele personale îmi pune în pericol siguranța și confidențialitatea.

În conformitate cu Politica de Confidențialitate Facebook și cu Termenii de Utilizare, solicit eliminarea imediată a acestui conținut.

Vă mulțumesc pentru atenția acordată acestei probleme urgente.

Cu respect,
[Your name]
[Your contact information]""",
            "instructions": """
1. Completați toate câmpurile din șablon cu informațiile specifice.
2. Trimiteți solicitarea prin formularul oficial Facebook de raportare sau prin email.
3. Furnizați URL-uri exacte - fără acestea, Facebook nu poate localiza conținutul.
4. Dacă nu primiți un răspuns în 48-72 de ore, trimiteți din nou solicitarea.
""",
            "additional_notes": """
Important: Facebook prioritizează solicitările care implică informații foarte sensibile (CNP, date financiare) sau situații de siguranță personală. Menționați clar dacă există un risc pentru siguranța dvs.
"""
        },
        "google": {
            "subject": "Solicitare de eliminare a informațiilor personale din rezultatele de căutare Google",
            "body": """Către Echipa Google de Asistență,

Prin prezenta, solicit eliminarea următoarelor URL-uri din rezultatele de căutare Google, deoarece conțin informații personale care îmi pun în pericol confidențialitatea și siguranța.

URL-uri care conțin informațiile mele personale:
1. [Introduceți URL complet]
2. [Introduceți URL complet]
3. [Adăugați mai multe URL-uri dacă este necesar]

Tipul de informații personale expuse: {data_type}

Termenii de căutare care afișează aceste rezultate:
1. [Termen de căutare, de ex. "numele meu complet"]
2. [Alți termeni de căutare relevanți]

Am încercat să contactez administratorii site-urilor pentru a elimina conținutul, dar [explicați rezultatul acestor încercări].

În conformitate cu politica Google privind eliminarea informațiilor personale (https://support.google.com/websearch/answer/9673730) și cu GDPR Articolul 17, solicit eliminarea acestor URL-uri din rezultatele de căutare.

Vă mulțumesc pentru atenția acordată acestei solicitări.

Cu respect,
[Your name]
[Your contact information]""",
            "instructions": """
1. Utilizați formularul oficial Google pentru eliminarea informațiilor personale: https://support.google.com/websearch/troubleshooter/9685456
2. Furnizați URL-uri exacte pentru toate paginile care conțin informațiile dvs.
3. Explicați clar de ce informațiile reprezintă un risc (doxxing, hărțuire, risc de fraudă).
4. Atașați capturi de ecran care arată informațiile personale (cu evidențierea clară a acestora).
5. Dacă cererea este respinsă, puteți trimite o solicitare revizuită cu mai multe detalii.
""",
            "additional_notes": """
Important: Google nu elimină de obicei informații care sunt relevante din punct de vedere al interesului public sau informații oficiale/legale. Concentrați-vă pe riscul specific pentru dvs. și explicați de ce eliminarea este justificată.
"""
        }
    }
    
    # Map social media platforms to the facebook template
    if service in ["twitter", "instagram", "linkedin", "reddit"]:
        template_key = "facebook"
    elif service == "people_search_sites":
        template_key = "data_brokers"
    
    template = templates.get(template_key, templates["generic"])
    template["body"] = template["body"].format(data_type=translate_data_type(data_type))
    template["status"] = "success"
    
    logger.info(f"Successfully generated GDPR request for {service}")
    return template

def track_removal_request(platform: str, request_date: str, status: str = "pending") -> Dict[str, any]:
    """
    Track the status of a removal request for a specific platform, persisting to a JSON file.

    Args:
        platform (str): The platform or service the request was sent to.
        request_date (str): The date the request was submitted (ISO format or readable).
        status (str): Current status of the request (e.g., 'pending', 'in_progress', 'completed').

    Returns:
        Dict[str, any]: Tracking information including platform, date, status, and notes.
    """
    logger.info(f"Tracking removal request for platform='{platform}', date='{request_date}', status='{status}'")
    
    supported_platforms = getattr(config, 'SUPPORTED_PLATFORMS', [])
    
    if platform not in supported_platforms:
        logger.warning(f"Unsupported platform: {platform}")
        return {
            "status": "error",
            "message": f"Platforma '{platform}' nu este suportată. Platformele valide sunt: {', '.join(supported_platforms)}"
        }
    
    tracking = {
        "status": "success",
        "platform": platform,
        "request_date": request_date,
        "current_status": status,
        "notes": [],
        "last_updated": datetime.now().isoformat()
    }
    
    # Add notes based on status
    status_notes = {
        "pending": ["Așteptați confirmarea de la platformă. Verificați emailul în 30 de zile."],
        "in_progress": ["Solicitarea este în proces. Contactați platforma dacă nu primiți actualizări în 15 zile."],
        "completed": ["Solicitarea a fost finalizată. Verificați online dacă datele au fost eliminate."]
    }
    tracking["notes"] = status_notes.get(status, ["Status necunoscut. Verificați manual stadiul solicitării."])
    
    # Persist to JSON file (for demonstration; use a database in production)
    tracking_file = "removal_requests.json"
    try:
        # Load existing requests
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r', encoding='utf-8') as f:
                requests = json.load(f)
        else:
            requests = {}
        
        # Update with new request
        request_key = f"{platform}_{request_date}"
        requests[request_key] = tracking
        
        # Save back to file
        with open(tracking_file, 'w', encoding='utf-8') as f:
            json.dump(requests, f, indent=2)
        
        logger.info(f"Successfully saved tracking data to {tracking_file}")
    except Exception as e:
        logger.error(f"Failed to save tracking data: {str(e)}")
        tracking["notes"].append(f"Eroare la salvarea datelor: {str(e)}")
    
    return tracking

def get_privacy_checklist() -> List[Dict[str, str]]:
    """
    Retrieve a checklist for regular online privacy maintenance.

    Returns:
        List[Dict[str, str]]: A list of checklist items with steps and details.
    """
    logger.info("Retrieving privacy checklist")
    
    checklist = [
        {
            "step": "Verificați setările de confidențialitate",
            "details": "Revizuiți periodic setările rețelelor sociale și ale aplicațiilor."
        },
        {
            "step": "Căutați-vă numele online",
            "details": "Folosiți diverse motoare de căutare pentru a verifica ce informații sunt publice."
        },
        {
            "step": "Monitorizați conturile",
            "details": "Verificați activitatea conturilor pentru accesări neautorizate."
        },
        {
            "step": "Revizuiți aplicațiile conectate",
            "details": "Eliminați aplicațiile terțe care au acces la conturile dvs."
        },
        {
            "step": "Utilizați alerte Google",
            "details": "Creați alerte pentru numele dvs. pentru a fi notificat când apare online."
        }
    ]
    
    return checklist

def translate_data_type(data_type: str) -> str:
    """
    Translate technical data type names to human-readable Romanian terms.

    Args:
        data_type (str): The technical name of the data type.

    Returns:
        str: Human-readable Romanian name for the data type.
    """
    translations = {
        "full_name": "numele complet",
        "home_address": "adresa de domiciliu",
        "phone_number": "numărul de telefon",
        "email_address": "adresa de email",
        "social_media_profiles": "profilurile de social media",
        "photos": "fotografiile personale",
        "government_id": "documentele de identitate/CNP",
        "financial_information": "informațiile financiare",
    }
    
    return translations.get(data_type, data_type)