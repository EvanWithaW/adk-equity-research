import requests
from bs4 import BeautifulSoup
import re

def find_cik(company_name: str) -> list:
    """
    Find the CIK (Central Index Key) for a company using the SEC's CIK lookup tool.

    Args:
        company_name (str): The company name or ticker symbol to search for

    Returns:
        list: A list of dictionaries containing company information with CIK numbers
    """
    # URL for the SEC's CIK lookup tool
    url = "https://www.sec.gov/cgi-bin/cik_lookup"

    # Set the header as specified
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    # Prepare the form data
    data = {
        'company': company_name
    }

    # Make the POST request
    response = requests.post(url, headers=headers, data=data)

    # Check if the request was successful
    if response.status_code != 200:
        return []

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Check if any results were found
    no_results = soup.find(string=re.compile('No matching companies'))
    if no_results:
        return []

    # Check for pre-block format
    pre_blocks = soup.find_all('pre')
    results = []

    # If we have at least one pre-block, process all of them
    if pre_blocks:
        # Combine all pre-block text
        all_text = ""
        for pre_block in pre_blocks:
            all_text += pre_block.get_text() + "\n"

        # Process each line
        for line in all_text.split('\n'):
            if not line.strip() or 'CIK Code' in line or 'Company Name' in line:
                continue

            match = re.search(r'(\d{10})\s+(.+)$', line.strip())
            if match:
                cik = match.group(1)
                company_name = match.group(2).strip()
                results.append({
                    'CIK': cik,
                    'Company': company_name,
                    'Link': f"https://www.sec.gov/browse-edgar?action=getcompany&CIK={cik.lstrip('0')}"
                })

    return results
