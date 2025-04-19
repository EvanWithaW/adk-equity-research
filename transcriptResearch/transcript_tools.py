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

def search_investor_meetings(company_name: str, count: int, specific_date: Optional[str], reference: Optional[str]) -> List[Dict[str, Any]]:
    """
    Search for investor meetings for a given company using the Alpha Vantage API.
    Can search for recent meetings or specific meetings referenced by other sub-agents.

    Args:
        company_name (str): The name of the company to search for
        count (int): The number of results to return.
        specific_date (Optional[str]): A specific date to search for in format YYYY-MM-DD.
        reference (Optional[str]): A reference to a specific meeting mentioned elsewhere.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about investor meetings
    """
    # Try to convert company name to ticker symbol
    # For simplicity, we'll assume the company name might be the ticker or close to it
    ticker = company_name.split()[0].upper()  # Just take the first word and uppercase it

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

        # Parse the response
        data = response.json()

        # Check if we have valid data
        if not data or "earnings" not in data:
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

            data = response.json()
            if not data or "earnings" not in data:
                raise ValueError(f"No earnings data found for {ticker}")

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
    Fetch the full text of a transcript using the Alpha Vantage API.

    Args:
        meeting_info (Dict[str, Any]): Information about the meeting, including ticker and date

    Returns:
        str: The full text of the transcript
    """
    try:
        # Extract the ticker and date from the meeting info
        ticker = meeting_info.get("ticker", "")
        if not ticker and "url" in meeting_info:
            # Try to extract ticker from URL
            url_parts = meeting_info["url"].split("/")
            if len(url_parts) > 4:
                ticker = url_parts[4]

        if not ticker:
            raise ValueError("Ticker symbol is required to fetch transcript")

        date_str = meeting_info.get("date", "")

        print(f"Fetching transcript for {ticker} on {date_str} from Alpha Vantage API...")

        # Get the Alpha Vantage API key
        api_key = Config.get_alpha_vantage_api_key()
        if not api_key:
            raise ValueError("Alpha Vantage API key is required but not found in environment variables.")

        # Alpha Vantage API endpoint for earnings call transcripts
        api_url = f"https://www.alphavantage.co/query"

        # Set up the query parameters
        params = {
            "function": "EARNINGS_TRANSCRIPT",
            "symbol": ticker,
            "apikey": api_key
        }

        if date_str:
            params["date"] = date_str

        # Make the API request
        response = requests.get(api_url, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve transcript: Status code {response.status_code}")

        # Parse the response
        data = response.json()

        # Check if we have valid data
        if not data or "transcript" not in data:
            raise ValueError(f"No transcript data found for {ticker} on {date_str}")

        # Extract the transcript content
        transcript_data = data["transcript"]

        # Combine all parts of the transcript
        transcript_text = ""
        for part in transcript_data:
            speaker = part.get("speaker", "")
            text = part.get("text", "")
            if speaker and text:
                transcript_text += f"{speaker}: {text}\n\n"
            elif text:
                transcript_text += f"{text}\n\n"

        if not transcript_text:
            return f"No transcript content found for {ticker} on {date_str}. The transcript may not be available through the API."

        return transcript_text

    except Exception as e:
        # If there's an error, return an error message
        return f"Error retrieving transcript: {str(e)}"

def summarize_transcript(transcript_text: str) -> Dict[str, Any]:
    """
    Summarize the key information from a transcript.

    This function analyzes the transcript text to extract key financial highlights,
    strategic initiatives, future outlook, and important quotes. It uses pattern
    matching to identify relevant sentences containing key terms.

    Args:
        transcript_text (str): The full text of the transcript

    Returns:
        Dict[str, Any]: A dictionary containing the summarized information
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

    # Determine meeting type
    if "earnings call" in transcript_text.lower() or "q1" in transcript_text.lower() or "q2" in transcript_text.lower() or "q3" in transcript_text.lower() or "q4" in transcript_text.lower():
        summary["meeting_type"] = "Earnings Call"
    elif "investor day" in transcript_text.lower():
        summary["meeting_type"] = "Investor Day"
    elif "annual meeting" in transcript_text.lower() or "shareholder meeting" in transcript_text.lower():
        summary["meeting_type"] = "Annual Shareholder Meeting"
    else:
        summary["meeting_type"] = "Investor Meeting"

    # Look for common financial terms
    financial_terms = ["revenue", "growth", "margin", "profit", "earnings", "EPS", "guidance", 
                      "outlook", "forecast", "dividend", "cash flow", "balance sheet"]

    for term in financial_terms:
        if term in transcript_text.lower():
            # Find the sentence containing the term
            term_index = transcript_text.lower().find(term)
            if term_index != -1:
                # Find the start of the sentence (previous period + 1 or start of text)
                start_index = transcript_text.rfind(".", 0, term_index) + 1
                if start_index == 0:  # No period found, start from beginning
                    start_index = max(0, term_index - 50)  # Start ~50 chars before the term

                # Find the end of the sentence (next period + 1 or end of text)
                end_index = transcript_text.find(".", term_index) + 1
                if end_index == 0:  # No period found, go to end
                    end_index = min(len(transcript_text), term_index + 100)  # Go ~100 chars after the term

                # Extract the sentence and add it to the appropriate category
                sentence = transcript_text[start_index:end_index].strip()

                if term in ["revenue", "growth", "margin", "profit", "earnings", "EPS"]:
                    if sentence not in summary["financial_highlights"]:
                        summary["financial_highlights"].append(sentence)
                elif term in ["guidance", "outlook", "forecast"]:
                    if sentence not in summary["outlook"]:
                        summary["outlook"].append(sentence)

    # Look for strategic terms
    strategic_terms = ["strategy", "initiative", "investment", "expansion", "acquisition", 
                      "innovation", "development", "launch", "partnership"]

    for term in strategic_terms:
        if term in transcript_text.lower():
            # Find the sentence containing the term
            term_index = transcript_text.lower().find(term)
            if term_index != -1:
                # Find the start of the sentence (previous period + 1 or start of text)
                start_index = transcript_text.rfind(".", 0, term_index) + 1
                if start_index == 0:  # No period found, start from beginning
                    start_index = max(0, term_index - 50)  # Start ~50 chars before the term

                # Find the end of the sentence (next period + 1 or end of text)
                end_index = transcript_text.find(".", term_index) + 1
                if end_index == 0:  # No period found, go to end
                    end_index = min(len(transcript_text), term_index + 100)  # Go ~100 chars after the term

                # Extract the sentence and add it to strategic initiatives
                sentence = transcript_text[start_index:end_index].strip()
                if sentence not in summary["strategic_initiatives"]:
                    summary["strategic_initiatives"].append(sentence)

    # Look for key quotes (sentences with executive names or important statements)
    executive_terms = ["ceo", "chief executive", "cfo", "chief financial", "president", "chairman", "director"]

    for term in executive_terms:
        if term in transcript_text.lower():
            # Find the sentence containing the term
            term_index = transcript_text.lower().find(term)
            if term_index != -1:
                # Find the start of the sentence (previous period + 1 or start of text)
                start_index = transcript_text.rfind(".", 0, term_index) + 1
                if start_index == 0:  # No period found, start from beginning
                    start_index = max(0, term_index - 50)  # Start ~50 chars before the term

                # Find the end of the sentence (next period + 1 or end of text)
                end_index = transcript_text.find(".", term_index) + 1
                if end_index == 0:  # No period found, go to end
                    end_index = min(len(transcript_text), term_index + 100)  # Go ~100 chars after the term

                # Extract the sentence and add it to key quotes
                sentence = transcript_text[start_index:end_index].strip()
                if sentence not in summary["key_quotes"]:
                    summary["key_quotes"].append(sentence)

    # Generate full summary
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
