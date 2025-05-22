#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - Exposure Monitor Module
This module handles the exposure monitoring functionality for checking if email addresses 
and usernames have been exposed in data breaches or leaked online.
"""

import re
import requests
import json
import logging
from datetime import datetime
import copy
# Import configuration settings
import config
from utils.api_clients import google_search  
# Import utilities
from utils.api_clients import hibp_api_request, search_pastebin, intelx_search, dehashed_search, leakcheck_search
from utils.regex_patterns import EMAIL_PATTERN, SENSITIVE_DATA_PATTERNS

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure logs are sent to the console
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


# Regex patterns for input detection
USERNAME_PATTERN = r'^[a-zA-Z0-9_]+$'
FULL_NAME_PATTERN = r'^[a-zA-Z\s]+$'

def check_email_exposure(email):
    """
    Check if an email has been exposed in known data breaches using HaveIBeenPwned API
    and search for it in Pastebin dumps using regex patterns. Additionally, query
    Intelligence X, DeHashed, and LeakCheck APIs for comprehensive exposure data.
    
    Args:
        email (str): The email address to check
        
    Returns:
        dict: Results of the exposure check containing breach data and leak matches
    """
    if not re.match(EMAIL_PATTERN, email):
        return {
            'status': 'error',
            'message': 'Invalid email format'
        }
    
    results = {
        'status': 'success',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'breaches': [],
        'pastes': [],
        'total_breaches': 0,
        'risk_level': 'low',
        'intelx_results': [],
        'dehashed_results': [],
        'leakcheck_results': []
    }
    
    # Check HaveIBeenPwned API for breaches
    try:
        breach_data = hibp_api_request(f"breachedaccount/{email}?includeUnverified=true")
        logger.debug(f"Raw HIBP breach data for {email}: {json.dumps(breach_data, indent=2)}")
        
        if breach_data is None:
            logger.warning(f"Failed to retrieve HIBP data for {email}")
        elif breach_data:
            results['breaches'] = [
                {
                    'name': breach.get('Name', ''),
                    'title': breach.get('Title', ''),
                    'domain': breach.get('Domain', ''),
                    'breach_date': breach.get('BreachDate', ''),
                    'added_date': breach.get('AddedDate', ''),
                    'modified_date': breach.get('ModifiedDate', ''),
                    'pwn_count': breach.get('PwnCount', 0),
                    'description': breach.get('Description', ''),
                    'logo_path': breach.get('LogoPath', ''),
                    'data_classes': breach.get('DataClasses', []),
                    'is_verified': breach.get('IsVerified', False),
                    'is_fabricated': breach.get('IsFabricated', False),
                    'is_sensitive': breach.get('IsSensitive', False),
                    'is_retired': breach.get('IsRetired', False),
                    'is_spam_list': breach.get('IsSpamList', False),
                    'is_malware': breach.get('IsMalware', False)
                } for breach in breach_data
            ]
            results['total_breaches'] = len(breach_data)
            
            for breach in breach_data:
                if not breach.get('Description'):
                    logger.warning(f"Missing description for breach {breach.get('Name')}")
                if not breach.get('DataClasses'):
                    logger.warning(f"Missing data classes for breach {breach.get('Name')}")
            
            if results['total_breaches'] > 5:
                results['risk_level'] = 'high'
            elif results['total_breaches'] > 2:
                results['risk_level'] = 'medium'
                
            for breach in breach_data:
                if any(category in ['Passwords', 'Credit Cards', 'Social Security Numbers', 'Banking'] 
                       for category in breach.get('DataClasses', [])):
                    results['risk_level'] = 'high'
                    break
        else:
            logger.info(f"No breaches found for {email} in HaveIBeenPwned")
    except Exception as e:
        logger.error(f"Error checking HaveIBeenPwned for {email}: {str(e)}")
    
    # Check Pastebin and other paste sites for the email
    try:
        paste_results = search_pastebin_for_email(email)
        results['pastes'] = paste_results
        
        if paste_results and results['risk_level'] != 'high':
            results['risk_level'] = 'medium'
    except Exception as e:
        logger.error(f"Error checking paste sites for {email}: {str(e)}")
    
    # Check Intelligence X for additional exposure
    try:
        intelx_results = intelx_search(email)
        if intelx_results:
            results['intelx_results'] = intelx_results
            if len(intelx_results) > 0 and results['risk_level'] != 'high':
                results['risk_level'] = 'medium'
    except Exception as e:
        logger.error(f"Error checking Intelligence X for {email}: {str(e)}")
    
    # Check DeHashed for leaked credentials
    try:
        dehashed_results = dehashed_search(email)
        logger.debug(f"Raw DeHashed results for {email}: {json.dumps(dehashed_results, indent=2)}")
        if dehashed_results:
            results['dehashed_results'] = dehashed_results
            if len(dehashed_results) > 0 and results['risk_level'] != 'high':
                results['risk_level'] = 'medium'
            results['total_breaches'] += len(dehashed_results)
    except Exception as e:
        logger.error(f"Error checking DeHashed for {email}: {str(e)}")
    
    # Check LeakCheck for exposure
    try:
        leakcheck_results = leakcheck_search(email)
        logger.debug(f"Raw LeakCheck results for {email}: {json.dumps(leakcheck_results, indent=2)}")
        if leakcheck_results:
            results['leakcheck_results'] = leakcheck_results
            if len(leakcheck_results) > 0 and results['risk_level'] != 'high':
                results['risk_level'] = 'medium'
            results['total_breaches'] += len(leakcheck_results)
    except Exception as e:
        logger.error(f"Error checking LeakCheck for {email}: {str(e)}")
    
    return results

def search_username_exposure(query):
    """
    Search for a query (username or full name) across various platforms and data sources to check exposure.
    
    Args:
        query (str): The username or full name to check
        
    Returns:
        dict: Results of the exposure check
    """
    if not query or len(query) < 3:
        return {
            'status': 'error',
            'message': 'Query too short or invalid'
        }
    
    # Determine input type
    is_full_name = bool(re.match(FULL_NAME_PATTERN, query))
    is_username = bool(re.match(USERNAME_PATTERN, query))
    input_type = 'full_name' if is_full_name else 'username' if is_username else 'unknown'
    logger.debug(f"Query '{query}' detected as {input_type}")

    results = {
        'status': 'success',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'found_on': [],
        'risk_level': 'low',
        'input_type': input_type
    }
    
    platforms = [
        'github.com', 'twitter.com', 'reddit.com', 'instagram.com', 
        'facebook.com', 'linkedin.com', 'youtube.com', 'pinterest.com'
    ]
    
    # Search across all platforms using Google Custom Search
    try:
        for platform in platforms:
            search_query = f"from:{platform} {query}"
            search_results = google_search(search_query, num_results=5)
            for item in search_results:
                url = item.get('link', '')
                if platform in url:
                    results['found_on'].append({
                        'platform': platform.split('.')[0],
                        'url': url,
                        'snippet': item.get('snippet', ''),
                        'confirmed': False,
                        'note': 'Potential match found, manual verification needed'
                    })
    except Exception as e:
        logger.error(f"Error searching platforms for {query}: {str(e)}")
        results['search_error'] = str(e)
    
    if len(results['found_on']) > 3:
        results['risk_level'] = 'medium'
    elif len(results['found_on']) > 0:
        results['risk_level'] = 'low'
    
    # Check Pastebin and similar sites
    try:
        paste_results = search_pastebin_for_username(query, is_full_name=is_full_name)
        if paste_results:
            results['pastes'] = paste_results
            if any(paste.get('contains_sensitive', False) for paste in paste_results):
                results['risk_level'] = 'high'
    except Exception as e:
        logger.error(f"Error checking paste sites for {query}: {str(e)}")
        results['pastebin_error'] = str(e)
    
    return results

def search_pastebin_for_email(email):
    """
    Search Pastebin and similar paste sites for a given email address.
    
    Args:
        email (str): The email address to search for
        
    Returns:
        list: List of paste matches with metadata
    """
    query = email
    results = search_pastebin(query, is_full_name=False)
    
    matches = []
    for result in results:
        matches.append({
            'source': result.get('source', 'pastebin'),
            'title': result.get('title', 'Untitled Paste'),
            'date': result.get('date', datetime.now().strftime('%Y-%m-%d')),
            'url': result.get('url'),
            'excerpt': result.get('snippet', ''),
            'contains_sensitive': 'password' in result.get('snippet', '').lower() or 
                                 'credentials' in result.get('snippet', '').lower() or
                                 'login' in result.get('snippet', '').lower()
        })
    
    return matches

def search_pastebin_for_username(username, is_full_name=False):
    """
    Search Pastebin and similar paste sites for a given username or full name.
    
    Args:
        username (str): The username or full name to search for
        is_full_name (bool): Flag to indicate if the query is a full name
        
    Returns:
        list: List of paste matches with metadata
    """
    results = search_pastebin(username, is_full_name=is_full_name)
    
    matches = []
    for result in results:
        matches.append({
            'source': result.get('source', 'pastebin'),
            'title': result.get('title', 'Untitled Paste'),
            'date': result.get('date', datetime.now().strftime('%Y-%m-%d')),
            'url': result.get('url'),
            'excerpt': result.get('snippet', ''),
            'contains_sensitive': username.lower() in result.get('snippet', '').lower() and 
                                 ('password' in result.get('snippet', '').lower() or
                                  'credentials' in result.get('snippet', '').lower() or
                                  'private' in result.get('snippet', '').lower())
        })
    
    return matches

def generate_exposure_report(email_results, username_results=None):
    """
    Generate a comprehensive report based on exposure check results.
    
    Args:
        email_results (dict): Results from email exposure check
        username_results (dict, optional): Results from username exposure check
        
    Returns:
        dict: Formatted report with findings and recommendations
    """
    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'overall_risk': email_results.get('risk_level', 'low'),
        'findings': [],
        'recommendations': []
    }
    
    if email_results.get('total_breaches', 0) > 0:
        report['findings'].append(f"Your email was found in {email_results['total_breaches']} data breaches.")
        
        for breach in email_results.get('breaches', []):
            report['findings'].append(
                f"Breach: {breach.get('name')} ({breach.get('breach_date', 'unknown date')}). "
                f"Types of data: {', '.join(breach.get('data_classes', ['Unknown']))}."
            )
        
        report['recommendations'].append("Change passwords for all accounts using this email address.")
        report['recommendations'].append("Enable two-factor authentication where possible.")
        
        if any('Password' in breach.get('data_classes', []) for breach in email_results.get('breaches', [])):
            report['recommendations'].append(
                "Use a password manager to create and store strong, unique passwords for each account."
            )
    else:
        report['findings'].append("Good news! Your email was not found in any known data breaches.")
    
    if username_results and username_results.get('found_on', []):
        platforms = [item['platform'] for item in username_results.get('found_on', [])]
        report['findings'].append(f"Your username was found on {len(platforms)} platforms: {', '.join(platforms)}.")
        
        report['recommendations'].append(
            "Consider using different usernames across platforms to reduce correlation of your accounts."
        )
    
    if email_results.get('pastes') or (username_results and username_results.get('pastes')):
        report['findings'].append("Your information was found in paste sites, which may indicate a data leak.")
        report['recommendations'].append("Monitor your accounts for suspicious activity.")
    
    if report['overall_risk'] in ['medium', 'high']:
        report['recommendations'].append("Consider using a different email for sensitive accounts.")
        report['recommendations'].append("Regularly check for new data breaches involving your information.")
    
    return report