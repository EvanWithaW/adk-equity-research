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
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import re
import os
import json
import warnings
import time
import random
from typing import List, Dict, Any, Optional, Callable
import json

# Filter the XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Import the existing find_cik function
from filingsResearch.get_company_cik import find_cik

def retry_with_backoff(max_retries: int = 5, initial_delay: float = 1.0, 
                      backoff_factor: float = 2.0, jitter: bool = True,
                      retry_on: Callable[[Exception], bool] = None) -> Callable:
    """
    Retry decorator with exponential backoff for handling rate limits and transient errors.

    Args:
        max_retries (int): Maximum number of retries before giving up
        initial_delay (float): Initial delay in seconds
        backoff_factor (float): Factor to multiply delay by after each retry
        jitter (bool): Whether to add random jitter to the delay
        retry_on (Callable): Function that takes an exception and returns True if it should be retried

    Returns:
        Callable: Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for retry in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if retry_on and not retry_on(e):
                        raise

                    # Check if we've reached the maximum number of retries
                    if retry >= max_retries:
                        raise

                    # Calculate delay with optional jitter
                    if jitter:
                        actual_delay = delay * (1 + random.random() * 0.1)
                    else:
                        actual_delay = delay

                    print(f"Request failed with error: {str(e)}. Retrying in {actual_delay:.2f} seconds...")
                    time.sleep(actual_delay)

                    # Increase delay for next retry
                    delay *= backoff_factor

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator

def should_retry_request(exception: Exception) -> bool:
    """
    Determine if a request should be retried based on the exception.

    Args:
        exception (Exception): The exception that was raised

    Returns:
        bool: True if the request should be retried, False otherwise
    """
    # Retry on connection errors, timeouts, and rate limits (429)
    if isinstance(exception, requests.exceptions.RequestException):
        if isinstance(exception, requests.exceptions.ConnectionError):
            return True
        if isinstance(exception, requests.exceptions.Timeout):
            return True
        if isinstance(exception, requests.exceptions.HTTPError):
            # Retry on 429 (Too Many Requests) and 5xx errors
            if hasattr(exception, 'response') and exception.response is not None:
                if exception.response.status_code == 429:
                    return True
                if 500 <= exception.response.status_code < 600:
                    return True

    return False

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

    # Make the GET request with retry logic
    try:
        response = make_request(url, headers)
    except Exception as e:
        return {"error": f"Failed to retrieve company information: {str(e)}"}

    # Parse the JSON response
    try:
        company_data = response.json()
        return company_data
    except json.JSONDecodeError:
        return {"error": "Failed to parse company information JSON"}

def find_filings(cik: str, filing_type: Optional[str], count: int) -> List[Dict[str, Any]]:
    """
    Find the company's most recent filings from the CIK.

    This tool helps you find the most recent SEC filings for a company using its CIK number.
    It returns a list of the most recent filings, including their titles, dates, and links.

    HOW TO USE THIS TOOL:
    1. First, get the company's CIK using the find_cik tool
    2. Call this tool with the CIK number to find recent filings
    3. You can optionally specify a filing type (e.g., "10-K", "10-Q") and count
    4. The tool will return a list of filings with their titles, dates, and links

    EXAMPLE:
    ```
    # Find Apple's CIK
    apple_results = find_cik("Apple")
    apple_cik = apple_results[0]["CIK"]

    # Find Apple's recent 10-K filings
    apple_filings = find_filings(apple_cik, "10-K", 3)

    # Display the results
    for filing in apple_filings:
        print(f"Title: {filing['title']}")
        print(f"Date: {filing['filing_date']}")
        print(f"Link: {filing['link']}")
    ```

    Args:
        cik (str): The company's CIK number (with or without leading zeros)
        filing_type (str, optional): The type of filing to retrieve (e.g., "10-K", "10-Q"). Default is None (all types).
        count (int, optional): The number of filings to retrieve. Default is 5.

    Returns:
        list: A list of dictionaries containing filing information (title, filing_date, link)
    """

    # Ensure CIK is properly formatted (remove leading zeros)
    cik = cik.lstrip('0')

    # URL for the SEC's company filings RSS feed
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type or ''}&count={count}&output=atom"

    print(f"Requesting URL: {url}")

    # Set the header as required by SEC
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    try:
        # Make the GET request with retry logic
        try:
            response = make_request(url, headers)
        except Exception as e:
            print(f"Error: Failed to retrieve filings: {str(e)}")
            return [{"error": f"Failed to retrieve filings: {str(e)}"}]

        # Print response info for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content length: {len(response.text)} characters")
        print(f"Response content preview: {response.text[:200]}...")

        # Parse the XML response
        try:
            # First try lxml, which is the best for XML
            soup = BeautifulSoup(response.text, 'lxml')
            print("Using lxml parser")
        except Exception as e:
            try:
                # Then try the xml feature
                soup = BeautifulSoup(response.text, features="xml")
                print("Using xml feature parser")
            except Exception as e:
                # Finally fall back to html.parser, which is always available
                # This might cause warnings, but they're filtered out by the warning filter
                soup = BeautifulSoup(response.text, 'html.parser')
                print("Using html.parser")

        # Try different approaches to find entries
        # First try with namespace
        entries = soup.find_all('entry')
        print(f"Found {len(entries)} entries using 'entry' tag")

        # If no entries found, try without namespace by parsing the XML manually
        if not entries and 'xml' in response.text.lower():
            print("Trying to parse XML manually...")
            # Print more of the response for debugging
            print(f"Full response content: {response.text}")

            # Try to extract entries using string manipulation
            import re
            entry_pattern = r'<entry>(.*?)</entry>'
            entries_text = re.findall(entry_pattern, response.text, re.DOTALL)
            print(f"Found {len(entries_text)} entries using regex")

            if entries_text:
                # Create a list to hold our manually parsed entries
                manual_entries = []

                for entry_text in entries_text:
                    # Extract title
                    title_match = re.search(r'<title>(.*?)</title>', entry_text, re.DOTALL)
                    title = title_match.group(1) if title_match else "Unknown"

                    # Extract updated date
                    updated_match = re.search(r'<updated>(.*?)</updated>', entry_text, re.DOTALL)
                    updated = updated_match.group(1) if updated_match else "Unknown"

                    # Extract link
                    link_match = re.search(r'<link[^>]*href="([^"]*)"', entry_text)
                    link = link_match.group(1) if link_match else None

                    # Create a simple object to mimic BeautifulSoup's structure
                    class SimpleEntry:
                        def __init__(self, title, updated, link):
                            self.title = title
                            self.updated = updated
                            self.link = link

                        def find(self, tag):
                            if tag == 'title':
                                return SimpleText(self.title)
                            elif tag == 'updated':
                                return SimpleText(self.updated)
                            elif tag == 'link':
                                return {'href': self.link} if self.link else None
                            return None

                    class SimpleText:
                        def __init__(self, text):
                            self.text = text

                    manual_entries.append(SimpleEntry(title, updated, link))

                # Use our manually parsed entries
                entries = manual_entries
                print(f"Successfully parsed {len(entries)} entries manually")

        # If no entries found, try alternative approaches
        if not entries:
            # Try to find filing links directly
            print("No entries found, trying alternative approaches...")

            # Try to find tables that might contain filing links
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables")

            # Try to find links that might be filings
            links = soup.find_all('a')
            print(f"Found {len(links)} links")

            # Try to find filing information in a different format
            # For example, look for rows in tables that might contain filing information
            rows = []
            for table in tables:
                rows.extend(table.find_all('tr'))
            print(f"Found {len(rows)} rows in tables")

            # If we found rows, try to extract filing information from them
            if rows:
                filings = []
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Look for cells that might contain filing type, date, and link
                        filing_type_cell = cells[0].text.strip() if len(cells) > 0 else ""
                        filing_date_cell = cells[3].text.strip() if len(cells) > 3 else ""

                        # Look for a link in the row
                        link = None
                        for cell in cells:
                            a_tag = cell.find('a')
                            if a_tag and 'href' in a_tag.attrs:
                                link = a_tag['href']
                                if not link.startswith('http'):
                                    # If the link is relative, construct the full URL
                                    base_url = "https://www.sec.gov"
                                    link = f"{base_url}{link}"
                                break

                        # If we found a link and it looks like a filing, add it to the list
                        if link and (filing_type.lower() in filing_type_cell.lower() if filing_type else True):
                            filings.append({
                                'title': filing_type_cell,
                                'filing_date': filing_date_cell,
                                'link': link
                            })

                # If we found filings, return them
                if filings:
                    print(f"Found {len(filings)} filings using alternative approach")
                    return filings

            # If we still haven't found any filings, try one more approach
            # Look for any links that might be filings
            filings = []
            for link in links:
                href = link.get('href')
                text = link.text.strip()

                # If the link text or href contains the filing type, it might be a filing
                if href and ((filing_type and filing_type.lower() in text.lower()) or 
                             (filing_type and filing_type.lower() in href.lower()) or
                             "filing" in text.lower() or "document" in text.lower()):
                    if not href.startswith('http'):
                        # If the link is relative, construct the full URL
                        base_url = "https://www.sec.gov"
                        href = f"{base_url}{href}"

                    filings.append({
                        'title': text,
                        'filing_date': "Unknown",
                        'link': href
                    })

            # If we found filings, return them
            if filings:
                print(f"Found {len(filings)} filings using link text approach")
                return filings

            # If we still haven't found any filings, return an empty list
            print("Could not find any filings using any approach")
            return []

        # Process entries if found
        filings = []
        for entry in entries:
            title = entry.find('title').text if entry.find('title') else "Unknown"
            filing_date = entry.find('updated').text if entry.find('updated') else "Unknown"
            link = entry.find('link')['href'] if entry.find('link') and 'href' in entry.find('link').attrs else None

            if link:
                filings.append({
                    'title': title,
                    'filing_date': filing_date,
                    'link': link
                })

        print(f"Found {len(filings)} filings from entries")
        return filings

    except Exception as e:
        print(f"Error in get_recent_filings: {str(e)}")
        return [{"error": f"Failed to retrieve filings: {str(e)}"}]

@retry_with_backoff(max_retries=3, initial_delay=2.0, retry_on=should_retry_request)
def make_request(url: str, headers: Dict[str, str]) -> requests.Response:
    """
    Make an HTTP request with retry logic.

    Args:
        url (str): The URL to request
        headers (Dict[str, str]): The headers to include in the request

    Returns:
        requests.Response: The response from the server
    """
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()  # Raise an exception for 4xx/5xx status codes
    return response

def extract_filing_text(filing_url: str) -> str:
    """
    Extract the text content from an SEC filing.

    This function handles various SEC filing formats. It first accesses the index page,
    then finds the link to the filing document, and finally retrieves and parses the document.
    It includes multiple fallback mechanisms to handle different filing formats and structures.
    The function ensures that only text content is returned, with no images.

    This function uses retry logic with exponential backoff to handle rate limits and transient errors.

    Args:
        filing_url (str): The URL of the SEC filing index page

    Returns:
        str: The text content of the filing
    """
    # Set the header as required by SEC
    headers = {
        'User-Agent': 'Educational Project Evan Weidner hi@evanweidner.com'
    }

    try:
        # Reduced logging to prevent excessive output
        # Make the GET request to the index page with retry logic
        try:
            response = make_request(filing_url, headers)
        except Exception as e:
            return f"Failed to retrieve filing index page: {str(e)}"

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if this is an inline XBRL viewer page
        if '/ix?doc=' in filing_url:
            print("This appears to be an inline XBRL viewer page. Extracting the actual document URL.")
            # Extract the actual document URL from the inline XBRL viewer page
            doc_url_match = re.search(r'/ix\?doc=(/Archives/edgar/data/[^"&]+)', filing_url)
            if doc_url_match:
                actual_doc_url = f"https://www.sec.gov{doc_url_match.group(1)}"
                print(f"Extracted actual document URL: {actual_doc_url}")

                # Fetch the actual document
                try:
                    try:
                        doc_response = make_request(actual_doc_url, headers)
                        print(f"Successfully retrieved actual document ({len(doc_response.text)} characters)")
                        # Parse the document
                        doc_soup = BeautifulSoup(doc_response.text, 'html.parser')

                        # Remove image tags
                        for img in doc_soup.find_all('img'):
                            img.decompose()

                        # Remove script and style tags
                        for tag in doc_soup.find_all(['script', 'style']):
                            tag.decompose()

                        # Extract text content
                        text_content = doc_soup.get_text(separator='\n')
                        text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
                        text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

                        if len(text_content.strip()) > 1000:
                            # Reduced logging to prevent excessive output
                            return text_content
                    except Exception as e:
                        print(f"Failed to retrieve actual document: {str(e)}")
                except Exception as e:
                    print(f"Error retrieving actual document: {str(e)}")
            else:
                print("Could not extract actual document URL from inline XBRL viewer page")

        # Check if this is already a document page (not an index)
        # If it has substantial text content and looks like a filing document, process it directly
        # Expanded check to capture more direct document pages
        is_direct_document = False

        # Check for substantial content
        if len(response.text) > 10000:
            # Check for common 10-K indicators in the text
            if ('FORM 10-K' in response.text or 
                'ANNUAL REPORT' in response.text.upper() or
                'SECURITIES AND EXCHANGE COMMISSION' in response.text.upper() and 
                ('FISCAL YEAR' in response.text.upper() or 'ANNUAL REPORT' in response.text.upper())):
                is_direct_document = True

            # Check for common document structure indicators
            elif soup.find('div', id='filing-content') or soup.find('div', id='document') or soup.find('div', class_='filing'):
                is_direct_document = True

            # Check for common 10-K section headers
            elif any(header in response.text.upper() for header in [
                'ITEM 1. BUSINESS', 
                'ITEM 1A. RISK FACTORS', 
                'ITEM 7. MANAGEMENT\'S DISCUSSION',
                'ITEM 8. FINANCIAL STATEMENTS'
            ]):
                is_direct_document = True

        if is_direct_document:
            # Reduced logging to prevent excessive output

            # Try to find the main content container first
            main_content = None

            # Look for common content containers
            container_ids = ['filing-content', 'main-content', 'document', 'content', 'body']
            for container_id in container_ids:
                container = soup.find(id=container_id)
                if container:
                    print(f"Found content container with id '{container_id}'")
                    main_content = container
                    break

            # If no specific container found by ID, try to find by tag and class
            if not main_content:
                # Look for div with class containing 'filing' or 'document'
                for div in soup.find_all('div'):
                    if div.get('class') and any(cls for cls in div.get('class') if 'filing' in cls.lower() or 'document' in cls.lower() or 'content' in cls.lower()):
                        print(f"Found content container with class '{div.get('class')}'")
                        main_content = div
                        break

            # If still no container found, use the whole document
            if not main_content:
                # Reduced logging to prevent excessive output
                main_content = soup

            # Remove image tags from the selected content
            for img in main_content.find_all('img'):
                img.decompose()

            # Remove script and style tags from the selected content
            for tag in main_content.find_all(['script', 'style']):
                tag.decompose()

            # Extract text content from the selected content
            text_content = main_content.get_text(separator='\n')

            # Clean up the text content
            text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
            text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

            # Check if we got meaningful content
            if len(text_content.strip()) < 5000:
                print("Warning: Extracted text is very short, might not be the complete document")

                # Try using the whole document as a fallback
                if main_content != soup:
                    print("Trying to extract text from the whole document as a fallback")

                    # Remove image tags from the whole document
                    for img in soup.find_all('img'):
                        img.decompose()

                    # Remove script and style tags from the whole document
                    for tag in soup.find_all(['script', 'style']):
                        tag.decompose()

                    # Extract text content from the whole document
                    text_content = soup.get_text(separator='\n')
                    text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
                    text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

            # Reduced logging to prevent excessive output
            return text_content

        print("Looking for document links in the index page...")

        # Find the table with the filing documents
        table = soup.find('table', class_='tableFile')

        # If no table is found, try alternative approaches
        if not table:
            # Try to find any tables that might contain filing links
            all_tables = soup.find_all('table')
            for potential_table in all_tables:
                if potential_table.find_all('a'):
                    table = potential_table
                    break

            # If still no table with links, try to extract text from the current page
            if not table:
                text_content = soup.get_text(separator='\n')
                if len(text_content.strip()) > 100:  # Ensure we have meaningful content
                    return text_content
                else:
                    return "Could not find filing content on the index page."

        # Find all rows in the table
        rows = table.find_all('tr')

        # Print table structure for debugging
        print(f"Found {len(rows)} rows in the table")

        # Priority order for file types to look for
        file_priorities = [
            # Main document types - specifically looking for the primary 10-K document
            # First priority: Exact matches for main 10-K document
            lambda cell: cell.text.strip().lower() == "10-k" and cell.text.strip().lower().endswith('.htm'),
            lambda cell: cell.text.strip().lower() == "form 10-k" and cell.text.strip().lower().endswith('.htm'),

            # Second priority: Company-specific main document patterns
            lambda cell: re.match(r'^aapl-10-?k.*\.htm$', cell.text.strip().lower()) is not None,
            lambda cell: re.match(r'^aapl-20\d{2}\.htm$', cell.text.strip().lower()) is not None,
            lambda cell: re.match(r'^aapl-20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\.htm$', cell.text.strip().lower()) is not None,

            # Third priority: Common main document patterns
            lambda cell: re.match(r'^10-?k\.htm$', cell.text.strip().lower()) is not None,
            lambda cell: re.match(r'^form10-?k\.htm$', cell.text.strip().lower()) is not None,
            lambda cell: re.match(r'^10-?k20\d{2}\.htm$', cell.text.strip().lower()) is not None,

            # Fourth priority: Description-based patterns
            lambda cell: "10-k" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and "complete submission" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),
            lambda cell: "annual report" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),
            lambda cell: "form 10-k" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),

            # Fifth priority: Document type patterns
            lambda cell: "10-k" in cell.text.strip().lower() and "form" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),
            lambda cell: "annual" in cell.text.strip().lower() and "report" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),

            # Sixth priority: Complete submission (might contain all documents)
            lambda cell: "10-k" in cell.text.strip().lower() and "complete submission" in cell.text.strip().lower(),

            # Seventh priority: Generic document types
            lambda cell: cell.text.strip().lower().endswith('.htm') and not cell.text.strip().lower().endswith('.html') and "exhibit" not in cell.text.strip().lower(),
            lambda cell: "document" in cell.text.strip().lower() and "exhibit" not in cell.text.strip().lower() and cell.text.strip().lower().endswith('.htm'),

            # Fallback to any HTM file that's not an exhibit
            lambda cell: cell.text.strip().lower().endswith('.htm') and "exhibit" not in cell.text.strip().lower(),

            # Last resort - any HTM file
            lambda cell: cell.text.strip().lower().endswith('.htm'),

            # Absolute last resort - any HTML file
            lambda cell: cell.text.strip().lower().endswith('.html'),

            # Final fallback - any file with a link
            lambda cell: True  # This will match any cell that has a link
        ]

        # Print the first few rows for debugging
        for i, row in enumerate(rows[:5]):
            cells = row.find_all('td')
            if cells:
                print(f"Row {i}: {[cell.text.strip() for cell in cells]}")

        # Look for filing document links based on priority
        document_link = None
        for priority_check in file_priorities:
            if document_link:
                break
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    if priority_check(cells[2]):
                        a_tag = cells[2].find('a')
                        if a_tag and 'href' in a_tag.attrs:
                            document_link = a_tag['href']
                            break

        # If still no link is found, try a more aggressive approach
        if not document_link:
            # Look for any link in the page
            all_links = soup.find_all('a')
            print(f"Found {len(all_links)} links in the page")

            # Extract the CIK from the URL if possible
            cik_match = re.search(r'/data/(\d+)/', filing_url)
            cik = cik_match.group(1) if cik_match else None
            print(f"Extracted CIK from URL: {cik}")

            # First try to find links that match specific patterns for main documents
            for link in all_links:
                href = link.get('href')
                if not href:
                    continue

                # Skip links to the SEC homepage or other non-filing pages
                if href == '/' or href == '/index.htm' or href == 'https://www.sec.gov/' or href == 'https://www.sec.gov/index.htm':
                    continue

                # Skip links that don't point to Archives if we're on an index page
                if '/Archives/edgar/data/' not in filing_url and '/Archives/edgar/data/' not in href:
                    continue

                # Extract just the filename for pattern matching
                filename = os.path.basename(href)

                # Check if this is likely the main document (not an exhibit)
                if ((filename.startswith('10-k') or filename.startswith('10k') or 
                     filename.startswith('form10-k') or filename.startswith('form10k') or
                     (cik and filename.startswith(cik))) and 
                    'exhibit' not in filename.lower() and
                    filename.endswith('.htm')):

                    print(f"Found potential main document link: {href}")
                    print(f"Link text: {link.text.strip()}")
                    document_link = href
                    break

            # If still no link found, fall back to any HTM file that's not an exhibit
            if not document_link:
                for link in all_links:
                    href = link.get('href')
                    if not href:
                        continue

                    # Skip links to the SEC homepage or other non-filing pages
                    if href == '/' or href == '/index.htm' or href == 'https://www.sec.gov/' or href == 'https://www.sec.gov/index.htm':
                        continue

                    # Check if this is an HTM file and not an exhibit
                    if href.endswith('.htm') and 'exhibit' not in href.lower() and 'exhibit' not in link.text.strip().lower():
                        print(f"Found HTM file (not exhibit): {href}")
                        print(f"Link text: {link.text.strip()}")
                        document_link = href
                        break

            # If still no link found, fall back to any HTM file
            if not document_link:
                for link in all_links:
                    href = link.get('href')
                    if href and (href.endswith('.htm') or href.endswith('.html') or href.endswith('.txt')):
                        # Skip links to the SEC homepage or other non-filing pages
                        if href == '/' or href == '/index.htm' or href == 'https://www.sec.gov/' or href == 'https://www.sec.gov/index.htm':
                            continue

                        print(f"Found any HTM/HTML/TXT file: {href}")
                        print(f"Link text: {link.text.strip()}")
                        document_link = href
                        break

        # If still no link is found, return the text from the index page
        if not document_link:
            text_content = soup.get_text(separator='\n')
            if len(text_content.strip()) > 100:  # Ensure we have meaningful content
                return text_content
            else:
                return "Could not find any document links in the filing."

        # Construct the full URL for the document
        if document_link.startswith('http'):
            document_url = document_link
        else:
            # If the link is relative, construct the full URL
            base_url = '/'.join(filing_url.split('/')[:-1])
            document_url = f"{base_url}/{document_link}"

        # Make the GET request to the document with retry logic
        try:
            response = make_request(document_url, headers)
        except Exception as e:
            # Try an alternative approach - extract text from the index page
            text_content = soup.get_text(separator='\n')
            if len(text_content.strip()) > 100:  # Ensure we have meaningful content
                return text_content
            else:
                return f"Failed to retrieve document file: {str(e)}"

        # Parse the HTML response
        document_soup = BeautifulSoup(response.text, 'html.parser')

        print(f"Successfully retrieved document from {document_url} ({len(response.text)} characters)")

        # Check if this is a 10-K document by looking for common indicators
        is_10k = False
        if ('FORM 10-K' in response.text or 
            'ANNUAL REPORT' in response.text.upper() or
            'SECURITIES AND EXCHANGE COMMISSION' in response.text.upper() and 
            ('FISCAL YEAR' in response.text.upper() or 'ANNUAL REPORT' in response.text.upper()) or
            any(header in response.text.upper() for header in [
                'ITEM 1. BUSINESS', 
                'ITEM 1A. RISK FACTORS', 
                'ITEM 7. MANAGEMENT\'S DISCUSSION',
                'ITEM 8. FINANCIAL STATEMENTS'
            ])):
            is_10k = True
            print("Detected 10-K document based on content indicators")

        # Check if this is an XBRL document
        is_xbrl = False
        if '<?xml' in response.text[:1000] and ('xmlns:xbrl' in response.text or 'xmlns:ix' in response.text):
            is_xbrl = True
            print("Detected XBRL document format")

            # For XBRL documents, try to find a non-XBRL version
            if document_url.endswith('.htm') or document_url.endswith('.html'):
                # Try multiple alternative URLs
                alternative_urls = []

                # Try to construct a URL for a text version
                txt_url = document_url.rsplit('.', 1)[0] + '.txt'
                alternative_urls.append(txt_url)

                # Try to find a non-inline version (remove ix?doc= if present)
                if '/ix?doc=' in document_url:
                    non_inline_url = re.sub(r'/ix\?doc=', '/', document_url)
                    alternative_urls.append(non_inline_url)

                # Try to find a complete submission text file
                if '/Archives/edgar/data/' in document_url:
                    # Extract the accession number from the URL
                    acc_match = re.search(r'/(\d{10}-\d{2}-\d{6})/', document_url)
                    if acc_match:
                        acc_num = acc_match.group(1)
                        acc_num_no_dashes = acc_num.replace('-', '')
                        base_url = document_url.split('/Archives/edgar/data/')[0]
                        complete_submission_url = f"{base_url}/Archives/edgar/data/{document_url.split('/Archives/edgar/data/')[1].split('/')[0]}/{acc_num}/{acc_num_no_dashes}.txt"
                        alternative_urls.append(complete_submission_url)

                # Try each alternative URL
                for alt_url in alternative_urls:
                    print(f"Trying alternative URL: {alt_url}")
                    try:
                        alt_response = make_request(alt_url, headers)
                        if len(alt_response.text) > 5000:
                            print(f"Found alternative version at {alt_url} ({len(alt_response.text)} characters)")
                            response = alt_response
                            document_soup = BeautifulSoup(response.text, 'html.parser')
                            is_xbrl = False
                            break
                    except Exception as e:
                        print(f"Error retrieving alternative version from {alt_url}: {str(e)}")
                        continue

                # If we still have an XBRL document, try to extract the actual document URL from the SEC website
                if is_xbrl and '/ix?doc=' in document_url:
                    try:
                        # Extract the CIK and accession number
                        cik_match = re.search(r'/data/(\d+)/', document_url)
                        acc_match = re.search(r'/(\d{10}-\d{2}-\d{6})/', document_url)

                        if cik_match and acc_match:
                            cik = cik_match.group(1)
                            acc_num = acc_match.group(1)

                            # Construct the URL to the document index page
                            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num.replace('-', '')}/{acc_num}-index.htm"
                            print(f"Trying to find document links from index page: {index_url}")

                            try:
                                index_response = make_request(index_url, headers)
                                index_soup = BeautifulSoup(index_response.text, 'html.parser')

                                # Look for links to the 10-K document (not XBRL)
                                for link in index_soup.find_all('a'):
                                    href = link.get('href')
                                    if href and href.endswith('.htm') and not '/ix?doc=' in href:
                                        if '10-k' in href.lower() or '10k' in href.lower() or 'form10' in href.lower() or 'annual' in href.lower():
                                            # Construct the full URL
                                            if href.startswith('http'):
                                                doc_url = href
                                            else:
                                                doc_url = f"https://www.sec.gov{href}" if href.startswith('/') else f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num.replace('-', '')}/{href}"

                                            print(f"Found potential 10-K document link: {doc_url}")
                                            try:
                                                doc_response = make_request(doc_url, headers)
                                                if len(doc_response.text) > 5000:
                                                    print(f"Successfully retrieved document from link ({len(doc_response.text)} characters)")
                                                    response = doc_response
                                                    document_soup = BeautifulSoup(response.text, 'html.parser')
                                                    is_xbrl = '<?xml' in response.text[:1000] and ('xmlns:xbrl' in response.text or 'xmlns:ix' in response.text)
                                                    if not is_xbrl:
                                                        break
                                            except Exception as e:
                                                print(f"Error retrieving document from link: {str(e)}")
                            except Exception as e:
                                print(f"Failed to retrieve index page: {str(e)}")
                    except Exception as e:
                        print(f"Error trying to find document from index page: {str(e)}")

        # Remove all image tags to ensure no images are included
        for img in document_soup.find_all('img'):
            img.decompose()

        # Remove script and style tags that might contain non-text content
        for tag in document_soup.find_all(['script', 'style']):
            tag.decompose()

        # Try to find the main content
        main_content = None

        # Look for common content containers
        container_ids = ['filing-content', 'main-content', 'document', 'content', 'body']
        for container_id in container_ids:
            container = document_soup.find(id=container_id)
            if container:
                print(f"Found content container with id '{container_id}'")
                main_content = container
                break

        # If no specific container found by ID, try to find by tag and class
        if not main_content:
            # Look for div with class containing 'filing' or 'document'
            for div in document_soup.find_all('div'):
                if div.get('class') and any(cls for cls in div.get('class') if 'filing' in cls.lower() or 'document' in cls.lower() or 'content' in cls.lower()):
                    print(f"Found content container with class '{div.get('class')}'")
                    main_content = div
                    break

        # If still no container found, look for the largest text block
        if not main_content:
            # Find all divs with substantial text content
            text_blocks = []
            for div in document_soup.find_all('div'):
                text = div.get_text()
                if len(text) > 1000:  # Only consider blocks with substantial text
                    text_blocks.append((div, len(text)))

            # Sort by text length (descending)
            text_blocks.sort(key=lambda x: x[1], reverse=True)

            if text_blocks:
                print(f"Using largest text block with {text_blocks[0][1]} characters")
                main_content = text_blocks[0][0]

        # If no specific container found, use the whole document
        if not main_content:
            # Reduced logging to prevent excessive output
            main_content = document_soup

        # Special handling for XBRL documents
        if is_xbrl:
            print("Extracting text from XBRL document...")

            # For XBRL documents, we need a more specialized approach
            # First, try to find the complete submission text file
            if '/Archives/edgar/data/' in document_url and not document_url.endswith('.txt'):
                # Extract the accession number and CIK from the URL
                acc_match = re.search(r'/(\d{10}-\d{2}-\d{6})/', document_url)
                cik_match = re.search(r'/data/(\d+)/', document_url)

                if acc_match and cik_match:
                    acc_num = acc_match.group(1)
                    acc_num_no_dashes = acc_num.replace('-', '')
                    cik = cik_match.group(1)

                    # Construct the URL to the complete submission text file
                    complete_submission_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_no_dashes}/{acc_num_no_dashes}.txt"
                    print(f"Trying to access complete submission text file: {complete_submission_url}")

                    try:
                        txt_response = make_request(complete_submission_url, headers)
                        if len(txt_response.text) > 10000:
                            print(f"Successfully retrieved complete submission text file ({len(txt_response.text)} characters)")

                            # Extract the 10-K document from the complete submission
                            # The 10-K document is typically between <DOCUMENT> and </DOCUMENT> tags with <TYPE>10-K
                            doc_matches = re.finditer(r'<DOCUMENT>.*?<TYPE>(10-K|10K).*?</DOCUMENT>', txt_response.text, re.DOTALL)

                            for match in doc_matches:
                                doc_text = match.group(0)
                                # Extract the text content between <TEXT> and </TEXT> tags
                                text_match = re.search(r'<TEXT>(.*?)</TEXT>', doc_text, re.DOTALL)
                                if text_match:
                                    extracted_text = text_match.group(1).strip()
                                    if len(extracted_text) > 10000:
                                        print(f"Extracted 10-K document from complete submission ({len(extracted_text)} characters)")

                                        # If it's HTML, parse it to extract text
                                        if extracted_text.startswith('<') and ('</html>' in extracted_text.lower() or '</body>' in extracted_text.lower()):
                                            doc_soup = BeautifulSoup(extracted_text, 'html.parser')
                                            # Remove script and style tags
                                            for tag in doc_soup.find_all(['script', 'style']):
                                                tag.decompose()
                                            # Extract text
                                            text_content = doc_soup.get_text(separator='\n')
                                        else:
                                            # Use the extracted text directly
                                            text_content = extracted_text

                                        # Clean up the text
                                        text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
                                        text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

                                        return text_content
                    except Exception as e:
                        print(f"Error retrieving complete submission text file: {str(e)}")

            # If we couldn't get the complete submission or extract the 10-K document,
            # try to extract text from the XBRL document itself

            # First, try to find sections that might contain actual content
            # Look for div elements with specific attributes that might indicate 10-K content
            content_sections = []

            # Look for divs with specific text content that might indicate 10-K sections
            section_indicators = [
                'Item 1. Business', 
                'Item 1A. Risk Factors', 
                'Item 7. Management', 
                'Item 8. Financial Statements'
            ]

            for div in document_soup.find_all(['div', 'section', 'span']):
                div_text = div.get_text().strip()
                if any(indicator in div_text for indicator in section_indicators):
                    content_sections.append(div)
                    # Also add the next few siblings which might contain the actual content
                    for sibling in div.find_next_siblings():
                        if len(sibling.get_text().strip()) > 100:
                            content_sections.append(sibling)

            # If we found content sections, extract text from them
            if content_sections:
                print(f"Found {len(content_sections)} potential content sections")
                sections_text = ""
                for section in content_sections:
                    section_text = section.get_text().strip()
                    if len(section_text) > 100:  # Only add substantial sections
                        sections_text += section_text + "\n\n"

                if len(sections_text) > 5000:
                    print(f"Extracted {len(sections_text)} characters from content sections")
                    text_content = sections_text
                    return text_content

            # If we still don't have good content, try to extract all text from spans
            spans_text = ""
            for span in document_soup.find_all('span'):
                # Skip spans with very short text
                span_text = span.get_text().strip()
                if len(span_text) > 50:  # Only consider spans with substantial text
                    spans_text += span_text + "\n\n"

            # If we extracted substantial text from spans, use it
            if len(spans_text) > 5000:
                print(f"Extracted {len(spans_text)} characters from spans")
                text_content = spans_text
            else:
                # As a last resort, try to find any divs with substantial text
                text_blocks = []
                for div in document_soup.find_all('div'):
                    div_text = div.get_text().strip()
                    if len(div_text) > 1000:  # Only consider divs with substantial text
                        text_blocks.append((div, len(div_text)))

                # Sort by text length (descending)
                text_blocks.sort(key=lambda x: x[1], reverse=True)

                if text_blocks:
                    print(f"Using largest text block with {text_blocks[0][1]} characters")
                    text_content = text_blocks[0][0].get_text(separator='\n')
                else:
                    # If all else fails, extract text from the main content
                    text_content = main_content.get_text(separator='\n')
        else:
            # For non-XBRL documents, extract text normally
            text_content = main_content.get_text(separator='\n')

        # Clean up the text content
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
        text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

        # For 10-K documents, ensure we have substantial content
        min_content_length = 5000 if is_10k else 1000

        # Check if we got meaningful content
        if len(text_content.strip()) < min_content_length:
            print(f"Warning: Extracted text is very short ({len(text_content.strip())} characters), might not be the complete document")

            # Try using the whole document as a fallback
            if main_content != document_soup:
                print("Trying to extract text from the whole document as a fallback")
                text_content = document_soup.get_text(separator='\n')
                text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Remove excessive newlines
                text_content = re.sub(r'\s{3,}', ' ', text_content)     # Remove excessive spaces

                # If we still don't have enough content and this is a 10-K, try to find more content
                if len(text_content.strip()) < min_content_length and is_10k:
                    print("Still not enough content for a 10-K document, trying to extract more content...")

                    # Try to find any tables that might contain content
                    tables = document_soup.find_all('table')
                    if tables:
                        print(f"Found {len(tables)} tables, extracting content from them")
                        for table in tables:
                            table_text = table.get_text(separator='\n')
                            if len(table_text.strip()) > 500:  # Only add substantial tables
                                text_content += "\n\n" + table_text

                    # Try to find any pre tags that might contain content
                    pre_tags = document_soup.find_all('pre')
                    if pre_tags:
                        print(f"Found {len(pre_tags)} pre tags, extracting content from them")
                        for pre in pre_tags:
                            pre_text = pre.get_text(separator='\n')
                            if len(pre_text.strip()) > 500:  # Only add substantial pre tags
                                text_content += "\n\n" + pre_text

        # Reduced logging to prevent excessive output
        return text_content

    except Exception as e:
        # Catch any unexpected errors
        return f"Error extracting filing text: {str(e)}"

def extract_filing_information(filing_text: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Extract key information from an SEC filing text.

    This function extracts structured information from the filing text, including:
    - Filing type identification
    - Key financial metrics
    - Growth trends
    - Key sections (Business Description, Risk Factors, MD&A, etc.)
    - Keyword context if keywords are provided

    Args:
        filing_text (str): The text content of the filing
        keywords (list, optional): A list of keywords to search for in the filing

    Returns:
        dict: A dictionary containing extracted information including:
            - filing_type: Identified filing type
            - financial_metrics: Extracted financial metrics
            - growth_trends: Identified growth trends
            - sections: Key sections from the filing
            - keyword_context: Keywords with surrounding context (if keywords provided)
            - length: Length of the filing text
    """
    # Set default keywords relevant to equity research if none are provided
    if keywords is None:
        keywords = [
            "revenue", "profit", "growth", "margin", "earnings", "EPS", 
            "cash flow", "debt", "assets", "liabilities", "equity", 
            "dividend", "capital expenditure", "R&D", "market share",
            "competition", "risk", "guidance", "forecast", "outlook",
            "strategy", "acquisition", "merger", "restructuring"
        ]

    extracted_info = {
        'length': len(filing_text),
        'keyword_context': {},
        'financial_metrics': {},
        'growth_trends': [],
        'sections': {},
        'filing_type': "Unknown"
    }

    # If the filing text is too short, return a message indicating insufficient content
    if len(filing_text) < 1000:
        extracted_info['error'] = "The filing text is too short to provide meaningful information. Please ensure the complete filing text is provided."
        return extracted_info

    # Determine the filing type based on content
    if re.search(r'Form\s+10-K', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "10-K (Annual Report)"
    elif re.search(r'Form\s+10-Q', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "10-Q (Quarterly Report)"
    elif re.search(r'Form\s+8-K', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "8-K (Current Report)"
    elif re.search(r'Form\s+DEF\s+14A|Proxy\s+Statement', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "DEF 14A (Proxy Statement)"
    elif re.search(r'Form\s+S-1', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "S-1 (IPO Filing)"
    elif re.search(r'Form\s+S-3', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "S-3 (Shelf Registration)"
    elif re.search(r'Form\s+4', filing_text, re.IGNORECASE):
        extracted_info['filing_type'] = "Form 4 (Insider Transactions)"

    # Extract context around keywords (not just count)
    if keywords:
        for keyword in keywords:
            # Find all occurrences of the keyword
            keyword_matches = re.finditer(r'\b' + re.escape(keyword) + r'\b', filing_text, re.IGNORECASE)
            contexts = []

            for match in keyword_matches:
                # Get the position of the match
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(filing_text), match.end() + 100)

                # Extract the context (100 characters before and after)
                context = filing_text[start_pos:end_pos]

                # Clean up the context
                context = re.sub(r'\s+', ' ', context).strip()
                contexts.append(context)

            extracted_info['keyword_context'][keyword] = contexts

    # Extract key financial metrics using regex patterns
    metric_patterns = {
        'Revenue': r'(?:total\s+revenue|revenue)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|m|b)?',
        'Net Income': r'(?:net\s+income|net\s+earnings|net\s+profit)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|m|b)?',
        'EPS': r'(?:earnings\s+per\s+share|EPS)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)',
        'Operating Income': r'(?:operating\s+income|income\s+from\s+operations)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|m|b)?',
        'Gross Margin': r'(?:gross\s+margin)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:%|percent)?',
        'Total Assets': r'(?:total\s+assets)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|m|b)?',
        'Total Debt': r'(?:total\s+debt|long-term\s+debt)[^\n.]*?[\$]?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|m|b)?'
    }

    for metric_name, pattern in metric_patterns.items():
        matches = re.findall(pattern, filing_text, re.IGNORECASE)
        if matches:
            # Clean up the matches (remove commas, convert to float)
            cleaned_matches = []
            for match in matches:
                if match and match.strip():  # Check if match is not empty or just whitespace
                    try:
                        # Remove commas and convert to float
                        cleaned_match = float(match.replace(',', ''))
                        cleaned_matches.append(cleaned_match)
                    except ValueError:
                        # Skip values that can't be converted to float
                        print(f"Warning: Could not convert '{match}' to float")

            if cleaned_matches:
                value = max(cleaned_matches)  # Use the largest value
                # Format the value appropriately
                if value >= 1000000:
                    extracted_info['financial_metrics'][metric_name] = f"${value/1000000:,.2f} billion"
                elif value >= 1000:
                    extracted_info['financial_metrics'][metric_name] = f"${value/1000:,.2f} million"
                else:
                    extracted_info['financial_metrics'][metric_name] = f"${value:,.2f}"

    # Extract growth trends
    growth_patterns = [
        r'(?:revenue|sales)\s+(?:increased|decreased|grew|declined)\s+by\s+(?:approximately\s+)?([\d,]+(?:\.\d+)?)\s*(?:%|percent)',
        r'(?:profit|income|earnings)\s+(?:increased|decreased|grew|declined)\s+by\s+(?:approximately\s+)?([\d,]+(?:\.\d+)?)\s*(?:%|percent)',
        r'(?:margin|margins)\s+(?:increased|decreased|improved|declined)\s+by\s+(?:approximately\s+)?([\d,]+(?:\.\d+)?)\s*(?:%|percent|basis\s+points|bps)'
    ]

    for pattern in growth_patterns:
        matches = re.findall(pattern, filing_text, re.IGNORECASE)
        if matches:
            # Find the surrounding context for each match
            for match in matches:
                # Find the sentence containing this match
                match_pos = filing_text.lower().find(match.lower())
                if match_pos >= 0:
                    # Get the surrounding text (200 characters before and after)
                    start_pos = max(0, match_pos - 200)
                    end_pos = min(len(filing_text), match_pos + 200)
                    context = filing_text[start_pos:end_pos]

                    # Clean up the context and add it to the trends
                    context = re.sub(r'\s+', ' ', context).strip()
                    extracted_info['growth_trends'].append(context)

    # Extract key sections based on common section headers in SEC filings
    section_headers = {
        'Business Description': ['Item 1', 'Business', 'Description of Business'],
        'Risk Factors': ['Item 1A', 'Risk Factors', 'Risks'],
        'MD&A': ['Item 7', 'Management\'s Discussion', 'MD&A'],
        'Financial Statements': ['Item 8', 'Financial Statements'],
        'Executive Compensation': ['Executive Compensation', 'Compensation Discussion'],
        'Material Events': ['Material Events', 'Recent Developments']
    }

    for section_name, headers in section_headers.items():
        for header in headers:
            pattern = re.compile(r'(?i)(' + re.escape(header) + r'[:\.\s])(.*?)(?=Item\s+\d|PART\s+[IVX]|\Z)', re.DOTALL)
            match = pattern.search(filing_text)
            if match:
                extracted_info['sections'][section_name] = match.group(2).strip()
                break

    return extracted_info

def summarize_filing(filing_url: str, chunk_index: int, max_chunk_size: int) -> str:
    """
    Extract and summarize the text content from an SEC filing.

    This tool extracts the full text of an SEC filing and provides it to the agent,
    allowing the agent to use its own thought process to identify and highlight 
    the most important parts of the filing, including key metrics and insights.

    IMPORTANT: This tool accesses the ACTUAL FILING CONTENT, not just the filing index.
    All financial information MUST be obtained directly from SEC filings using this tool,
    not from other sources. This tool should be called whenever financial data is needed.

    HOW TO USE THIS TOOL:
    1. First, find the filing URL using the find_filings tool
    2. Call this tool with the filing URL
    3. The tool will extract the text of the filing and return it
    4. YOU (the agent) should analyze the text and identify important information:
       - Key financial metrics (revenue, profit, margins, etc.)
       - Growth trends and year-over-year changes
       - Important business developments
       - Risk factors and challenges
       - Management's outlook and guidance
    5. Create a comprehensive summary focusing on the most relevant information

    EXAMPLE:
    ```
    # Find Apple's CIK
    apple_results = find_cik("Apple")
    apple_cik = apple_results[0]["CIK"]

    # Find Apple's most recent 10-K filing
    apple_filings = find_filings(apple_cik, "10-K", 1)
    filing_url = apple_filings[0]["link"]

    # Extract the filing text
    filing_text = summarize_filing(filing_url, 0, 200000)

    # Now YOU (the agent) should analyze the text and create a summary
    # highlighting the most important information
    ```

    Args:
        filing_url (str): The URL of the SEC filing
        chunk_index (int): Index of the chunk to return (0-based). Use -1 to get information about total chunks.
        max_chunk_size (int): Maximum size of each chunk in characters.

    Returns:
        str: A chunk of the filing text, or information about the total number of chunks
    """
    # Extract the text content from the filing
    filing_text = extract_filing_text(filing_url)

    # Calculate the total number of chunks
    total_length = len(filing_text)
    total_chunks = (total_length + max_chunk_size - 1) // max_chunk_size  # Ceiling division

    # If chunk_index is -1, return information about the total number of chunks
    if chunk_index == -1:
        return f"Filing has {total_chunks} chunks. Use chunk_index=0 to {total_chunks-1} to retrieve specific chunks."

    # Validate chunk_index
    if chunk_index < 0 or chunk_index >= total_chunks:
        return f"Invalid chunk_index. Filing has {total_chunks} chunks. Use chunk_index=0 to {total_chunks-1}."

    # Calculate the start and end positions for the requested chunk
    start_pos = chunk_index * max_chunk_size
    end_pos = min(start_pos + max_chunk_size, total_length)

    # Extract the requested chunk
    chunk_text = filing_text[start_pos:end_pos]

    # Add information about the chunk
    chunk_info = f"[Chunk {chunk_index+1} of {total_chunks}] "

    # Return the chunk with information
    return chunk_info + chunk_text

def analyze_filing(filing_text: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Analyze the content of an SEC filing by extracting information and generating a summary.

    This function is a wrapper around the extract_filing_information and summarize_filing_information
    functions. It extracts structured information from the filing text and then generates a
    comprehensive summary focusing on the most relevant information for investors or researchers.

    Args:
        filing_text (str): The text content of the filing
        keywords (list, optional): A list of keywords to search for in the filing

    Returns:
        dict: A dictionary containing comprehensive analysis results including:
            - summary: A summary of key findings
            - extracted_info: The extracted information from the filing
            - keyword_context: Keywords with surrounding context (if keywords provided)
    """
    # Extract information from the filing
    extracted_info = extract_filing_information(filing_text, keywords)

    # Generate a summary from the extracted information
    result = summarize_filing_information(extracted_info)

    # Ensure the result includes the keyword_context from extracted_info
    if 'keyword_context' not in result and 'keyword_context' in extracted_info:
        result['keyword_context'] = extracted_info['keyword_context']
    elif 'keyword_context' not in result:
        # If no keyword_context is available, create an empty one
        result['keyword_context'] = {}

    # Return the analysis result
    return result
