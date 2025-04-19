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
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import re

# Import configuration
from filingsResearch.config import Config

def search_investor_meetings(company_name: str, ticker_symbol: Optional[str] = None, count: int = 5, specific_date: Optional[str] = None, reference: Optional[str] = None) -> List[Dict[str, Any]]:
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
        ticker_symbol (Optional[str], optional): The ticker symbol for the company (e.g., "AAPL", "MSFT").
                                               If provided, this will be used instead of trying to derive
                                               a ticker from the company name. Defaults to None.
        count (int, optional): The number of results to return. Defaults to 5.
        specific_date (Optional[str], optional): A specific date to search for in format YYYY-MM-DD 
                                               (e.g., "2023-05-04"). Defaults to None.
        reference (Optional[str], optional): A reference to a specific meeting mentioned elsewhere.
                                           Can be a quarter (e.g., "Q1 2023", "first quarter 2023") 
                                           or a month (e.g., "January 2023"). Defaults to None.

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
        meetings = search_investor_meetings(company_name="Apple")

        # Search for Microsoft investor meetings using ticker symbol
        meetings = search_investor_meetings(company_name="Microsoft", ticker_symbol="MSFT", count=3)

        # Search for a specific Tesla earnings call from Q1 2023
        meetings = search_investor_meetings(company_name="Tesla", ticker_symbol="TSLA", reference="Q1 2023")

        # Search for a specific Apple earnings call on May 4, 2023
        meetings = search_investor_meetings(company_name="Apple", ticker_symbol="AAPL", specific_date="2023-05-04")
    """
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

        # Make the API request
        response = requests.get(api_url, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve earnings data: Status code {response.status_code}")

        # Try to parse the response as JSON first
        try:
            data = response.json()

            # Check if we have valid JSON data with earnings
            if not data or "earnings" not in data:
                # If not, we'll try parsing as CSV below
                raise ValueError("No earnings data in JSON response")

        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, try to parse as CSV
            # Alpha Vantage often returns CSV for EARNINGS_CALENDAR
            try:
                # Get the raw text response
                csv_data = response.text.strip()

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

                overview_response = requests.get(api_url, params=params)
                if overview_response.status_code != 200:
                    raise ValueError(f"No earnings data found for {ticker}")

                overview_data = overview_response.json()
                if not overview_data or "Name" not in overview_data:
                    raise ValueError(f"No company information found for {ticker}")

                # Now try to get earnings calendar for the confirmed ticker
                params = {
                    "function": "EARNINGS_CALENDAR",
                    "symbol": ticker,
                    "apikey": api_key
                }

                response = requests.get(api_url, params=params)
                if response.status_code != 200:
                    raise ValueError(f"Failed to retrieve earnings data: Status code {response.status_code}")

                # Try parsing the new response as CSV
                try:
                    csv_data = response.text.strip()
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

        # Filter by specific date if provided
        if specific_date:
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

            # If we found date information, filter earnings data by those dates
            if extracted_dates:
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
                "url": f"https://www.alphavantage.co/earnings/{ticker}/{formatted_date}",
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
        meetings = search_investor_meetings(company_name="Apple")

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
            url_parts = meeting_info["url"].split("/")
            if len(url_parts) > 4:
                ticker = url_parts[4]

        if not ticker:
            return "Error: Ticker symbol is required to retrieve transcript."

        date_str = meeting_info.get("date", "")
        title = meeting_info.get("title", f"{ticker} Earnings Call on {date_str}")
        meeting_type = meeting_info.get("type", "Earnings Call")

        # Extract quarter information from the date or title
        quarter = None

        # Try to extract quarter from title first (e.g., "Q1 2023", "Q2 2023")
        quarter_match = re.search(r'Q([1-4])\s+(\d{4})', title)
        if quarter_match:
            q_num = quarter_match.group(1)
            year = quarter_match.group(2)
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
                    quarter = f"{year}Q{q_num}"
                except ValueError:
                    # If date parsing fails, we'll continue without a quarter
                    pass

        if not quarter:
            # If we couldn't extract a quarter, return an error message
            return f"""
# Transcript Information for {title}

## Meeting Details
- **Company**: {ticker}
- **Date**: {date_str}
- **Type**: {meeting_type}

## Error: Could not determine quarter
The Alpha Vantage EARNINGS_CALL_TRANSCRIPT API requires a quarter in YYYYQM format (e.g., 2024Q1).
Could not extract quarter information from the meeting date or title.
Please try again with a meeting that has a clear quarter reference in the title or a valid date.
"""

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

        # Make the API request
        response = requests.get(api_url, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            return f"Error: Failed to retrieve transcript. Status code: {response.status_code}"

        # Parse the JSON response
        data = response.json()

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

def summarize_transcript(transcript_text: str) -> Dict[str, Any]:
    """
    Summarize the key information from a transcript.

    This function analyzes the transcript text to extract key financial highlights,
    strategic initiatives, future outlook, and important quotes. It primarily uses
    an LLM (Google's Gemini model) to generate the summary, with minimal regex for 
    error handling and meeting type detection. The function processes the transcript
    to identify the type of meeting, extract key financial metrics, highlight strategic
    initiatives, capture management's outlook, and identify important quotes from executives.

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
        meetings = search_investor_meetings(company_name="Apple")

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
    summary = {
        "meeting_type": "",
        "financial_highlights": [],
        "strategic_initiatives": [],
        "outlook": [],
        "key_quotes": [],
        "full_summary": ""
    }

    # Check if we have an error message instead of a transcript
    if transcript_text.startswith("Error retrieving transcript:") or transcript_text.startswith("No transcript content found"):
        summary["meeting_type"] = "Error"
        summary["financial_highlights"].append("Unable to retrieve transcript content.")
        summary["strategic_initiatives"].append("Unable to retrieve transcript content.")
        summary["outlook"].append("Unable to retrieve transcript content.")
        summary["key_quotes"].append(transcript_text)
        summary["full_summary"] = f"Error: {transcript_text}"
        return summary

    # Use regex only to determine meeting type
    if "earnings call" in transcript_text.lower() or "q1" in transcript_text.lower() or "q2" in transcript_text.lower() or "q3" in transcript_text.lower() or "q4" in transcript_text.lower():
        summary["meeting_type"] = "Earnings Call"
    elif "investor day" in transcript_text.lower():
        summary["meeting_type"] = "Investor Day"
    elif "annual meeting" in transcript_text.lower() or "shareholder meeting" in transcript_text.lower():
        summary["meeting_type"] = "Annual Shareholder Meeting"
    else:
        summary["meeting_type"] = "Investor Meeting"

    # Use LLM to generate the summary
    try:
        # Import the necessary modules
        from google.adk.models.llm import Llm
        from google.adk.models.llm_factory import LlmFactory

        # Create an LLM instance
        llm = LlmFactory.create_llm(model="gemini-2.0-flash")

        # Truncate the transcript if it's too long (to avoid token limits)
        max_length = 30000  # Adjust based on model token limits
        truncated_transcript = transcript_text[:max_length] if len(transcript_text) > max_length else transcript_text

        # Create prompts for each section of the summary
        financial_prompt = f"""
        Analyze the following transcript and extract the key financial highlights.
        Focus on information about revenue, growth, margins, profit, earnings, EPS, and other financial metrics.
        Format your response as a list of bullet points, with each point being a concise statement about a financial highlight.

        Transcript:
        {truncated_transcript}
        """

        strategic_prompt = f"""
        Analyze the following transcript and extract the key strategic initiatives mentioned.
        Focus on information about strategy, initiatives, investments, expansions, acquisitions, innovations, developments, launches, and partnerships.
        Format your response as a list of bullet points, with each point being a concise statement about a strategic initiative.

        Transcript:
        {truncated_transcript}
        """

        outlook_prompt = f"""
        Analyze the following transcript and extract information about the company's future outlook.
        Focus on information about guidance, outlook, forecasts, future plans, and expectations.
        Format your response as a list of bullet points, with each point being a concise statement about the company's outlook.

        Transcript:
        {truncated_transcript}
        """

        quotes_prompt = f"""
        Analyze the following transcript and extract important quotes from executives.
        Focus on statements from the CEO, CFO, President, Chairman, and other key executives.
        Format your response as a list of bullet points, with each point being a direct quote attributed to the speaker.

        Transcript:
        {truncated_transcript}
        """

        # Generate summaries for each section
        financial_response = llm.generate_content(financial_prompt)
        strategic_response = llm.generate_content(strategic_prompt)
        outlook_response = llm.generate_content(outlook_prompt)
        quotes_response = llm.generate_content(quotes_prompt)

        # Process the responses
        financial_text = financial_response.text if hasattr(financial_response, 'text') else str(financial_response)
        strategic_text = strategic_response.text if hasattr(strategic_response, 'text') else str(strategic_response)
        outlook_text = outlook_response.text if hasattr(outlook_response, 'text') else str(outlook_response)
        quotes_text = quotes_response.text if hasattr(quotes_response, 'text') else str(quotes_response)

        # Convert bullet points to list items
        summary["financial_highlights"] = [line.strip().lstrip('•-*').strip() for line in financial_text.split('\n') if line.strip() and not line.strip().startswith('#')]
        summary["strategic_initiatives"] = [line.strip().lstrip('•-*').strip() for line in strategic_text.split('\n') if line.strip() and not line.strip().startswith('#')]
        summary["outlook"] = [line.strip().lstrip('•-*').strip() for line in outlook_text.split('\n') if line.strip() and not line.strip().startswith('#')]
        summary["key_quotes"] = [line.strip().lstrip('•-*').strip() for line in quotes_text.split('\n') if line.strip() and not line.strip().startswith('#')]

        # Filter out empty items
        summary["financial_highlights"] = [item for item in summary["financial_highlights"] if item]
        summary["strategic_initiatives"] = [item for item in summary["strategic_initiatives"] if item]
        summary["outlook"] = [item for item in summary["outlook"] if item]
        summary["key_quotes"] = [item for item in summary["key_quotes"] if item]

        # Generate full summary
        full_summary_prompt = f"""
        Create a comprehensive summary of the following transcript of a {summary["meeting_type"]}.
        Include key financial highlights, strategic initiatives, future outlook, and important quotes.
        Format your response in a clear, organized manner with sections for each category.

        Transcript:
        {truncated_transcript}
        """

        full_summary_response = llm.generate_content(full_summary_prompt)
        full_summary_text = full_summary_response.text if hasattr(full_summary_response, 'text') else str(full_summary_response)

        summary["full_summary"] = full_summary_text

    except Exception as e:
        # Fallback to a simple summary if LLM fails
        print(f"Error using LLM for summarization: {str(e)}")

        # Generate a basic summary from the extracted information
        summary["full_summary"] = f"""
Meeting Type: {summary["meeting_type"]}

Financial Highlights:
{"- " + "\n- ".join(summary["financial_highlights"]) if summary["financial_highlights"] else "No specific financial highlights extracted."}

Strategic Initiatives:
{"- " + "\n- ".join(summary["strategic_initiatives"]) if summary["strategic_initiatives"] else "No specific strategic initiatives extracted."}

Outlook:
{"- " + "\n- ".join(summary["outlook"]) if summary["outlook"] else "No specific outlook information extracted."}

Key Quotes:
{"- " + "\n- ".join(summary["key_quotes"]) if summary["key_quotes"] else "No key quotes extracted."}

Note: This summary was generated by analyzing the transcript text from Alpha Vantage.
For complete and accurate information, please refer to the full transcript.
"""

    return summary
