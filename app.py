#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - A Self-Defense Toolkit for Online Identity Protection
Main application file (app.py) - Modified for Global Data Persistence (No Flask Sessions)
"""

import logging
from flask import Flask, render_template, request, flash, redirect, url_for
import os
import json
import sqlite3
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import configuration
try:
    import config
except ImportError:
    class MockConfig:
        SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_please_change")
        DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
        HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
        PORT = int(os.environ.get("FLASK_PORT", 5000))
        ENABLE_LLM_REPORTS = os.environ.get("ENABLE_LLM_REPORTS", "true").lower() == "true"
        DB_PATH = 'identity_guardian.db'
    config = MockConfig()
    logging.warning("config.py not found, using environment variables or defaults.")
    if config.SECRET_KEY == "default_secret_key_please_change":
        logging.critical("CRITICAL: Flask SECRET_KEY is not set securely! Flash messages might not work properly.")

# Initialize Flask Application
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
if not app.secret_key:
    logging.critical("CRITICAL: Flask SECRET_KEY is not set. Flash messages will not work.")

# Import Module Functions
try:
    from modules.exposure_monitor import check_email_exposure, search_username_exposure
except ImportError:
    logging.error("Could not import from modules.exposure_monitor")
    def check_email_exposure(*args, **kwargs): return {"error": "Module unavailable"}
    def search_username_exposure(*args, **kwargs): return {"error": "Module unavailable"}

try:
    from modules.digital_hygiene import load_questionnaire, process_hygiene_form, generate_hygiene_report
except ImportError:
    logging.error("Could not import from modules.digital_hygiene")
    def load_questionnaire(*args, **kwargs): return {}
    def process_hygiene_form(*args, **kwargs): return None
    def generate_hygiene_report(*args, **kwargs): return None

try:
    from modules.antidox_toolkit import generate_gdpr_request
except ImportError:
    logging.error("Could not import from modules.antidox_toolkit")
    def generate_gdpr_request(*args, **kwargs): return {"status": "error", "message": "Module unavailable"}

# Import and Initialize Utilities & Database
try:
    from utils.api_clients import initialize_api_clients
except ImportError:
    logging.error("Could not import/initialize from utils.api_clients")
    def initialize_api_clients(): pass

try:
    from utils.llm_handler import initialize_llm
except ImportError:
    logging.error("Could not import/initialize from utils.llm_handler")
    def initialize_llm(): pass

try:
    from utils.database import save_report, get_reports_by_type, get_report_detail
    DATABASE_AVAILABLE = True
except ImportError:
    logging.critical("CRITICAL: Could not import database functions from utils.database. Database features unavailable.")
    DATABASE_AVAILABLE = False
    def save_report(*args, **kwargs): return None
    def get_reports_by_type(*args, **kwargs): return []
    def get_report_detail(*args, **kwargs): return None

# Helper Functions for Report Detail
def fetch_mentions(report_id):
    """Fetch username mentions for an exposure report."""
    try:
        report_data = get_report_detail(report_id)
        if not report_data:
            app.logger.error(f"No report data found for report_id {report_id}")
            return []
        full_report = report_data.get('full_report')
        if not isinstance(full_report, dict):
            app.logger.error(f"Invalid full_report for report_id {report_id}: {full_report}")
            return []
        username_report = full_report.get('username_report') or {
            'found_on': [],
            'pastes': [],
            'input_type': 'none',
            'status': 'success',
            'risk_level': 'low'
        }
        if not isinstance(username_report, dict):
            app.logger.warning(f"username_report is not a dict for report_id {report_id}: {username_report}")
            return []
        found_on = username_report.get('found_on', [])
        return [
            {
                'platform': m.get('platform', 'Unknown'),
                'url': m.get('url', ''),
                'snippet': m.get('snippet', m.get('note', '')),
                'confirmed': m.get('confirmed', False)
            }
            for m in found_on
            if m.get('platform') in ['github', 'twitter', 'reddit', 'instagram', 
                                    'facebook', 'linkedin', 'youtube', 'pinterest']
        ]
    except Exception as e:
        app.logger.error(f"Error fetching mentions for report {report_id}: {str(e)}")
        return []

def fetch_recommendations(report_id, type_):
    """Fetch recommendations for email or username exposure reports."""
    try:
        report_data = get_report_detail(report_id)
        if not report_data:
            app.logger.error(f"No report data found for report_id {report_id}")
            return []
        full_report = report_data.get('full_report')
        if not isinstance(full_report, dict):
            app.logger.error(f"Invalid full_report for report_id {report_id}: {full_report}")
            return []
        if type_ == 'email':
            return full_report.get('email_report', {}).get('recommendations', [])
        username_report = full_report.get('username_report') or {
            'found_on': [],
            'pastes': [],
            'input_type': 'none',
            'status': 'success',
            'risk_level': 'low'
        }
        if not isinstance(username_report, dict):
            app.logger.warning(f"username_report is not a dict for report_id {report_id}: {username_report}")
            return []
        return username_report.get('recommendations', [])
    except Exception as e:
        app.logger.error(f"Error fetching recommendations for report {report_id}, type {type_}: {str(e)}")
        return []

# Initialize external services at startup within app context
with app.app_context():
    try:
        initialize_api_clients()
    except Exception as e:
        app.logger.error(f"Error initializing API Clients: {e}", exc_info=True)
    try:
        initialize_llm()
    except Exception as e:
        app.logger.error(f"Error initializing LLM Handler: {e}", exc_info=True)

# Route Definitions

@app.route('/')
def index():
    """Render the home/landing page."""
    return render_template('index.html', title="Identity Guardian - Protejează-ți Identitatea Digitală")

@app.route('/exposure-monitor', methods=['GET', 'POST'])
def exposure_monitor():
    """Handle the exposure monitor page and form submission."""
    last_check_summary = None
    current_results = None

    if request.method == 'GET' and DATABASE_AVAILABLE:
        previous_checks = get_reports_by_type('exposure', limit=1)
        if previous_checks:
            last_check_summary = previous_checks[0]
            app.logger.info(f"Found last global exposure check: {last_check_summary.get('report_id')}")

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        query = request.form.get('query', '').strip()

        if not email and not query:
            flash('Introduceți cel puțin un email sau un username/nume complet pentru verificare.', 'warning')
            return render_template('exposure.html',
                                  title="Monitorizare Expunere - Identity Guardian",
                                  last_check=last_check_summary,
                                  current_results=current_results)
        elif not DATABASE_AVAILABLE:
            flash('Funcționalitatea bazei de date nu este disponibilă.', 'danger')
            return render_template('exposure.html',
                                  title="Monitorizare Expunere - Identity Guardian",
                                  last_check=last_check_summary,
                                  current_results=current_results)

        try:
            email_results = check_email_exposure(email) if email else None
            # Set default username_results if query is empty
            username_results = search_username_exposure(query) if query else {
                'status': 'success',
                'found_on': [],
                'pastes': [],
                'risk_level': 'low',
                'input_type': 'none',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            app.logger.debug(f"Email results: {json.dumps(email_results, default=str)}")
            app.logger.debug(f"Username results: {json.dumps(username_results, default=str)}")

            current_results = {
                'query': {'email': email, 'query': query},
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'email_report': email_results,
                'username_report': username_results,
                'combined_risk': 'low',
                'paste_count': 0
            }
            if email_results and email_results.get('risk_level') in ['high', 'medium']:
                current_results['combined_risk'] = email_results.get('risk_level')
            elif username_results and username_results.get('found_on'):
                current_results['combined_risk'] = 'medium' if current_results['combined_risk'] == 'low' else current_results['combined_risk']

            paste_count = 0
            if email_results and 'pastes' in email_results:
                paste_count += len(email_results['pastes'])
            if username_results and 'pastes' in username_results:
                paste_count += len(username_results['pastes'])
            current_results['paste_count'] = paste_count
            app.logger.debug(f"Calculated paste_count: {paste_count} (email: {len(email_results['pastes']) if email_results and 'pastes' in email_results else 0}, username: {len(username_results['pastes']) if username_results and 'pastes' in username_results else 0})")

            flash('Verificare expunere completă.', 'success')

            summary_data = {
                'type': 'exposure',
                'email': email,
                'query': query,
                'input_type': username_results.get('input_type', 'none'),
                'risk': current_results['combined_risk'],
                'breach_count': email_results.get('total_breaches', 0) if email_results else 0,
                'mention_count': len(username_results.get('found_on', [])),
                'paste_count': paste_count
            }
            app.logger.debug(f"Saving report with summary_data: {summary_data}")
            report_id = save_report('exposure', summary_data, current_results)
            if report_id:
                app.logger.info(f"Exposure check saved with global ID {report_id}")
                current_results['report_id'] = report_id
                last_check_summary = {'report_id': report_id, 'timestamp': current_results['timestamp'], 'summary_data': summary_data}
            else:
                app.logger.error("Failed to save exposure check")

        except Exception as e:
            app.logger.error(f"Error during exposure check: {e}", exc_info=True)
            flash(f'A apărut o eroare în timpul verificării expunerii: {str(e)}', 'danger')
            return render_template('exposure.html',
                                  title="Monitorizare Expunere - Identity Guardian",
                                  last_check=last_check_summary,
                                  current_results=current_results)

    app.logger.debug(f"Rendering exposure.html with current_results: {current_results}, last_check: {last_check_summary}")
    return render_template('exposure.html',
                          title="Monitorizare Expunere - Identity Guardian",
                          last_check=last_check_summary,
                          current_results=current_results)

@app.route('/digital-hygiene', methods=['GET', 'POST'])
def digital_hygiene():
    """Handle the digital hygiene assessment page and form submission."""
    last_report_summary = None
    questionnaire = {}
    current_hygiene_report = None

    try:
        questionnaire = load_questionnaire()
    except Exception as e:
        app.logger.error(f"Failed to load questionnaire in route: {e}", exc_info=True)
        flash('Eroare la încărcarea chestionarului.', 'danger')

    if request.method == 'GET' and DATABASE_AVAILABLE:
        previous_reports = get_reports_by_type('hygiene', limit=1)
        if previous_reports:
            last_report_summary = previous_reports[0]
            app.logger.info(f"Found last global hygiene report: {last_report_summary.get('report_id')}")

    if request.method == 'POST':
        form_data = request.form.to_dict()
        if not form_data:
            flash('Nu au fost primite date din formular.', 'warning')
        elif not DATABASE_AVAILABLE:
            flash('Funcționalitatea bazei de date nu este disponibilă.', 'danger')
        else:
            try:
                processed_data = process_hygiene_form(form_data)
                if processed_data:
                    current_hygiene_report = generate_hygiene_report(processed_data)
                    if current_hygiene_report:
                        flash('Evaluarea ta a fost finalizată!', 'success')
                        summary_data = {
                            'type': 'hygiene',
                            'score': current_hygiene_report.get('overall_score', 0),
                            'risk': current_hygiene_report.get('risk_level', 'necunoscut')
                        }
                        report_id = save_report('hygiene', summary_data, current_hygiene_report)
                        if report_id:
                            app.logger.info(f"Hygiene report saved with global ID {report_id}")
                            current_hygiene_report['report_id'] = report_id
                            last_report_summary = {'report_id': report_id, 'timestamp': current_hygiene_report['generated_at'], 'summary_data': summary_data}
                        else:
                            app.logger.error("Failed to save hygiene report")
                    else:
                        flash('Nu s-a putut genera raportul de igienă.', 'danger')
                else:
                    flash('Nu s-au putut procesa datele formularului.', 'danger')
            except Exception as e:
                app.logger.error(f"Error processing hygiene form or generating report: {e}", exc_info=True)
                flash('A apărut o eroare internă la procesarea evaluării.', 'danger')

    return render_template('hygiene.html',
                          title="Evaluare Igienă Digitală - Identity Guardian",
                          questionnaire=questionnaire,
                          last_report=last_report_summary,
                          current_hygiene_report=current_hygiene_report)

@app.route('/digital-hygiene-report/<int:report_id>')
def digital_hygiene_report(report_id):
    """Render the detailed digital hygiene report for a specific report ID."""
    if not DATABASE_AVAILABLE:
        flash("Funcționalitatea bazei de date nu este disponibilă.", "danger")
        return redirect(url_for('digital_hygiene'))

    report_data = get_report_detail(report_id)
    if not report_data or not isinstance(report_data.get('full_report'), dict):
        app.logger.error(f"Invalid or missing report data for report_id {report_id}: {report_data}")
        flash('Raportul specificat nu a fost găsit sau este corupt.', 'danger')
        return redirect(url_for('digital_hygiene'))

    full_report = report_data.get('full_report')
    summary_data = full_report.get('summary_data', full_report)
    if not summary_data:
        app.logger.error(f"Hygiene report {report_id} lacks valid summary_data.")
        flash("Raportul de igienă digitală este corupt sau incomplet.", "danger")
        return redirect(url_for('digital_hygiene'))

    report = {
        'timestamp': report_data.get('timestamp', ''),
        'report_id': report_id,
        'summary_data': summary_data
    }

    return render_template('hygiene_report_detail.html',
                          title="Detalii Raport Igienă Digitală - Identity Guardian",
                          report=report)

@app.route('/antidox-toolkit', methods=['GET', 'POST'])
def antidox_toolkit():
    """Render the anti-dox toolkit page and handle removal request generation."""
    request_template = None

    if request.method == 'POST':
        language = request.form.get('language')
        data_types = request.form.getlist('data_types')  # Get list of selected data types
        reason = request.form.get('reason')

        if not language or not data_types or not reason:
            flash('Vă rugăm să selectați limba, cel puțin un tip de date și motivul ștergerii.', 'error')
        else:
            try:
                request_template = generate_gdpr_request(language, data_types, reason)
                if request_template.get('status') == 'error':
                    flash(request_template.get('message', 'Eroare la generarea cererii.'), 'error')
                else:
                    flash('Cererea de eliminare a fost generată cu succes.', 'success')
            except Exception as e:
                app.logger.error(f"Failed to generate GDPR request: {e}", exc_info=True)
                flash(f'Eroare la generarea cererii: {str(e)}', 'error')

    return render_template('antidox.html',
                          title="Anti-Dox Toolkit - Identity Guardian",
                          request_template=request_template)

@app.route('/report-detail/<int:report_id>')
def report_detail(report_id):
    """Show details of a specific exposure report (not hygiene reports)."""
    if not DATABASE_AVAILABLE:
        flash("Funcționalitatea bazei de date nu este disponibilă.", "danger")
        return redirect(url_for('dashboard'))

    report_data = get_report_detail(report_id)
    app.logger.debug(f"Report data for report_id {report_id}: {report_data}")
    
    if not report_data or not isinstance(report_data.get('full_report'), dict):
        app.logger.error(f"Invalid or missing report data for report_id {report_id}: {report_data}")
        flash('Raportul specificat nu a fost găsit sau este corupt.', 'danger')
        return redirect(url_for('dashboard'))

    module_type = report_data.get('module_type')
    full_report = report_data.get('full_report')

    if not module_type:
        app.logger.error(f"Missing module_type for report_id {report_id}")
        flash('Tip de raport necunoscut.', 'danger')
        return redirect(url_for('dashboard'))

    if module_type == 'exposure':
        email_report = full_report.get('email_report', {})
        # Ensure username_report is a dict, even if stored as None or invalid
        username_report = full_report.get('username_report') or {
            'found_on': [],
            'pastes': [],
            'input_type': 'none',
            'status': 'success',
            'risk_level': 'low',
            'timestamp': report_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        }
        if not isinstance(username_report, dict):
            app.logger.warning(f"username_report is not a dict for report_id {report_id}: {username_report}")
            username_report = {
                'found_on': [],
                'pastes': [],
                'input_type': 'none',
                'status': 'success',
                'risk_level': 'low',
                'timestamp': report_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }

        paste_count = full_report.get('paste_count', 0)
        if paste_count == 0:
            email_pastes = len(email_report.get('pastes', [])) if email_report else 0
            username_pastes = len(username_report.get('pastes', []))
            paste_count = email_pastes + username_pastes
            app.logger.debug(f"Recalculated paste_count for report_id {report_id}: {paste_count} (email: {email_pastes}, username: {username_pastes})")

        current_results = {
            'query': {
                'email': full_report.get('query', {}).get('email', ''),
                'query': full_report.get('query', {}).get('query', '')
            },
            'combined_risk': full_report.get('combined_risk', 'unknown'),
            'email_report': {
                'total_breaches': email_report.get('total_breaches', 0),
                'breaches': email_report.get('breaches', []),
                'pastes': email_report.get('pastes', []),
                'intelx_results': email_report.get('intelx_results', []),
                'dehashed_results': email_report.get('dehashed_results', []),
                'leakcheck_results': email_report.get('leakcheck_results', []),
                'recommendations': fetch_recommendations(report_id, 'email') or []
            },
            'username_report': {
                'mentions': fetch_mentions(report_id) or [],
                'pastes': username_report.get('pastes', []),
                'recommendations': fetch_recommendations(report_id, 'username') or [],
                'input_type': username_report.get('input_type', 'none')
            },
            'timestamp': report_data.get('timestamp', ''),
            'report_id': report_id,
            'paste_count': paste_count
        }
        app.logger.debug(f"Rendering exposure report {report_id} with paste_count: {paste_count}")
        return render_template('report_detail.html',
                              title=f"Detalii Raport Expunere - Identity Guardian",
                              report=current_results)
    else:
        flash("Tip de raport necunoscut sau raportul aparține altui modul.", "danger")
        return redirect(url_for('dashboard'))
    
@app.route('/dashboard')
def dashboard():
    """Render a dashboard showing recent activity with pagination."""
    if not DATABASE_AVAILABLE:
        flash("Funcționalitatea bazei de date nu este disponibilă.", "danger")
        return redirect(url_for('index'))

    # Get pagination parameters
    exposure_page = request.args.get('exposure_page', 1, type=int)
    hygiene_page = request.args.get('hygiene_page', 1, type=int)
    
    # Ensure page numbers are valid
    exposure_page = max(1, exposure_page)
    hygiene_page = max(1, hygiene_page)
    
    # Items per page
    items_per_page = 3
    
    try:
        # Get ALL reports for proper pagination
        all_exposure_reports = get_reports_by_type('exposure', limit=100)  # Get more records
        all_hygiene_reports = get_reports_by_type('hygiene', limit=100)
        
        # Calculate pagination for exposure reports
        exposure_total = len(all_exposure_reports)
        exposure_total_pages = (exposure_total + items_per_page - 1) // items_per_page
        exposure_start = (exposure_page - 1) * items_per_page
        exposure_end = min(exposure_start + items_per_page, exposure_total)
        
        # Ensure page is within valid range
        if exposure_page > exposure_total_pages and exposure_total_pages > 0:
            exposure_page = exposure_total_pages
            exposure_start = (exposure_page - 1) * items_per_page
            exposure_end = min(exposure_start + items_per_page, exposure_total)
        
        # Get paginated exposure reports
        exposure_history = all_exposure_reports[exposure_start:exposure_end]
        
        # Calculate pagination for hygiene reports
        hygiene_total = len(all_hygiene_reports)
        hygiene_total_pages = (hygiene_total + items_per_page - 1) // items_per_page
        hygiene_start = (hygiene_page - 1) * items_per_page
        hygiene_end = min(hygiene_start + items_per_page, hygiene_total)
        
        # Ensure page is within valid range
        if hygiene_page > hygiene_total_pages and hygiene_total_pages > 0:
            hygiene_page = hygiene_total_pages
            hygiene_start = (hygiene_page - 1) * items_per_page
            hygiene_end = min(hygiene_start + items_per_page, hygiene_total)
        
        # Get paginated hygiene reports
        hygiene_history = all_hygiene_reports[hygiene_start:hygiene_end]
        
        app.logger.debug(f"Exposure pagination: page {exposure_page}/{exposure_total_pages}, showing items {exposure_start}-{exposure_end} of {exposure_total}")
        app.logger.debug(f"Hygiene pagination: page {hygiene_page}/{hygiene_total_pages}, showing items {hygiene_start}-{hygiene_end} of {hygiene_total}")
        
    except Exception as e:
        app.logger.error(f"Error fetching reports for dashboard: {e}", exc_info=True)
        flash("Eroare la încărcarea istoricului.", "danger")
        exposure_history = []
        hygiene_history = []
        exposure_total_pages = 0
        hygiene_total_pages = 0
        exposure_page = 1
        hygiene_page = 1

    return render_template('dashboard.html',
                          exposure_history=exposure_history,
                          hygiene_history=hygiene_history,
                          exposure_page=exposure_page,
                          exposure_total_pages=exposure_total_pages,
                          hygiene_page=hygiene_page,
                          hygiene_total_pages=hygiene_total_pages)


if __name__ == '__main__':
    print("\n=== Starting Identity Guardian Application ===")
    print(f"Debug mode: {config.DEBUG}")
    print(f"Host: {config.HOST}")
    print(f"Port: {config.PORT}")
    
    if not app.secret_key or app.secret_key == "default_secret_key_please_change":
        print("\n!!! ATENȚIE: Flask SECRET_KEY nu este setată sau este nesigură !!!\n")

    if not DATABASE_AVAILABLE:
        try:
            from utils.database import init_database
            print("Attempting to initialize database...")
            if init_database(): 
                DATABASE_AVAILABLE = True
                print("Database initialized successfully!")
            else:
                print("Failed to initialize database!")
        except Exception as e:
            print(f"Error during database initialization: {e}")

    if not DATABASE_AVAILABLE:
        print("\n!!! ATENȚIE: NU S-A PUTUT CONECTA/INIȚIALIZA BAZA DE DATE !!!")
        print("!!! Aplicația va rula FĂRĂ persistența datelor. !!!\n")

    print("\nStarting Flask server...")
    try:
        app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
    except Exception as e:
        print(f"\nError starting Flask server: {e}")
        import traceback
        traceback.print_exc()