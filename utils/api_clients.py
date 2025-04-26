#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Identity Guardian - API Clients Module
This module handles all API interactions with external services.
"""

import requests
import json
import logging
import time
import datetime
from requests.exceptions import RequestException, Timeout

# Import configuration
import config

# Set up logging
logger = logging.getLogger(__name__)

# Global variables to store API configurations
api_configs = {
    'hibp': {
        'initialized': False,
        'base_url': 'https://haveibeenpwned.com/api/v3/',
        'api_key': None,
        'rate_limit': 1.5,  # HaveIBeenPwned rate limit is 1 request per 1.5 seconds
        'last_request_time': 0
    },
    'google_search': {
        'initialized': False,
        'base_url': 'https://www.googleapis.com/customsearch/v1',
        'api_key': None,
        'search_engine_id': None
    },
    'gemini': {
        'initialized': False,
        'api_key': None
    }
}

def initialize_api_clients():
    """
    Initialize all API clients with configuration from config file.
    This should be called during application startup.
    """
    # Initialize HaveIBeenPwned API
    if hasattr(config, 'HIBP_API_KEY') and config.HIBP_API_KEY:
        api_configs['hibp']['api_key'] = config.HIBP_API_KEY
        api_configs['hibp']['initialized'] = True
        logger.info("HaveIBeenPwned API client initialized")
    else:
        logger.warning("HaveIBeenPwned API key not found in config. HIBP features will be limited.")
    
    # Initialize Google Custom Search API
    if hasattr(config, 'GOOGLE_API_KEY') and hasattr(config, 'GOOGLE_CSE_ID'):
        api_configs['google_search']['api_key'] = config.GOOGLE_API_KEY
        api_configs['google_search']['search_engine_id'] = config.GOOGLE_CSE_ID
        api_configs['google_search']['initialized'] = True
        logger.info("Google Custom Search API client initialized")
    else:
        logger.warning("Google Search API configuration not found. Search features will be limited.")
    
    # Initialize Gemini API
    if hasattr(config, 'GEMINI_API_KEY'):
        api_configs['gemini']['api_key'] = config.GEMINI_API_KEY
        api_configs['gemini']['initialized'] = True
        logger.info("Gemini API client initialized")
    else:
        logger.warning("Gemini API key not found in config. LLM features will be limited.")

def hibp_api_request(endpoint, api_key=None):
    """
    Make a request to the HaveIBeenPwned API.
    
    Args:
        endpoint (str): The API endpoint to query
        api_key (str, optional): API key override
    
    Returns:
        dict/list: The JSON response from the API or None if error
    """
    # Use provided API key or the one from config
    key = api_key or api_configs['hibp']['api_key']
    
    if not key:
        logger.error("No HaveIBeenPwned API key available for request")
        return None
    
    # Respect rate limiting
    current_time = time.time()
    time_since_last_request = current_time - api_configs['hibp']['last_request_time']
    
    if time_since_last_request < api_configs['hibp']['rate_limit']:
        wait_time = api_configs['hibp']['rate_limit'] - time_since_last_request
        logger.debug(f"Waiting {wait_time:.2f}s for HIBP rate limit")
        time.sleep(wait_time)
    
    # Update last request time
    api_configs['hibp']['last_request_time'] = time.time()
    
    # Prepare the request
    url = f"{api_configs['hibp']['base_url']}{endpoint}"
    headers = {
        'hibp-api-key': key,
        'User-Agent': 'IdentityGuardian-MonitoringTool',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Handle the common responses
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # 404 for HIBP usually means no breaches found, which is not an error
            return []
        elif response.status_code == 429:
            logger.warning("HaveIBeenPwned rate limit exceeded")
            # Wait and retry once
            time.sleep(api_configs['hibp']['rate_limit'] * 2)
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else []
        else:
            logger.error(f"HaveIBeenPwned API error {response.status_code}: {response.text}")
            return None
    
    except Timeout:
        logger.error("HaveIBeenPwned API request timed out")
        return None
    except RequestException as e:
        logger.error(f"HaveIBeenPwned API request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with HaveIBeenPwned API: {str(e)}")
        return None

def google_search(query, num_results=10):
    """
    Perform a Google search using the Custom Search API.
    
    Args:
        query (str): The search query
        num_results (int): Number of results to return (max 10 per request)
    
    Returns:
        list: Search results or empty list if error
    """
    if not api_configs['google_search']['initialized']:
        logger.warning("Google Search API not initialized. Cannot perform search.")
        return []
    
    params = {
        'key': api_configs['google_search']['api_key'],
        'cx': api_configs['google_search']['search_engine_id'],
        'q': query,
        'num': min(num_results, 10)  # Max 10 results per request
    }
    
    try:
        response = requests.get(
            api_configs['google_search']['base_url'], 
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data:
                return data['items']
            return []
        else:
            logger.error(f"Google Search API error {response.status_code}: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error with Google Search API: {str(e)}")
        return []

def search_pastebin(query):
    """
    Search for content on Pastebin related to a query.
    
    Args:
        query (str): The search term
    
    Returns:
        list: Search results or empty list if error
    """
    # Create a Google dork to search Pastebin
    dork_query = f"site:pastebin.com {query}"
    
    try:
        # Use our Google search function
        results = google_search(dork_query)
        
        # Format the results and validate URLs
        formatted_results = []
        for item in results:
            url = item.get('link')
            
            # Verifică doar că URL-ul are formatul corect pentru Pastebin
            # Validarea completă se va face în validate_search_results
            if url and 'pastebin.com' in url:
                formatted_results.append({
                    'title': item.get('title', 'Untitled Paste'),
                    'url': url,
                    'snippet': item.get('snippet', ''),
                    'source': 'pastebin',
                    'date': datetime.now().strftime('%Y-%m-%d')  # Data curentă ca placeholder
                })
        
        return formatted_results
    
    except Exception as e:
        logger.error(f"Error searching Pastebin: {str(e)}")
        return []

def gemini_request(prompt, max_tokens=1024):
    """
    Send a request to the Gemini API for generative AI processing.
    
    Args:
        prompt (str): The text prompt to send to Gemini
        max_tokens (int): Maximum number of tokens to generate
    
    Returns:
        str: The generated text response or None if error
    """
    if not api_configs['gemini']['initialized']:
        logger.warning("Gemini API not initialized. Cannot generate response.")
        return None
    
    # Simple implementation for Gemini API - customize based on actual API requirements
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9,
        }
    }
    
    params = {
        "key": api_configs['gemini']['api_key']
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Extract the generated text - adjust this based on actual API response structure
            if (result 
                and 'candidates' in result 
                and len(result['candidates']) > 0 
                and 'content' in result['candidates'][0]
                and 'parts' in result['candidates'][0]['content']
                and len(result['candidates'][0]['content']['parts']) > 0):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                logger.error(f"Unexpected Gemini API response structure: {result}")
                return None
        else:
            logger.error(f"Gemini API error {response.status_code}: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error with Gemini API: {str(e)}")
        return None