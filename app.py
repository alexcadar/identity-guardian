#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - A Self-Defense Toolkit for Online Identity Protection
Main application file (app.py)
"""

from flask import Flask, render_template, request, flash, redirect, url_for, session

# Import configuration
import config

# Import modules for each main feature
from modules.exposure_monitor import check_email_exposure, search_username_exposure
from modules.digital_hygiene import process_hygiene_form, generate_hygiene_report
from modules.antidox_toolkit import get_removal_guides, generate_removal_request

# Import utility functions
from utils.api_clients import initialize_api_clients
from utils.llm_handler import initialize_llm

# Initialize Flask application
app = Flask(__name__)
app.secret_key = config.SECRET_KEY  # Used for flash messages and sessions

# Initialize external services when app starts
app = Flask(__name__)
app.secret_key = config.SECRET_KEY  # Used for flash messages and sessions

# Initialize external services at startup
with app.app_context():
    initialize_api_clients()
    initialize_llm()

# Route for home page
@app.route('/')
def index():
    """Render the home/landing page."""
    return render_template('index.html', title="Identity Guardian - Protect Your Online Identity")

# Routes for Exposure Monitor
@app.route('/exposure-monitor', methods=['GET', 'POST'])
def exposure_monitor():
    """Handle the exposure monitor page and form submission."""
    results = None
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        
        if email:
            # Check email exposure
            email_results = check_email_exposure(email)
            
            # Check username exposure if provided
            username_results = search_username_exposure(username) if username else None
            
            results = {
                'email': email,
                'username': username,
                'email_results': email_results,
                'username_results': username_results
            }
            
            # Store results in session for potential later use
            session['last_exposure_check'] = results
            
            # Flash a message to the user
            flash('Exposure check completed.', 'success')
        else:
            flash('Please enter an email address to check.', 'error')
    
    return render_template('exposure.html', 
                          title="Exposure Monitor - Identity Guardian",
                          results=results)

# Routes for Digital Hygiene Report
@app.route('/digital-hygiene', methods=['GET', 'POST'])
def digital_hygiene():
    """Handle the digital hygiene assessment page and form submission."""
    hygiene_report = None
    
    # Încarcă chestionarul din fișierul JSON
    from modules.digital_hygiene import load_questionnaire
    questionnaire = load_questionnaire()
    
    if request.method == 'POST':
        # Process the form submission from the hygiene questionnaire
        form_data = request.form.to_dict()
        
        # Process the questionnaire data
        from modules.digital_hygiene import process_hygiene_form, generate_hygiene_report
        processed_data = process_hygiene_form(form_data)
        
        # Generate the hygiene report using LLM
        hygiene_report = generate_hygiene_report(processed_data)
        
        # Store report in session for potential later use
        session['last_hygiene_report'] = hygiene_report
        
        flash('Raportul de igienă digitală a fost generat cu succes!', 'success')
    
    return render_template('hygiene.html', 
                          title="Evaluare de Igienă Digitală - Identity Guardian",
                          questionnaire=questionnaire,
                          hygiene_report=hygiene_report)

# Routes for Anti-Dox Toolkit
@app.route('/antidox-toolkit', methods=['GET', 'POST'])
def antidox_toolkit():
    """Handle the anti-dox toolkit page and form submission."""
    guides = None
    request_template = None
    
    if request.method == 'GET':
        # Get general removal guides
        guides = get_removal_guides()
    
    if request.method == 'POST':
        # Get data type and service to generate a removal request
        data_type = request.form.get('data_type')
        service = request.form.get('service')
        
        if data_type and service:
            # Generate a removal request template
            request_template = generate_removal_request(data_type, service)
            flash('Removal request template generated successfully.', 'success')
        else:
            flash('Please select both data type and service.', 'error')
    
    return render_template('antidox.html',
                          title="Anti-Dox Toolkit - Identity Guardian",
                          guides=guides,
                          request_template=request_template)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', 
                           error_code=404,
                           error_message="Page Not Found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    return render_template('error.html',
                           error_code=500, 
                           error_message="Internal Server Error"), 500

# Run the application
if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)