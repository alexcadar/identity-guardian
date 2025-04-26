#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - Configuration File
This file contains all configuration settings for the application.

IMPORTANT: In a production environment, sensitive information like API keys
should be stored in environment variables or a secure vault, not in source code.
"""

import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv() 

# Flask application settings
DEBUG = True  # Set to False in production
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000  # Default Flask port
SECRET_KEY = secrets.token_hex(16)  # Generate a random secret key for sessions
SESSION_LIFETIME = timedelta(hours=1)  # Session expiration time

# API Keys - Replace with your actual API keys or use environment variables
# To use environment variables, uncomment the lines below and set the values in your environment

# HaveIBeenPwned API
# Get key from: https://haveibeenpwned.com/API/Key
HIBP_API_KEY = os.environ.get('HIBP_API_KEY', '')  # Replace with your actual API key

# Google Custom Search API 
# Get API key from: https://developers.google.com/custom-search/v1/overview
# Create search engine at: https://programmablesearchengine.google.com/
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
GOOGLE_CSE_ID = os.environ.get('GOOGLE_CSE_ID', '')  # Custom Search Engine ID

# Gemini API (for LLM functionality)
# Get API key from: https://ai.google.dev/
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Logging configuration
LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = 'identity_guardian.log'

# Feature flags - Enable/disable specific features
ENABLE_EMAIL_MONITORING = True
ENABLE_USERNAME_MONITORING = True
ENABLE_PASTEBIN_SEARCH = True
ENABLE_LLM_REPORTS = True

# Digital Hygiene Report configuration
HYGIENE_CATEGORIES = [
    'account_security',
    'data_sharing',
    'device_security',
    'social_media',
    'browsing_habits'
]

# Exposure Monitor configuration
MAX_SAVED_REPORTS = 5  # Maximum number of reports to save in session history

# Anti-Dox Toolkit configuration
SUPPORTED_DATA_TYPES = [
    'full_name',
    'home_address',
    'phone_number',
    'email_address',
    'social_media_profiles',
    'photos',
    'government_id',
    'financial_information'
]

SUPPORTED_PLATFORMS = [
    'google',
    'facebook',
    'twitter',
    'instagram',
    'linkedin',
    'reddit',
    'data_brokers',
    'people_search_sites'
]

# Advanced settings
REQUEST_TIMEOUT = 10  # Timeout for external API requests in seconds
CACHE_DURATION = 3600  # Cache duration in seconds (1 hour)