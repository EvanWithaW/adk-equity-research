"""
SEC Filings Research Module

This module provides functions for retrieving and analyzing SEC filings data.
It includes functions for:
1. Looking up CIK numbers for companies
2. Retrieving company information from the SEC
3. Fetching and parsing SEC filings
4. Analyzing filing contents

The module uses the SEC's EDGAR database to access public company filings.
"""

import requests
from bs4 import BeautifulSoup
import re
import os
import json
from typing import List, Dict, Any, Optional

# Import the existing find_cik function
from filingsResearch.get_company_cik import find_cik

def get_company_info(cik: str) -> Dict[str, Any]:
    """
    Get detailed information about a company using its CIK number.

    Args:
        cik (str): The company's CIK number (with or without leading zeros)

    Returns:
        dict: A dictionary containing company information
    """
    # Ensure CIK is properly formatted (remove leading zeros)
    cik = cik.lstrip('0')

    # URL for the SEC's company information page
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"

    # Set the header as required by SEC
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    # Make the GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        return {"error": f"Failed to retrieve company information. Status code: {response.status_code}"}

    # Parse the JSON response
    try:
        company_data = response.json()
        return company_data
    except json.JSONDecodeError:
        return {"error": "Failed to parse company information JSON"}

def get_recent_filings(cik: str, filing_type: Optional[str], count: int) -> List[Dict[str, Any]]:
    """
    Get recent SEC filings for a company.

    Args:
        cik (str): The company's CIK number (with or without leading zeros)
        filing_type (str, optional): The type of filing to retrieve (e.g., "10-K", "10-Q")
        count (int, optional): The number of filings to retrieve, if you don't know how many then choose 5.

    Returns:
        list: A list of dictionaries containing filing information
    """

    # Ensure CIK is properly formatted (remove leading zeros)
    cik = cik.lstrip('0')

    # URL for the SEC's company filings RSS feed
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type or ''}&count={count}&output=atom"

    # Set the header as required by SEC
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    # Make the GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        return [{"error": f"Failed to retrieve filings. Status code: {response.status_code}"}]

    # Parse the XML response
    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception as e:
        # Fall back to html.parser if lxml is not available
        soup = BeautifulSoup(response.text, 'html.parser')
    entries = soup.find_all('entry')

    filings = []
    for entry in entries:
        title = entry.find('title').text if entry.find('title') else "Unknown"
        filing_date = entry.find('updated').text if entry.find('updated') else "Unknown"
        link = entry.find('link')['href'] if entry.find('link') else None

        filings.append({
            'title': title,
            'filing_date': filing_date,
            'link': link
        })

    return filings

def extract_filing_text(filing_url: str) -> str:
    """
    Extract the text content from an SEC filing.

    Args:
        filing_url (str): The URL of the SEC filing

    Returns:
        str: The text content of the filing
    """
    # Set the header as required by SEC
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    # Make the GET request
    response = requests.get(filing_url, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        return f"Failed to retrieve filing. Status code: {response.status_code}"

    # Parse the HTML response
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the text content
    text_content = soup.get_text(separator='\n')

    return text_content

def analyze_filing(filing_text: str, keywords: List[str] ) -> Dict[str, Any]:
    """
    Analyze the content of an SEC filing.

    Args:
        filing_text (str): The text content of the filing
        keywords (list, optional): A list of keywords to search for in the filing

    Returns:
        dict: A dictionary containing analysis results
    """
    analysis = {
        'length': len(filing_text),
        'keyword_matches': {}
    }

    # Search for keywords if provided
    if keywords:
        for keyword in keywords:
            matches = re.findall(r'\b' + re.escape(keyword) + r'\b', filing_text, re.IGNORECASE)
            analysis['keyword_matches'][keyword] = len(matches)

    return analysis
