"""
Test script for transcript functions

This script tests the updated transcript functions that use the Alpha Vantage API.
NOTE: You must have a valid ALPHA_VANTAGE_API_KEY in your .env file to run these tests.
"""

import sys
import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Add the parent directory to the path so we can import the transcript_tools module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcriptResearch.transcript_tools import (
    search_investor_meetings,
    get_transcript_text,
    summarize_transcript
)

def test_search_investor_meetings():
    """Test the search_investor_meetings function"""
    print("\n=== Testing search_investor_meetings ===")

    # Test with a valid company name (recent meetings)
    print("\nTesting with 'Apple' (recent meetings):")
    meetings = search_investor_meetings("Apple")
    print(f"Found {len(meetings)} meetings")
    for i, meeting in enumerate(meetings[:2]):  # Show first 2 meetings
        print(f"\nMeeting {i+1}:")
        print(f"Title: {meeting['title']}")
        print(f"Date: {meeting['date']}")
        print(f"Type: {meeting['type']}")
        print(f"URL: {meeting['url']}")
        print(f"Source: {meeting.get('source', 'N/A')}")

    # Save the first meeting date for testing specific_date parameter
    first_meeting_date = None
    if meetings and len(meetings) > 0 and 'date' in meetings[0]:
        first_meeting_date = meetings[0]['date']

    # Test with another company
    print("\nTesting with 'Microsoft' (recent meetings):")
    meetings = search_investor_meetings("Microsoft")
    print(f"Found {len(meetings)} meetings")
    for i, meeting in enumerate(meetings[:2]):  # Show first 2 meetings
        print(f"\nMeeting {i+1}:")
        print(f"Title: {meeting['title']}")
        print(f"Date: {meeting['date']}")
        print(f"Type: {meeting['type']}")
        print(f"URL: {meeting['url']}")
        print(f"Source: {meeting.get('source', 'N/A')}")

    # Test with specific_date parameter
    if first_meeting_date:
        print(f"\nTesting with 'Apple' and specific date '{first_meeting_date}':")
        date_meetings = search_investor_meetings("Apple", specific_date=first_meeting_date)
        print(f"Found {len(date_meetings)} meetings")
        for i, meeting in enumerate(date_meetings[:2]):  # Show first 2 meetings
            print(f"\nMeeting {i+1}:")
            print(f"Title: {meeting['title']}")
            print(f"Date: {meeting['date']}")
            print(f"Type: {meeting['type']}")
            print(f"URL: {meeting['url']}")
            print(f"Source: {meeting.get('source', 'N/A')}")

    # Test with reference parameter
    print("\nTesting with 'Apple' and reference 'Q1 2023':")
    reference_meetings = search_investor_meetings("Apple", reference="Q1 2023")
    print(f"Found {len(reference_meetings)} meetings")
    for i, meeting in enumerate(reference_meetings[:2]):  # Show first 2 meetings
        print(f"\nMeeting {i+1}:")
        print(f"Title: {meeting['title']}")
        print(f"Date: {meeting['date']}")
        print(f"Type: {meeting['type']}")
        print(f"URL: {meeting['url']}")
        print(f"Source: {meeting.get('source', 'N/A')}")

def test_get_transcript_text():
    """Test the get_transcript_text function"""
    print("\n=== Testing get_transcript_text ===")

    # First, get some meeting info from the search function
    print("\nSearching for Apple meetings...")
    apple_meetings = search_investor_meetings("Apple", 2)

    if apple_meetings and len(apple_meetings) > 0:
        # Test with a valid meeting info from the search results
        meeting_info = apple_meetings[0]
        print(f"\nTesting with meeting: {meeting_info['title']} on {meeting_info['date']}")
        transcript = get_transcript_text(meeting_info)
        print("Transcript excerpt:")
        print(transcript[:500] + "...\n" if len(transcript) > 500 else transcript)
    else:
        print("\nCould not find Apple meetings. Skipping transcript text test.")

    # Test with a manually created meeting info with explicit quarter information
    print("\nTesting with manually created meeting info (explicit quarter):")
    manual_meeting_info = {
        "ticker": "AAPL",
        "date": "2023-05-04",
        "title": "Apple Q2 2023 Earnings Call",
        "type": "Earnings Call",
        "source": "Alpha Vantage"
    }
    transcript = get_transcript_text(manual_meeting_info)
    print("Transcript excerpt:")
    print(transcript[:500] + "...\n" if len(transcript) > 500 else transcript)

    # Test with a manually created meeting info for a recent quarter
    print("\nTesting with manually created meeting info (recent quarter):")
    # Get the current date
    from datetime import datetime
    current_date = datetime.now()
    # Calculate the current quarter
    current_quarter = ((current_date.month - 1) // 3) + 1
    current_year = current_date.year

    # Test with IBM which is mentioned in the API documentation
    manual_meeting_info_ibm = {
        "ticker": "IBM",
        "date": current_date.strftime("%Y-%m-%d"),
        "title": f"IBM Q{current_quarter} {current_year} Earnings Call",
        "type": "Earnings Call",
        "source": "Alpha Vantage"
    }
    transcript = get_transcript_text(manual_meeting_info_ibm)
    print("Transcript excerpt:")
    print(transcript[:500] + "...\n" if len(transcript) > 500 else transcript)

    # Test with a meeting info that doesn't have quarter information
    print("\nTesting with meeting info without quarter information:")
    no_quarter_info = {
        "ticker": "MSFT",
        "date": "2023-07-15",  # This date should map to Q3
        "title": "Microsoft Earnings Call",  # No quarter information in the title
        "type": "Earnings Call",
        "source": "Alpha Vantage"
    }
    transcript = get_transcript_text(no_quarter_info)
    print("Transcript excerpt:")
    print(transcript[:500] + "...\n" if len(transcript) > 500 else transcript)

def test_summarize_transcript():
    """Test the summarize_transcript function"""
    print("\n=== Testing summarize_transcript ===")

    # Test with a transcript location (not actual content)
    print("\nTesting with transcript location information:")
    transcript_location = """
Transcript for AAPL can be found at https://seekingalpha.com/symbol/AAPL/earnings/transcripts

Note: This is a real URL where you can find actual earnings call transcripts for AAPL.
To access the full transcript, you would need to:
1. Visit the URL above
2. Select the specific earnings call you're interested in
3. Register for a Seeking Alpha account if required
"""
    summary = summarize_transcript(transcript_location)
    print(f"Meeting Type: {summary['meeting_type']}")
    print(f"Financial Highlights: {summary['financial_highlights']}")
    print(f"Strategic Initiatives: {summary['strategic_initiatives']}")
    print(f"Outlook: {summary['outlook']}")
    print(f"Key Quotes: {summary['key_quotes']}")

    # Test with some actual transcript content
    print("\nTesting with some actual transcript content:")
    transcript_content = """
Apple Q2 2023 Earnings Call Transcript

Tim Cook: We're pleased to report revenue of $94.8 billion for the March quarter. We set an all-time record in Services and a March quarter record for iPhone. Our installed base of active devices reached an all-time high in all geographic segments.

Luca Maestri: Our revenue for the March quarter was $94.8 billion, down 3% year-over-year. Products revenue was $73.9 billion, down 5% from the year-ago quarter due to foreign exchange headwinds and challenging macroeconomic conditions.

Tim Cook: Looking ahead, we expect our June quarter year-over-year revenue performance to be similar to the March quarter. We expect Services to grow double digits. We remain focused on investing in our long-term growth plans.

We're excited about our product pipeline and continue to invest in innovation, in new and emerging markets, and in our installed base growth.
"""
    summary = summarize_transcript(transcript_content)
    print(f"Meeting Type: {summary['meeting_type']}")
    print(f"Financial Highlights: {summary['financial_highlights']}")
    print(f"Strategic Initiatives: {summary['strategic_initiatives']}")
    print(f"Outlook: {summary['outlook']}")

def check_api_key():
    """Check if the Alpha Vantage API key is set"""
    from filingsResearch.config import Config

    api_key = Config.get_alpha_vantage_api_key()
    if not api_key:
        print("\n⚠️ WARNING: ALPHA_VANTAGE_API_KEY is not set in your environment variables.")
        print("These tests will fail without a valid API key.")
        print("Please set the ALPHA_VANTAGE_API_KEY in your .env file and try again.")
        return False
    return True

def main():
    """Run all tests"""
    if not check_api_key():
        return

    test_search_investor_meetings()
    test_get_transcript_text()
    test_summarize_transcript()

    print("\n=== All tests completed ===")

if __name__ == "__main__":
    main()
