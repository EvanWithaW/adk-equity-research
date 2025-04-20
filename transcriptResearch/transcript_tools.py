"""
Transcript Tools

This module provides tools for retrieving and summarizing investor meeting transcripts.
The tools can:
1. Search for recent investor meetings for a company
2. Retrieve the full text of meeting transcripts using the Alpha Vantage API
3. Summarize key information from transcripts

These tools are used by the transcript_summarization_agent.
"""

import requests
from typing import List, Dict, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import json
import re
import time
import random

# Import configuration
from filingsResearch.config import Config

# Rate limiting parameters
MAX_RETRIES = 7
INITIAL_DELAY = 2.0
BACKOFF_FACTOR = 2.0
JITTER_FACTOR = 0.1

def make_api_request_with_retry(url: str, params: Dict[str, str] = None) -> Tuple[bool, Union[Dict, str]]:
    """
    Make an API request with retry logic for rate limiting and network errors.

    Args:
        url (str): The API endpoint URL, may already include query parameters
        params (Dict[str, str], optional): The query parameters for the request. 
                                         If None or empty, assumes parameters are already in the URL.

    Returns:
        Tuple[bool, Union[Dict, str]]: A tuple containing:
            - bool: True if the request was successful, False otherwise
            - Union[Dict, str]: The response data if successful, or an error message if not
    """
    retry_count = 0
    delay = INITIAL_DELAY

    while True:
        try:
            # Make the API request
            if params:
                response = requests.get(url, params=params)
            else:
                response = requests.get(url)

            # Check if the request was successful
            if response.status_code != 200:
                # Check if this is a rate limiting error (status code 429)
                if response.status_code == 429:
                    # If we've reached the maximum number of retries, return an error
                    if retry_count >= MAX_RETRIES:
                        return False, f"Rate limit exceeded after {MAX_RETRIES} retries. Please try again later."

                    # Extract retry delay from response headers if available
                    retry_delay = None
                    if 'Retry-After' in response.headers:
                        retry_delay = int(response.headers['Retry-After'])

                    # Calculate delay with jitter
                    if retry_delay:
                        actual_delay = retry_delay
                    else:
                        actual_delay = delay * (1 + random.random() * JITTER_FACTOR)

                    print(f"Rate limit exceeded. Waiting {actual_delay:.1f} seconds before retrying (attempt {retry_count + 1}/{MAX_RETRIES})...")

                    # Wait before retrying
                    time.sleep(actual_delay)

                    # Increase delay for next retry using exponential backoff
                    delay *= BACKOFF_FACTOR
                    retry_count += 1
                    continue
                else:
                    # For other status codes, return an error
                    return False, f"Failed to retrieve data: Status code {response.status_code}"

            # Try to parse the response as JSON
            try:
                data = response.json()
                return True, data
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                return True, response.text

        except requests.exceptions.RequestException as e:
            # If we've reached the maximum number of retries, return an error
            if retry_count >= MAX_RETRIES:
                return False, f"Network error persisted after {MAX_RETRIES} retries: {str(e)}"

            # Calculate delay with jitter
            actual_delay = delay * (1 + random.random() * JITTER_FACTOR)

            print(f"Network error detected: {type(e).__name__}. Waiting {actual_delay:.1f} seconds before retrying (attempt {retry_count + 1}/{MAX_RETRIES})...")

            # Wait before retrying
            time.sleep(actual_delay)

            # Increase delay for next retry using exponential backoff
            delay *= BACKOFF_FACTOR
            retry_count += 1
            continue

def search_investor_meetings(company_name: str, ticker_symbol: Optional[str] = None, count: Optional[int] = None, specific_date: Optional[str] = None, reference: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for investor meetings for a given company using the Alpha Vantage API.
    Can search for recent meetings or specific meetings referenced by other sub-agents.

    This function attempts to find investor meetings (primarily earnings calls) for the specified company.
    It uses the provided ticker_symbol if available, or tries to derive a ticker from the company_name,
    then queries the Alpha Vantage API to find earnings calls and other investor meetings.
    The function can filter results by date or by a reference to a specific meeting 
    (like "Q1 2023" or "first quarter 2023").

    Args:
        company_name (str): The name of the company to search for (e.g., "Apple", "Microsoft", "Tesla").
                           This is a required parameter.
        ticker_symbol (Optional[str]): The ticker symbol for the company (e.g., "AAPL", "MSFT").
                                     If provided, this will be used instead of trying to derive
                                     a ticker from the company name. If None, will derive from company_name.
        count (int): The number of results to return. If None, defaults to 5.
        specific_date (Optional[str]): A specific date to search for in format YYYY-MM-DD 
                                     (e.g., "2023-05-04"). If None, no date filtering is applied.
        reference (Optional[str]): A reference to a specific meeting mentioned elsewhere.
                                 Can be a quarter (e.g., "Q1 2023", "first quarter 2023") 
                                 or a month (e.g., "January 2023"). If None, no reference filtering is applied.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about investor meetings.
                             Each dictionary contains the following keys:
                             - id: A unique identifier for the meeting
                             - title: The title of the meeting (e.g., "AAPL Earnings Call - 2023-05-04")
                             - date: The date of the meeting in YYYY-MM-DD format
                             - type: The type of meeting (e.g., "Earnings Call", "Investor Day")
                             - url: A URL to access the meeting transcript
                             - source: The source of the meeting information (e.g., "Alpha Vantage")
                             - ticker: The ticker symbol for the company

    Examples:
        # Search for recent investor meetings for Apple using company name only
        meetings = search_investor_meetings(company_name="Apple", ticker_symbol=None, count=20, specific_date=None, reference=None)

        # Search for Microsoft investor meetings using ticker symbol
        meetings = search_investor_meetings(company_name="Microsoft", ticker_symbol="MSFT", count=3, specific_date=None, reference=None)

        # Search for a specific Tesla earnings call from Q1 2023
        meetings = search_investor_meetings(company_name="Tesla", ticker_symbol="TSLA", count=20, specific_date=None, reference="Q1 2023")

        # Search for a specific Apple earnings call on May 4, 2023
        meetings = search_investor_meetings(company_name="Apple", ticker_symbol="AAPL", count=20, specific_date="2023-05-04", reference=None)
    """
    # Set default values for parameters if they are None
    if count is None:
        count = 20  # Increased from 5 to ensure we get all relevant/recent meetings

    # Use the provided ticker_symbol if available, otherwise try to derive one from the company_name
    if ticker_symbol:
        ticker = ticker_symbol.strip().upper()
    else:
        # For simplicity, we'll assume the company name might be the ticker or close to it
        # Just take the first word and uppercase it
        ticker = company_name.split()[0].upper()

    try:
        print(f"Searching for investor meetings for {company_name} (ticker: {ticker})...")

        # Get the Alpha Vantage API key
        api_key = Config.get_alpha_vantage_api_key()
        if not api_key:
            raise ValueError("Alpha Vantage API key is required but not found in environment variables.")

        # Alpha Vantage API endpoint for earnings
        api_url = f"https://www.alphavantage.co/query"

        # Set up the query parameters
        params = {
            "function": "EARNINGS_CALENDAR",
            "symbol": ticker,
            "apikey": api_key
        }

        # Make the API request with retry logic
        success, response_data = make_api_request_with_retry(api_url, params)

        # Check if the request was successful
        if not success:
            raise ValueError(f"Failed to retrieve earnings data: {response_data}")

        # Try to parse the response as JSON first
        try:
            # If response_data is already a dictionary, use it directly
            if isinstance(response_data, dict):
                data = response_data
            else:
                # Otherwise, try to parse it as JSON
                data = json.loads(response_data) if isinstance(response_data, str) else {}

            # Check if we have valid JSON data with earnings
            if not data or "earnings" not in data:
                # If not, we'll try parsing as CSV below
                raise ValueError("No earnings data in JSON response")

        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, try to parse as CSV
            # Alpha Vantage often returns CSV for EARNINGS_CALENDAR
            try:
                # Get the raw text response
                csv_data = response_data.strip() if isinstance(response_data, str) else ""

                # Check if we have any data
                if not csv_data:
                    raise ValueError(f"Empty response for {ticker}")

                # Split into lines and check if we have more than just headers
                lines = csv_data.split('\n')
                if len(lines) <= 1:
                    raise ValueError(f"No earnings data found for {ticker} (CSV format)")

                # Parse the CSV data
                headers = lines[0].split(',')

                # Clean up headers (remove any trailing \r)
                headers = [h.strip().rstrip('\r') for h in headers]

                # Create earnings data from CSV
                earnings_data = []
                for i in range(1, len(lines)):
                    row = lines[i].split(',')
                    if len(row) == len(headers):
                        earnings_dict = {headers[j]: row[j].strip() for j in range(len(headers))}
                        earnings_data.append(earnings_dict)

                # Create a data structure similar to what we'd expect from JSON
                data = {"earnings": earnings_data}

                # If we have no earnings data, try the fallback approach
                if not earnings_data:
                    raise ValueError(f"No earnings data found for {ticker} (CSV format)")

            except Exception as csv_error:
                # If CSV parsing also fails, try the fallback approach with OVERVIEW
                print(f"Failed to parse earnings data as CSV: {str(csv_error)}")
                print("Trying fallback approach with OVERVIEW endpoint...")

                # Try another approach - get company overview first
                params = {
                    "function": "OVERVIEW",
                    "symbol": ticker,
                    "apikey": api_key
                }

                # Make the API request with retry logic
                overview_success, overview_response_data = make_api_request_with_retry(api_url, params)

                # Check if the request was successful
                if not overview_success:
                    raise ValueError(f"No earnings data found for {ticker}: {overview_response_data}")

                # Parse the response data
                if isinstance(overview_response_data, dict):
                    overview_data = overview_response_data
                else:
                    try:
                        overview_data = json.loads(overview_response_data) if isinstance(overview_response_data, str) else {}
                    except json.JSONDecodeError:
                        raise ValueError(f"Failed to parse company information for {ticker}")

                if not overview_data or "Name" not in overview_data:
                    raise ValueError(f"No company information found for {ticker}")

                # Now try to get earnings calendar for the confirmed ticker
                params = {
                    "function": "EARNINGS_CALENDAR",
                    "symbol": ticker,
                    "apikey": api_key
                }

                # Make the API request with retry logic
                success, response_data = make_api_request_with_retry(api_url, params)

                # Check if the request was successful
                if not success:
                    raise ValueError(f"Failed to retrieve earnings data: {response_data}")

                # Try parsing the new response as CSV
                try:
                    # If response_data is already a dictionary, convert it to string for CSV parsing
                    if isinstance(response_data, dict):
                        csv_data = json.dumps(response_data).strip()
                    else:
                        csv_data = response_data.strip() if isinstance(response_data, str) else ""
                    lines = csv_data.split('\n')
                    if len(lines) <= 1:
                        raise ValueError(f"No earnings data found for {ticker} (CSV format)")

                    headers = [h.strip().rstrip('\r') for h in lines[0].split(',')]
                    earnings_data = []
                    for i in range(1, len(lines)):
                        row = lines[i].split(',')
                        if len(row) == len(headers):
                            earnings_dict = {headers[j]: row[j].strip() for j in range(len(headers))}
                            earnings_data.append(earnings_dict)

                    data = {"earnings": earnings_data}

                    if not earnings_data:
                        raise ValueError(f"No earnings data found for {ticker} (CSV format)")

                except Exception:
                    # If all attempts fail, raise an error
                    raise ValueError(f"No earnings data found for {ticker} after multiple attempts")

        # Extract the earnings data
        earnings_data = data["earnings"]  # Get all earnings data

        # Check if specific_date is in the future
        if specific_date:
            try:
                specific_date_obj = datetime.strptime(specific_date, "%Y-%m-%d")
                current_date = datetime.now()

                # If the date is in the future, return a message
                if specific_date_obj > current_date:
                    return [{
                        "id": "future_date",
                        "title": f"Future date requested for {company_name}",
                        "date": specific_date,
                        "type": "Information",
                        "url": f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}",
                        "source": "Alpha Vantage",
                        "message": f"The requested date ({specific_date}) is in the future. Earnings call transcripts are only available for past events. Please try a date that has already occurred."
                    }]

                # If the date is not in the future, filter by it
                earnings_data = [e for e in earnings_data if e.get("reportedDate", "") == specific_date]
            except ValueError:
                # If the date format is invalid, just try to filter as before
                earnings_data = [e for e in earnings_data if e.get("reportedDate", "") == specific_date]

        # Filter by reference if provided (simple text matching)
        if reference:
            # Convert reference to lowercase for case-insensitive matching
            reference_lower = reference.lower()
            # Try to extract dates or quarters from the reference
            # Look for patterns like "Q1 2023", "first quarter 2023", "January 2023", etc.
            import re

            # Match quarter patterns (Q1 2023, first quarter 2023, etc.)
            quarter_patterns = [
                r'q(\d)\s+(\d{4})',  # Q1 2023
                r'(first|second|third|fourth)\s+quarter\s+(\d{4})'  # first quarter 2023
            ]

            # Match month patterns (January 2023, Jan 2023, etc.)
            month_patterns = [
                r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})'
            ]

            # Try to extract date information from the reference
            extracted_dates = []

            # Check for quarter patterns
            for pattern in quarter_patterns:
                matches = re.findall(pattern, reference_lower)
                for match in matches:
                    if len(match) == 2:
                        quarter = match[0]
                        year = match[1]
                        # Convert quarter to month range
                        if quarter == '1' or quarter == 'first':
                            extracted_dates.extend([f"{year}-01", f"{year}-02", f"{year}-03"])
                        elif quarter == '2' or quarter == 'second':
                            extracted_dates.extend([f"{year}-04", f"{year}-05", f"{year}-06"])
                        elif quarter == '3' or quarter == 'third':
                            extracted_dates.extend([f"{year}-07", f"{year}-08", f"{year}-09"])
                        elif quarter == '4' or quarter == 'fourth':
                            extracted_dates.extend([f"{year}-10", f"{year}-11", f"{year}-12"])

            # Check for month patterns
            for pattern in month_patterns:
                matches = re.findall(pattern, reference_lower)
                for match in matches:
                    if len(match) == 2:
                        month = match[0]
                        year = match[1]
                        # Convert month name to month number
                        month_dict = {
                            'january': '01', 'jan': '01',
                            'february': '02', 'feb': '02',
                            'march': '03', 'mar': '03',
                            'april': '04', 'apr': '04',
                            'may': '05',
                            'june': '06', 'jun': '06',
                            'july': '07', 'jul': '07',
                            'august': '08', 'aug': '08',
                            'september': '09', 'sep': '09',
                            'october': '10', 'oct': '10',
                            'november': '11', 'nov': '11',
                            'december': '12', 'dec': '12'
                        }
                        if month in month_dict:
                            extracted_dates.append(f"{year}-{month_dict[month]}")

            # If we found date information, check if all dates are in the future
            if extracted_dates:
                # Check if all extracted dates are in the future
                all_future_dates = True
                current_year_month = datetime.now().strftime("%Y-%m")

                for extracted_date in extracted_dates:
                    # Compare with current year and month (YYYY-MM format)
                    if extracted_date <= current_year_month:
                        all_future_dates = False
                        break

                # If all dates are in the future, return a message
                if all_future_dates:
                    future_period = reference
                    return [{
                        "id": "future_date_reference",
                        "title": f"Future period requested for {company_name}",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "Information",
                        "url": f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}",
                        "source": "Alpha Vantage",
                        "message": f"The requested period ({future_period}) is in the future. Earnings call transcripts are only available for past events. Please try a period that has already occurred."
                    }]

                # If not all dates are in the future, filter earnings data by those dates
                filtered_earnings = []
                for e in earnings_data:
                    date_str = e.get("reportedDate", "")
                    if any(date_str.startswith(extracted_date) for extracted_date in extracted_dates):
                        filtered_earnings.append(e)

                # If we found matches, use them; otherwise, keep all earnings data
                if filtered_earnings:
                    earnings_data = filtered_earnings

        # Limit to requested count
        earnings_data = earnings_data[:count]

        # Create a list of meetings
        meetings = []

        for earnings in earnings_data:
            # Extract the relevant information
            date_str = earnings.get("reportedDate", "")

            # Parse the date
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            # Create the meeting object
            meeting = {
                "id": f"{ticker}_{formatted_date}",
                "title": f"{ticker} Earnings Call - {formatted_date}",
                "date": formatted_date,
                "type": "Earnings Call",
                "url": f"https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol={ticker}",
                "source": "Alpha Vantage",
                "ticker": ticker
            }

            meetings.append(meeting)

        # If no meetings were found, return a message
        if not meetings:
            return [{
                "id": "no_meetings",
                "title": f"No recent investor meetings found for {company_name}",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "Information",
                "url": f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}",
                "source": "Alpha Vantage",
                "message": f"No recent investor meetings were found for {company_name} using the Alpha Vantage API."
            }]

        return meetings

    except Exception as e:
        # If there's an error, return a list with a single item explaining the error
        error_meeting = {
            "id": "error",
            "title": f"Error finding meetings for {company_name}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "Error",
            "url": f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}",
            "source": "Alpha Vantage",
            "error": str(e),
            "message": f"An error occurred while searching for investor meetings: {str(e)}"
        }
        return [error_meeting]

def get_transcript_text(meeting_info: Dict[str, Any]) -> str:
    """
    Retrieve the transcript text for an investor meeting using the Alpha Vantage API.

    This function retrieves the complete text of an investor meeting transcript using the
    Alpha Vantage EARNINGS_CALL_TRANSCRIPT API. It extracts the necessary information from
    the meeting_info parameter, formats it for the API call, and returns the transcript text.

    Args:
        meeting_info (Dict[str, Any]): Information about the meeting, including ticker and date.
                                     This should be one of the meeting objects returned by the
                                     search_investor_meetings function. The dictionary should contain
                                     information about the meeting such as ticker, date, and title.

    Returns:
        str: The full text of the transcript if available, or an error message if the transcript
             could not be retrieved.

    Examples:
        # First, search for meetings
        meetings = search_investor_meetings(company_name="Apple", ticker_symbol=None, count=5, specific_date=None, reference=None)

        # Then, get the transcript information for the first meeting
        if meetings and len(meetings) > 0:
            transcript_text = get_transcript_text(meeting_info=meetings[0])
            print(transcript_text)

        # Example with a manually created meeting_info dictionary
        meeting_info = {
            "ticker": "AAPL",
            "date": "2023-05-04",
            "title": "Apple Q2 2023 Earnings Call"
        }
        transcript_text = get_transcript_text(meeting_info=meeting_info)
    """
    try:
        # Extract information from the meeting info
        ticker = meeting_info.get("ticker", "")
        if not ticker and "url" in meeting_info:
            # Try to extract ticker from URL
            url = meeting_info["url"]
            # Check if the URL is in the format with query parameters
            if "?" in url and "symbol=" in url:
                # Extract the ticker from the symbol parameter
                symbol_part = url.split("symbol=")[1]
                # The ticker is everything up to the next & or the end of the string
                ticker = symbol_part.split("&")[0]
            # Also try the old format where ticker is part of the path
            elif len(url.split("/")) > 4:
                url_parts = url.split("/")
                ticker = url_parts[4]

        if not ticker:
            return "Error: Ticker symbol is required to retrieve transcript."

        date_str = meeting_info.get("date", "")
        title = meeting_info.get("title", f"{ticker} Earnings Call on {date_str}")
        meeting_type = meeting_info.get("type", "Earnings Call")

        # Check if quarter is directly provided in meeting_info
        quarter = meeting_info.get("quarter", "")

        # Check if the quarter is in the future (do this check early)
        if quarter and re.match(r'^\d{4}Q[1-4]$', quarter):
            try:
                year_str, q_part = quarter.split('Q')
                year_int = int(year_str)
                q_num_int = int(q_part)
                current_year = datetime.now().year
                current_quarter = ((datetime.now().month - 1) // 3) + 1

                # If the year is in the future, or it's the current year but a future quarter
                if year_int > current_year or (year_int == current_year and q_num_int > current_quarter):
                    return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}
- **Quarter**: {quarter}

## Error: Future Quarter Requested
The requested quarter ({quarter}) is in the future. Earnings call transcripts are only available for past events.
Please try a quarter that has already occurred.
"""
            except (ValueError, IndexError):
                # If parsing fails, we'll continue with the existing quarter
                pass

        # Check if the date is in the future
        if date_str and len(date_str) >= 10:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                current_date = datetime.now()

                # If the date is in the future, return a message
                if date_obj > current_date:
                    return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}

## Error: Future Date Requested
The requested date ({date_str}) is in the future. Earnings call transcripts are only available for past events.
Please try a date that has already occurred.
"""
            except ValueError:
                # If date parsing fails, we'll continue with the existing logic
                pass

        # Extract quarter information from the date or title
        quarter = None

        # Try to extract quarter from title first (e.g., "Q1 2023", "Q2 2023")
        quarter_match = re.search(r'Q([1-4])\s+(\d{4})', title)
        if quarter_match:
            q_num = quarter_match.group(1)
            year = quarter_match.group(2)

            # Check if the quarter is in the future
            try:
                year_int = int(year)
                q_num_int = int(q_num)
                current_year = datetime.now().year
                current_quarter = ((datetime.now().month - 1) // 3) + 1

                # If the year is in the future, or it's the current year but a future quarter
                if year_int > current_year or (year_int == current_year and q_num_int > current_quarter):
                    return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}
- **Quarter**: {year}Q{q_num}

## Error: Future Quarter Requested
The requested quarter (Q{q_num} {year}) is in the future. Earnings call transcripts are only available for past events.
Please try a quarter that has already occurred.
"""
            except ValueError:
                # If parsing fails, continue with the existing logic
                pass

            quarter = f"{year}Q{q_num}"
        else:
            # Try to extract quarter from date (format: YYYY-MM-DD)
            if date_str and len(date_str) >= 10:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    year = date_obj.year
                    month = date_obj.month
                    # Map month to quarter
                    q_num = ((month - 1) // 3) + 1

                    # Check if the quarter is in the future
                    current_date = datetime.now()
                    current_year = current_date.year
                    current_quarter = ((current_date.month - 1) // 3) + 1

                    # If the year is in the future, or it's the current year but a future quarter
                    if year > current_year or (year == current_year and q_num > current_quarter):
                        return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}
- **Quarter**: {year}Q{q_num}

## Error: Future Quarter Requested
The requested quarter (Q{q_num} {year}) is in the future. Earnings call transcripts are only available for past events.
Please try a quarter that has already occurred.
"""

                    quarter = f"{year}Q{q_num}"
                except ValueError:
                    # If date parsing fails, we'll continue without a quarter
                    pass

        # Check if quarter is directly provided in meeting_info
        if not quarter and "quarter" in meeting_info:
            quarter = meeting_info.get("quarter", "")

        if not quarter:
            # If we couldn't extract a quarter, use the most recent completed quarter
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            # Calculate the most recent completed quarter
            recent_quarter = ((current_month - 1) // 3)
            if recent_quarter == 0:  # If we're in Q1, use Q4 of previous year
                year = current_year - 1
                q_num = 4
            else:
                year = current_year
                q_num = recent_quarter

            quarter = f"{year}Q{q_num}"
            print(f"Could not determine quarter from meeting info. Using most recent completed quarter: {quarter}")

        # Check if the quarter is in the future, regardless of how it was determined
        if quarter and re.match(r'^\d{4}Q[1-4]$', quarter):
            try:
                year_str, q_part = quarter.split('Q')
                year_int = int(year_str)
                q_num_int = int(q_part)
                current_year = datetime.now().year
                current_quarter = ((datetime.now().month - 1) // 3) + 1

                # If the year is in the future, or it's the current year but a future quarter
                if year_int > current_year or (year_int == current_year and q_num_int > current_quarter):
                    return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}
- **Quarter**: {quarter}

## Error: Future Quarter Requested
The requested quarter ({quarter}) is in the future. Earnings call transcripts are only available for past events.
Please try a quarter that has already occurred.
"""
            except (ValueError, IndexError):
                # If parsing fails, we'll continue with the existing quarter
                pass

        print(f"Retrieving transcript for {ticker} for {quarter}...")

        # Get the Alpha Vantage API key
        api_key = Config.get_alpha_vantage_api_key()
        if not api_key:
            return "Error: Alpha Vantage API key is required but not found in environment variables."

        # Alpha Vantage API endpoint for earnings call transcripts
        api_url = "https://www.alphavantage.co/query"

        # Set up the query parameters
        params = {
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": ticker,
            "quarter": quarter,
            "apikey": api_key
        }

        # Construct the URL directly with the parameters
        full_url = f"{api_url}?function=EARNINGS_CALL_TRANSCRIPT&symbol={ticker}&quarter={quarter}&apikey={api_key}"

        # Make the API request with retry logic
        success, response_data = make_api_request_with_retry(full_url, None)

        # Check if the request was successful
        if not success:
            return f"Error: Failed to retrieve transcript. {response_data}"

        # Parse the response data
        if isinstance(response_data, dict):
            data = response_data
        else:
            try:
                data = json.loads(response_data) if isinstance(response_data, str) else {}
            except json.JSONDecodeError:
                return f"Error: Failed to parse transcript data. Invalid JSON response."

        # Check if we have valid data
        if not data or "transcript" not in data:
            return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}
- **Quarter**: {quarter}

## Error: No transcript found
The Alpha Vantage API did not return a transcript for this meeting.
This could be because:
1. The transcript is not available in the Alpha Vantage database
2. The quarter format ({quarter}) might not match the actual fiscal quarter
3. The company might use a different ticker symbol in the Alpha Vantage database

Please try a different meeting or check the company's investor relations website for the transcript.
"""

        # Extract the transcript data
        transcript_data = data["transcript"]

        # Format the transcript text
        transcript_text = f"""
# Transcript for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Quarter**: {quarter}
- **Type**: {meeting_type}

## Transcript
"""

        # Add each speaker's part to the transcript
        for entry in transcript_data:
            speaker = entry.get("speaker", "Unknown Speaker")
            text = entry.get("text", "")
            transcript_text += f"\n**{speaker}**: {text}\n"

        return transcript_text

    except Exception as e:
        # If there's an error, return an error message
        return f"Error retrieving transcript: {str(e)}"

def get_most_recent_transcript(company_name: str, ticker_symbol: Optional[str] = None) -> str:
    """
    Get the transcript for the most recent investor meeting for a company.

    This function algorithmically determines the most recent completed quarter based on the current date,
    and tries to retrieve the transcript for that quarter. If that doesn't work, it tries the previous quarter.
    If the quarter is 0, it rolls back the year by 1 and makes the quarter 4.

    Args:
        company_name (str): The name of the company to search for (e.g., "Apple", "Microsoft", "Tesla").
                           This is a required parameter.
        ticker_symbol (Optional[str]): The ticker symbol for the company (e.g., "AAPL", "MSFT").
                                     If provided, this will be used instead of trying to derive
                                     a ticker from the company name. If None, will derive from company_name.

    Returns:
        str: The full text of the transcript for the most recent meeting, or an error message if no
             meetings were found or the transcript could not be retrieved.

    Examples:
        # Get the most recent transcript for Apple
        transcript = get_most_recent_transcript(company_name="Apple", ticker_symbol="AAPL")

        # Get the most recent transcript for Microsoft using only the company name
        transcript = get_most_recent_transcript(company_name="Microsoft")
    """
    try:
        # Use the provided ticker_symbol if available, otherwise try to derive one from the company_name
        if ticker_symbol:
            ticker = ticker_symbol.strip().upper()
        else:
            # For simplicity, we'll assume the company name might be the ticker or close to it
            # Just take the first word and uppercase it
            ticker = company_name.split()[0].upper()

        # Get the current date for reference
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Determine the current quarter based on the month
        # If month is in the first 3 months (1-3), it's quarter 1
        # If month is in the second 3 months (4-6), it's quarter 2
        # If month is in the third 3 months (7-9), it's quarter 3
        # If month is in the fourth 3 months (10-12), it's quarter 4
        current_quarter = ((current_month - 1) // 3) + 1

        # Define a function to try getting a transcript for a specific quarter
        def try_get_transcript_for_quarter(year, quarter):
            quarter_str = f"{year}Q{quarter}"
            print(f"Trying to get transcript for {company_name} ({ticker}) for {quarter_str}...")

            # Get the Alpha Vantage API key
            api_key = Config.get_alpha_vantage_api_key()
            if not api_key:
                return None

            # Alpha Vantage API endpoint for earnings call transcripts
            api_url = "https://www.alphavantage.co/query"

            # Construct the URL directly with the parameters
            full_url = f"{api_url}?function=EARNINGS_CALL_TRANSCRIPT&symbol={ticker}&quarter={quarter_str}&apikey={api_key}"

            # Make the API request with retry logic
            success, response_data = make_api_request_with_retry(full_url, None)

            # Check if the request was successful
            if not success:
                print(f"Error: Failed to retrieve transcript. {response_data}")
                return None

            # Parse the response data
            if isinstance(response_data, dict):
                data = response_data
            else:
                try:
                    data = json.loads(response_data) if isinstance(response_data, str) else {}
                except json.JSONDecodeError:
                    print(f"Error: Failed to parse transcript data. Invalid JSON response.")
                    return None

            # Check if we have valid data
            if not data or "transcript" not in data:
                print(f"No transcript found for {quarter_str}.")
                return None

            # Extract the transcript data
            transcript_data = data["transcript"]

            # Format the transcript text
            transcript_text = f"""
# Transcript for {company_name} Earnings Call - {quarter_str}

## Meeting Details
- **Company**: {ticker}
- **Date**: {year}-{quarter*3-1:02d}-15
- **Quarter**: {quarter_str}
- **Type**: Earnings Call

## Transcript
"""

            # Add each speaker's part to the transcript
            for entry in transcript_data:
                speaker = entry.get("speaker", "Unknown Speaker")
                text = entry.get("text", "")
                transcript_text += f"\n**{speaker}**: {text}\n"

            return transcript_text

        print(f"Attempting to retrieve the most recent transcript for {company_name}...")

        # Try to get the transcript for the current quarter
        year = current_year
        quarter = current_quarter

        # We'll keep trying quarters until we get a hit or reach a reasonable limit
        # (e.g., going back 10 years or 40 quarters)
        max_years_back = 10
        min_year = current_year - max_years_back
        attempted_quarters = []

        # Keep trying quarters until we get a hit or reach the minimum year
        while year >= min_year:
            quarter_str = f"{year}Q{quarter}"
            attempted_quarters.append(quarter_str)

            transcript = try_get_transcript_for_quarter(year, quarter)
            if transcript:
                return transcript

            print(f"No transcript found for {quarter_str}. Trying previous quarter...")

            # Move to the previous quarter
            quarter -= 1

            # If the quarter is 0, roll back the year by 1 and make the quarter 4
            if quarter == 0:
                year -= 1
                quarter = 4

            # If we've tried too many quarters, break to avoid excessive API calls
            if len(attempted_quarters) >= 40:  # 10 years worth of quarters
                break

        # If all attempts fail, return an error message
        return f"""
# No Transcript Found for {company_name}

## Attempted Quarters
{chr(10).join([f"- {q}" for q in attempted_quarters])}

No transcript could be found for any of these quarters. This could be because:
1. The transcripts are not available in the Alpha Vantage database
2. The company might use a different ticker symbol in the Alpha Vantage database
3. The company might not have had earnings calls in these quarters

Please try a different company or check the company's investor relations website for transcripts.
"""

    except Exception as e:
        # If there's an error, return an error message
        return f"Error retrieving the most recent transcript for {company_name}: {str(e)}"

def summarize_transcript(transcript_text: str) -> Dict[str, Any]:
    """
    Summarize the key information from a transcript.

    This function prepares a structure for summarizing transcript text. It provides the 
    transcript text to the transcript_summarization_agent, which uses its LLM capabilities
    to analyze and extract key information. The function is designed to be used as a tool 
    by the agent, which will populate the summary components with extracted information.

    Args:
        transcript_text (str): The full text of the transcript, typically obtained from
                             the get_transcript_text function. This should be the raw
                             transcript text with speaker names and their statements.

    Returns:
        Dict[str, Any]: A dictionary containing the summarized information with the following keys:
                      - meeting_type (str): The type of meeting (e.g., "Earnings Call", "Investor Day")
                      - financial_highlights (List[str]): A list of key financial metrics and trends
                      - strategic_initiatives (List[str]): A list of important business developments and strategic plans
                      - outlook (List[str]): A list of statements about future expectations and guidance
                      - key_quotes (List[str]): A list of important quotes from executives
                      - full_summary (str): A comprehensive summary of the transcript

    Examples:
        # First, search for meetings
        meetings = search_investor_meetings(company_name="Apple", ticker_symbol=None, count=5, specific_date=None, reference=None)

        # Then, get the transcript for the first meeting
        if meetings and len(meetings) > 0:
            transcript = get_transcript_text(meeting_info=meetings[0])

            # Finally, summarize the transcript
            summary = summarize_transcript(transcript_text=transcript)

            # Access specific parts of the summary
            print(f"Meeting Type: {summary['meeting_type']}")
            print("Financial Highlights:")
            for highlight in summary['financial_highlights']:
                print(f"- {highlight}")

            # Or use the full summary
            print(summary['full_summary'])
    """
    # Initialize the summary structure
    summary = {
        "meeting_type": "Earnings Call",  # Default meeting type
        "financial_highlights": [],
        "strategic_initiatives": [],
        "outlook": [],
        "key_quotes": [],
        "full_summary": ""
    }

    # Check if we have an error message instead of a transcript
    if transcript_text.startswith("Error") or "Error:" in transcript_text or "## Error:" in transcript_text or transcript_text.startswith("No transcript content found"):
        summary["meeting_type"] = "Error"
        summary["financial_highlights"].append("Unable to retrieve transcript content.")
        summary["strategic_initiatives"].append("Unable to retrieve transcript content.")
        summary["outlook"].append("Unable to retrieve transcript content.")
        summary["key_quotes"].append(transcript_text)
        summary["full_summary"] = f"Error: {transcript_text}"
        return summary

    # Truncate the transcript if it's too long (to avoid token limits)
    max_length = 30000  # Adjust based on model token limits
    truncated_transcript = transcript_text[:max_length] if len(transcript_text) > max_length else transcript_text

    # Basic meeting type detection (can be refined by the LLM)
    if "earnings call" in truncated_transcript.lower() or "q1" in truncated_transcript.lower() or "q2" in truncated_transcript.lower() or "q3" in truncated_transcript.lower() or "q4" in truncated_transcript.lower():
        summary["meeting_type"] = "Earnings Call"
    elif "investor day" in truncated_transcript.lower():
        summary["meeting_type"] = "Investor Day"
    elif "annual meeting" in truncated_transcript.lower() or "shareholder meeting" in truncated_transcript.lower():
        summary["meeting_type"] = "Annual Shareholder Meeting"
    else:
        summary["meeting_type"] = "Investor Meeting"

    # Provide placeholder content that will be replaced by the LLM's analysis
    # The transcript_summarization_agent will use its LLM capabilities to analyze the transcript
    # and replace these placeholders with actual extracted information
    summary["financial_highlights"] = ["Extracted from transcript by the agent"]
    summary["strategic_initiatives"] = ["Extracted from transcript by the agent"]
    summary["outlook"] = ["Extracted from transcript by the agent"]
    summary["key_quotes"] = ["Extracted from transcript by the agent"]

    # Create a basic summary template
    summary["full_summary"] = f"""
Meeting Type: {summary["meeting_type"]}

This transcript will be analyzed by the LLM to extract:
1. Financial highlights and key metrics
2. Strategic initiatives and business developments
3. Future outlook and guidance
4. Important quotes from executives

The LLM will replace this placeholder with a comprehensive summary.
"""

    return summary
