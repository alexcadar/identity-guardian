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
from dotenv import load_dotenv
import os
import base64

# Import configuration
import config

# Load environment variables from .env
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Global variables to store API configurations
api_configs = {
    'hibp': {
        'initialized': False,
        'base_url': 'https://haveibeenpwned.com/api/v3/',
        'api_key': None,
        'rate_limit': 1.5,
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
    },
    'intelx': {
        'initialized': False,
        'base_url': 'https://free.intelx.io/',  # Primary endpoint for free tier
        'api_key': os.getenv('INTELLX', ''),
        'rate_limit': 2.0,
        'max_poll_attempts': 5,  # Max attempts to poll for results
        'poll_interval': 2.0  # Seconds between polling attempts
    },
    'dehashed': {
        'initialized': False,
        'base_url': 'https://api.dehashed.com/search',
        'api_key': os.getenv('DEHASHED', ''),
        'email': os.getenv('DEHASHED_EMAIL', ''),
        'rate_limit': 1.0
    },
    'leakcheck': {
        'initialized': False,
        'base_url': 'https://leakcheck.net/api/v2',
        'public_base_url': 'https://leakcheck.io/api/public',
        'api_key': os.getenv('LEAK_CHECK', ''),
        'rate_limit': 1.5
    }
}

def initialize_api_clients():
    """
    Initialize all API clients with configuration from config file and .env.
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
    
    # Initialize Intelligence X API
    if api_configs['intelx']['api_key']:
        api_configs['intelx']['initialized'] = True
        logger.info("Intelligence X API client initialized with endpoint: %s", api_configs['intelx']['base_url'])
    else:
        logger.warning("Intelligence X API key not found in .env. Using free API with limited functionality.")
    
    # Initialize DeHashed API
    if api_configs['dehashed']['api_key'] and api_configs['dehashed']['email']:
        api_configs['dehashed']['initialized'] = True
        logger.info("DeHashed API client initialized")
    else:
        logger.warning("DeHashed API key or email not found in .env. DeHashed features will be limited.")
    
    # Initialize LeakCheck API
    if api_configs['leakcheck']['api_key']:
        api_configs['leakcheck']['initialized'] = True
        logger.info("LeakCheck API client initialized")
    else:
        logger.warning("LeakCheck API key not found in .env. Falling back to public API for LeakCheck.")

def hibp_api_request(endpoint, api_key=None):
    """
    Make a request to the HaveIBeenPwned API.
    
    Args:
        endpoint (str): The API endpoint to query
        api_key (str, optional): API key override
    
    Returns:
        dict/list: The JSON response from the API or None if error
    """
    key = api_key or api_configs['hibp']['api_key']
    
    if not key:
        logger.error("No HaveIBeenPwned API key available for request")
        return None
    
    current_time = time.time()
    time_since_last_request = current_time - api_configs['hibp']['last_request_time']
    
    if time_since_last_request < api_configs['hibp']['rate_limit']:
        wait_time = api_configs['hibp']['rate_limit'] - time_since_last_request
        logger.debug(f"Waiting {wait_time:.2f}s for HIBP rate limit")
        time.sleep(wait_time)
    
    api_configs['hibp']['last_request_time'] = time.time()
    
    url = f"{api_configs['hibp']['base_url']}{endpoint}"
    headers = {
        'hibp-api-key': key,
        'User-Agent': 'IdentityGuardian/1.0 (contact: support@identityguardian.local)',
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return []
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', api_configs['hibp']['rate_limit']))
                logger.warning(f"HaveIBeenPwned rate limit exceeded. Waiting {retry_after}s as per Retry-After header")
                time.sleep(retry_after)
                continue
            elif response.status_code == 503:
                wait_time = (2 ** attempt)
                logger.warning(f"HaveIBeenPwned service unavailable (503). Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for HIBP 503 error")
                    return None
                time.sleep(wait_time)
                continue
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
    
    logger.error("Max retries reached for HIBP request")
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
        'num': min(num_results, 10)
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
    dork_query = f"site:pastebin.com {query}"
    
    try:
        results = google_search(dork_query)
        formatted_results = []
        for item in results:
            url = item.get('link')
            if url and 'pastebin.com' in url:
                formatted_results.append({
                    'title': item.get('title', 'Untitled Paste'),
                    'url': url,
                    'snippet': item.get('snippet', ''),
                    'source': 'pastebin',
                    'date': datetime.datetime.now().strftime('%Y-%m-%d')
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
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9,
        }
    }
    params = {"key": api_configs['gemini']['api_key']}
    
    try:
        response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if (result and 'candidates' in result and len(result['candidates']) > 0 and
                'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content'] and
                len(result['candidates'][0]['content']['parts']) > 0):
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

def intelx_search(query):
    """
    Search Intelligence X for exposure data related to a query (e.g., email).
    
    Args:
        query (str): The search term (e.g., email address)
    
    Returns:
        list: Search results or empty list if error
    """
    if not api_configs['intelx']['initialized']:
        logger.warning("Intelligence X API not initialized. Cannot perform search.")
        return []
    
    base_url = api_configs['intelx']['base_url']
    search_url = f"{base_url}intelligent/search"
    headers = {
        'x-key': api_configs['intelx']['api_key'],
        'User-Agent': 'IdentityGuardian/1.0 (contact: support@identityguardian.local)',
        'Content-Type': 'application/json'
    }
    payload = {
        'term': query,
        'maxresults': 10,
        'media': 0,  # All media types
        'sort': 2,   # Sort by date (2 is commonly used per API docs)
        'timeout': 20,  # API-side timeout in seconds
        'lookuplevel': 0  # Basic lookup level for free tier
    }
    
    try:
        # Rate limiting for search submission
        current_time = time.time()
        time_since_last_request = current_time - api_configs['intelx'].get('last_request_time', 0)
        if time_since_last_request < api_configs['intelx']['rate_limit']:
            wait_time = api_configs['intelx']['rate_limit'] - time_since_last_request
            logger.debug(f"Waiting {wait_time:.2f}s for Intelligence X rate limit")
            time.sleep(wait_time)
        
        api_configs['intelx']['last_request_time'] = time.time()
        logger.debug(f"Submitting Intelligence X POST request to {search_url} with query: {query}")
        
        # Submit search query
        response = requests.post(search_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Intelligence X search submission response: {json.dumps(data, indent=2)}")
            if 'id' in data and data.get('status') in [0, 'pending', 'success']:
                search_id = data['id']
                logger.info(f"Intelligence X search submitted successfully. ID: {search_id}")
                
                # Poll for results
                results_url = f"{base_url}intelligent/search/result?id={search_id}"
                result_headers = {
                    'x-key': api_configs['intelx']['api_key'],
                    'User-Agent': 'IdentityGuardian/1.0 (contact: support@identityguardian.local)'
                }
                
                for attempt in range(api_configs['intelx']['max_poll_attempts']):
                    time.sleep(api_configs['intelx']['poll_interval'])
                    logger.debug(f"Polling Intelligence X results for search ID {search_id}, attempt {attempt + 1}")
                    
                    result_response = requests.get(results_url, headers=result_headers, timeout=10)
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        logger.debug(f"Intelligence X results response: {json.dumps(result_data, indent=2)}")
                        
                        if result_data.get('status') == 0 and 'records' in result_data:
                            return [{
                                'source': 'intelx',
                                'title': record.get('name', 'Untitled Result'),
                                'date': record.get('date', record.get('added', datetime.datetime.now().strftime('%Y-%m-%d'))),
                                'url': record.get('storageid', ''),  # Use storageid as URL placeholder
                                'excerpt': record.get('preview', {}).get('data', record.get('content', '')),
                                'category': record.get('media_type_name', record.get('type', 'unknown'))
                            } for record in result_data.get('records', [])]
                        elif result_data.get('status') == 2:
                            logger.info(f"Intelligence X: No results found for search ID '{search_id}' (status 2)")
                            return []
                        else:
                            logger.debug(f"Intelligence X: Search ID {search_id} not ready, status: {result_data.get('status')}")
                            continue
                    else:
                        logger.error(f"Intelligence X results retrieval error {result_response.status_code}: {result_response.text}")
                        return []
                
                logger.warning(f"Intelligence X: Max polling attempts reached for search ID {search_id}")
                return []
            else:
                logger.error(f"Intelligence X search submission failed: {data.get('status')}")
                return []
        elif response.status_code == 401:
            logger.error(f"Intelligence X API error 401 (Unauthorized) at {search_url}. Check API key.")
            return []
        elif response.status_code == 402:
            logger.error(f"Intelligence X API error 402 (Quota Exceeded) at {search_url}.")
            return []
        else:
            logger.error(f"Intelligence X API error {response.status_code} at {search_url}: {response.text}")
            return []
    
    except Timeout:
        logger.error(f"Intelligence X API request to {search_url} timed out")
        return []
    except RequestException as e:
        logger.error(f"Intelligence X API request to {search_url} failed: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error with Intelligence X API at {search_url}: {str(e)}")
        return []

def dehashed_search(query):
    """
    Search DeHashed for leaked credentials related to a query (e.g., email).
    
    Args:
        query (str): The search term (e.g., email address)
    
    Returns:
        list: Search results or empty list if error
    """
    if not api_configs['dehashed']['initialized']:
        logger.warning("DeHashed API not initialized. Cannot perform search.")
        return []
    
    auth_string = f"{api_configs['dehashed']['email']}:{api_configs['dehashed']['api_key']}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_auth}',
        'Accept': 'application/json'
    }
    params = {
        'query': query,
        'size': 10
    }
    url = api_configs['dehashed']['base_url']
    
    try:
        current_time = time.time()
        time_since_last_request = current_time - api_configs['dehashed'].get('last_request_time', 0)
        if time_since_last_request < api_configs['dehashed']['rate_limit']:
            wait_time = api_configs['dehashed']['rate_limit'] - time_since_last_request
            logger.debug(f"Waiting {wait_time:.2f}s for DeHashed rate limit")
            time.sleep(wait_time)
        
        api_configs['dehashed']['last_request_time'] = time.time()
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('entries'):
                return [{
                    'source': 'dehashed',
                    'email': entry.get('email', ''),
                    'username': entry.get('username', ''),
                    'password': entry.get('password', ''),
                    'hashed_password': entry.get('hashed_password', ''),
                    'name': entry.get('name', ''),
                    'dob': entry.get('dob', ''),
                    'address': entry.get('address', ''),
                    'phone': entry.get('phone', ''),
                    'company': entry.get('company', ''),
                    'url': entry.get('url', ''),
                    'social': entry.get('social', ''),
                    'cryptocurrency_address': entry.get('cryptocurrency_address', ''),
                    'database_name': entry.get('database_name', ''),
                    'source_site': entry.get('source', 'unknown'),
                    'date': datetime.datetime.now().strftime('%Y-%m-%d')
                } for entry in data['entries']]
            return []
        else:
            logger.error(f"DeHashed API error {response.status_code}: {response.text}")
            return []
    
    except Timeout:
        logger.error("DeHashed API request timed out")
        return []
    except RequestException as e:
        logger.error(f"DeHashed API request failed: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error with DeHashed API: {str(e)}")
        return []

def leakcheck_search(query):
    """
    Search LeakCheck API for exposure data related to a query (e.g., email or username).
    Attempts authenticated API first, falls back to public API if key is missing or authenticated request fails.
    
    Args:
        query (str): The search term (e.g., email address or username)
    
    Returns:
        list: Formatted search results or empty list if error or no results
    """
    if api_configs['leakcheck']['initialized'] and api_configs['leakcheck']['api_key']:
        logger.debug("Attempting LeakCheck authenticated API request")
        url = api_configs['leakcheck']['base_url']
        headers = {
            'X-API-Key': api_configs['leakcheck']['api_key'],
            'User-Agent': 'IdentityGuardian/1.0 (contact: support@identityguardian.local)'
        }
        params = {'type': 'auto', 'query': query}

        try:
            current_time = time.time()
            time_since_last_request = current_time - api_configs['leakcheck'].get('last_request_time', 0)
            if time_since_last_request < api_configs['leakcheck']['rate_limit']:
                wait_time = api_configs['leakcheck']['rate_limit'] - time_since_last_request
                logger.debug(f"Waiting {wait_time:.2f}s for LeakCheck rate limit")
                time.sleep(wait_time)
            
            api_configs['leakcheck']['last_request_time'] = time.time()
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"LeakCheck authenticated API response: {json.dumps(data, indent=2)}")
                if data.get('success') and data.get('found', 0) > 0 and 'result' in data:
                    return [{
                        'source': 'leakcheck',
                        'name': item.get('name', 'N/A'),
                        'date': item.get('last_breach', 'N/A'),
                        'data_classes': item.get('fields', []),
                        'source_url': None
                    } for item in data['result']]
                logger.info(f"LeakCheck authenticated API: No breaches found for query '{query}'")
                return []
            else:
                logger.error(f"LeakCheck authenticated API error {response.status_code}: {response.text}")
                logger.info("Falling back to LeakCheck public API")
        
        except Timeout:
            logger.error("LeakCheck authenticated API request timed out")
            logger.info("Falling back to LeakCheck public API")
        except RequestException as e:
            logger.error(f"LeakCheck authenticated API request failed: {str(e)}")
            logger.info("Falling back to LeakCheck public API")
        except Exception as e:
            logger.error(f"Unexpected error with LeakCheck authenticated API: {str(e)}")
            logger.info("Falling back to LeakCheck public API")
    
    logger.debug("Using LeakCheck public API")
    url = api_configs['leakcheck']['public_base_url']
    params = {'check': query}
    headers = {
        'User-Agent': 'IdentityGuardian/1.0 (contact: support@identityguardian.local)'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"LeakCheck public API response: {json.dumps(data, indent=2)}")
            if data.get('success') and data.get('found', 0) > 0 and 'sources' in data:
                return [{
                    'source': 'leakcheck_public',
                    'name': item.get('name', 'N/A'),
                    'date': item.get('date', 'N/A'),
                    'data_classes': data.get('fields', []),
                    'source_url': None
                } for item in data['sources']]
            logger.info(f"LeakCheck public API: No breaches found for query '{query}'")
            return []
        else:
            logger.error(f"LeakCheck public API error {response.status_code}: {response.text}")
            return []
    
    except Timeout:
        logger.error("LeakCheck public API request timed out")
        return []
    except RequestException as e:
        logger.error(f"LeakCheck public API request failed: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error with LeakCheck public API: {str(e)}")
        return []