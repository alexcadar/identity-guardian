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

# Import utilities
from utils.api_clients import hibp_api_request
from utils.regex_patterns import EMAIL_PATTERN, SENSITIVE_DATA_PATTERNS

# Set up logging
logger = logging.getLogger(__name__)

def validate_url(url, timeout=3):
    """
    Check if a URL is valid and accessible.
    
    Args:
        url (str): The URL to check
        timeout (int): Timeout in seconds
        
    Returns:
        bool: True if URL is valid and accessible, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    try:
        # Adaugă User-Agent pentru a evita blocarea
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        
        # Pentru unele site-uri, HEAD nu este acceptat, încearcă GET dacă HEAD eșuează
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, stream=True, headers=headers)
            # Citim doar primii câțiva bytes pentru a verifica disponibilitatea
            if response.raw:
                response.raw.read(1024)
                response.close()
                
        return response.status_code < 400
    except Exception as e:
        logger.debug(f"URL validation failed for {url}: {str(e)}")
        return False
    
def check_email_exposure(email):
    """
    Check if an email has been exposed in known data breaches using HaveIBeenPwned API
    and search for it in Pastebin dumps using regex patterns.
    
    Args:
        email (str): The email address to check
        
    Returns:
        dict: Results of the exposure check containing breach data and paste matches
    """
    if not re.match(EMAIL_PATTERN, email):
        return {
            'status': 'error',
            'message': 'Invalid email format'
        }
    
    results = {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'breaches': [],
        'pastes': [],
        'total_breaches': 0,
        'risk_level': 'low'
    }
    
    # Check HaveIBeenPwned API for breaches
    try:
        # Using API key that's been generated for HaveIBeenPwned
        breach_data = hibp_api_request(f"breachedaccount/{email}", api_key=config.HIBP_API_KEY)
        
        if breach_data:
            results['breaches'] = breach_data
            results['total_breaches'] = len(breach_data)
            
            # Assess risk level based on number and sensitivity of breaches
            if results['total_breaches'] > 5:
                results['risk_level'] = 'high'
            elif results['total_breaches'] > 2:
                results['risk_level'] = 'medium'
                
            # Check for sensitive breaches
            for breach in breach_data:
                if any(category in ['Passwords', 'Credit Cards', 'Social Security Numbers', 'Banking'] 
                       for category in breach.get('DataClasses', [])):
                    results['risk_level'] = 'high'
                    break
    except Exception as e:
        logger.error(f"Error checking HaveIBeenPwned: {str(e)}")
        results['hibp_error'] = str(e)
    
    # Check Pastebin for the email using regex patterns
    try:
        paste_results = search_pastebin_for_email(email)
        results['pastes'] = paste_results
        
        # Update risk level if pastes were found
        if paste_results and results['risk_level'] != 'high':
            results['risk_level'] = 'medium'
    except Exception as e:
        logger.error(f"Error checking Pastebin: {str(e)}")
        results['pastebin_error'] = str(e)
    
    # Important: Validează rezultatele înainte de a le returna
    if results:
        logger.info(f"Validating search results for email {email}")
        results = validate_search_results(results, email)
    
    return results

def search_username_exposure(username):
    """
    Search for a username across various platforms and data sources to check exposure.
    
    Args:
        username (str): The username to check
        
    Returns:
        dict: Results of the username exposure check
    """
    if not username or len(username) < 3:
        return {
            'status': 'error',
            'message': 'Username too short or invalid'
        }
    
    results = {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'found_on': [],
        'risk_level': 'low'
    }
    
    # This would normally search across multiple platforms
    # For now, we're implementing a simpler version that checks a few common sites
    
    # List of common platforms to check
    platforms = [
        'github', 'twitter', 'reddit', 'instagram', 
        'facebook', 'linkedin', 'youtube', 'pinterest'
    ]
    
    for platform in platforms:
        # In a real implementation, we would check each platform's API or use web scraping
        # For now, just simulate the check with random results for demonstration
        # This should be replaced with actual API calls or proper OSINT techniques
        if len(username) > 5 and platform in ['github', 'twitter', 'reddit']:
            url = f"https://{platform}.com/{username}"
            if validate_url(url):
                results['found_on'].append({
                    'platform': platform,
                    'url': url,
                    'confirmed': False,  # Would be True if verified through API
                    'note': 'Potential match found, manual verification needed'
                })
    
    # Update risk level based on findings
    if len(results['found_on']) > 3:
        results['risk_level'] = 'medium'
    
    # Search Pastebin for the username
    try:
        paste_results = search_pastebin_for_username(username)
        if paste_results:
            results['pastes'] = paste_results
            # Update risk level if sensitive pastes were found
            if any(paste.get('contains_sensitive', False) for paste in paste_results):
                results['risk_level'] = 'high'
    except Exception as e:
        logger.error(f"Error checking Pastebin for username: {str(e)}")
        results['pastebin_error'] = str(e)
    
    # Important: Validează rezultatele înainte de a le returna
    if results:
        logger.info(f"Validating search results for username {username}")
        results = validate_search_results({'username_results': results}, username)['username_results']
    
    return results

def search_pastebin_for_email(email):
    """
    Search Pastebin and similar paste sites for a given email address.
    
    Args:
        email (str): The email address to search for
        
    Returns:
        list: List of paste matches with metadata
    """
    # Folosește Google Search pentru a căuta conținut real pe Pastebin
    from utils.api_clients import search_pastebin
    
    # Caută email-ul pe Pastebin
    query = email.replace('@', ' ')  # Separă username și domeniul pentru căutare mai bună
    results = search_pastebin(query)
    
    # Procesează rezultatele
    matches = []
    for result in results:
        if validate_url(result.get('url')):
            # Adaugă doar URL-uri validate
            matches.append({
                'source': 'pastebin',
                'title': result.get('title', 'Untitled Paste'),
                'date': result.get('date', datetime.now().strftime('%Y-%m-%d')),
                'url': result.get('url'),
                'excerpt': result.get('snippet', ''),
                'contains_sensitive': 'password' in result.get('snippet', '').lower() or 
                                     'credentials' in result.get('snippet', '').lower() or
                                     'login' in result.get('snippet', '').lower()
            })
    
    return matches

def search_pastebin_for_username(username):
    """
    Search Pastebin and similar paste sites for a given username.
    
    Args:
        username (str): The username to search for
        
    Returns:
        list: List of paste matches with metadata
    """
    # Folosește Google Search pentru a căuta conținut real pe Pastebin
    from utils.api_clients import search_pastebin
    
    # Caută username-ul pe Pastebin
    results = search_pastebin(username)
    
    # Procesează rezultatele
    matches = []
    for result in results:
        if validate_url(result.get('url')):
            # Adaugă doar URL-uri validate
            matches.append({
                'source': 'pastebin',
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


def validate_search_results(results, search_term):
    """
    Validate all URLs in search results and ensure they contain the search term.
    Remove any invalid or irrelevant results.
    
    Args:
        results (dict): Search results dictionary containing URLs to validate
        search_term (str): The original search term to check for relevance
        
    Returns:
        dict: Filtered results with only valid URLs
    """
    if not results:
        return results
    
    # Create a copy to avoid modifying the original during iteration
    validated_results = copy.deepcopy(results)
    
    # Validate email results
    if 'email_results' in validated_results:
        email_results = validated_results['email_results']
        
        # Validate pastes in email results
        if email_results and 'pastes' in email_results and email_results['pastes']:
            valid_pastes = []
            for paste in email_results['pastes']:
                if 'url' in paste and validate_url(paste['url']):
                    valid_pastes.append(paste)
                else:
                    logger.info(f"Removing invalid paste URL: {paste.get('url')}")
            email_results['pastes'] = valid_pastes
    
    # Validate username results
    if 'username_results' in validated_results:
        username_results = validated_results['username_results']
        
        if username_results:
            # Validate found_on URLs in username results
            if 'found_on' in username_results and username_results['found_on']:
                valid_found_on = []
                for item in username_results['found_on']:
                    if 'url' in item and validate_url(item['url']):
                        valid_found_on.append(item)
                    else:
                        logger.info(f"Removing invalid platform URL: {item.get('url')}")
                username_results['found_on'] = valid_found_on
            
            # Validate pastes in username results
            if 'pastes' in username_results and username_results['pastes']:
                valid_pastes = []
                for paste in username_results['pastes']:
                    if 'url' in paste and validate_url(paste['url']):
                        valid_pastes.append(paste)
                    else:
                        logger.info(f"Removing invalid paste URL: {paste.get('url')}")
                username_results['pastes'] = valid_pastes
    
    return validated_results


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
        'generated_at': datetime.now().isoformat(),
        'overall_risk': email_results.get('risk_level', 'low'),
        'findings': [],
        'recommendations': []
    }
    
    # Process email breach findings
    if email_results.get('total_breaches', 0) > 0:
        report['findings'].append(f"Your email was found in {email_results['total_breaches']} data breaches.")
        
        # Add specific breach details
        for breach in email_results.get('breaches', []):
            report['findings'].append(
                f"Breach: {breach.get('Name')} ({breach.get('BreachDate', 'unknown date')}). "
                f"Types of data: {', '.join(breach.get('DataClasses', ['Unknown']))}."
            )
        
        # Add recommendations based on breaches
        report['recommendations'].append("Change passwords for all accounts using this email address.")
        report['recommendations'].append("Enable two-factor authentication where possible.")
        
        if any('Password' in breach.get('DataClasses', []) for breach in email_results.get('breaches', [])):
            report['recommendations'].append(
                "Use a password manager to create and store strong, unique passwords for each account."
            )
    else:
        report['findings'].append("Good news! Your email was not found in any known data breaches.")
    
    # Process username findings if available
    if username_results and username_results.get('found_on', []):
        platforms = [item['platform'] for item in username_results.get('found_on', [])]
        report['findings'].append(f"Your username was found on {len(platforms)} platforms: {', '.join(platforms)}.")
        
        report['recommendations'].append(
            "Consider using different usernames across platforms to reduce correlation of your accounts."
        )
    
    # Process paste findings
    if email_results.get('pastes') or (username_results and username_results.get('pastes')):
        report['findings'].append("Your information was found in paste sites, which may indicate a data leak.")
        report['recommendations'].append("Monitor your accounts for suspicious activity.")
    
    # Overall recommendations
    if report['overall_risk'] in ['medium', 'high']:
        report['recommendations'].append("Consider using a different email for sensitive accounts.")
        report['recommendations'].append("Regularly check for new data breaches involving your information.")
    
    return report