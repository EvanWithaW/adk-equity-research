"""
Example Usage of Investment Recommendation Agent

This script demonstrates how to use the Investment Recommendation Agent to get
buy/hold/sell recommendations based on SEC filings analysis.

Usage:
    python example_usage.py

This will start an interactive session with the Investment Recommendation Agent where you can
ask questions about companies' SEC filings and get investment recommendations.
"""

import asyncio
import os
import dotenv
from investment_recommendation_agent import create_investment_recommendation_agent, Runner, APP_NAME, USER_ID, SESSION_ID
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import UserContent
from google.genai.errors import ClientError

# Load environment variables from .env file
dotenv.load_dotenv()

# Ensure GOOGLE_API_KEY is set
if not os.environ.get("GOOGLE_API_KEY"):
    # Try to read it directly from .env file
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"\'')
                    os.environ["GOOGLE_API_KEY"] = key
                    break
    except Exception as e:
        print(f"Warning: Could not read GOOGLE_API_KEY from .env file: {e}")
        print("\nPlease set the GOOGLE_API_KEY environment variable by:")
        print("1. Creating a .env file in the project root directory")
        print("2. Adding the line: GOOGLE_API_KEY=your_api_key_here")
        print("3. Restarting the application")
        print("\nYou can obtain a Google API key from https://makersuite.google.com/app/apikey")

async def run_example():
    """
    Run an interactive conversational session with the Investment Recommendation Agent.

    This function creates and runs the Investment Recommendation Agent, allowing you to
    interact with it to get investment recommendations based on SEC filings analysis.
    """
    # No need for filing chunks dictionary anymore
    print("=" * 80)
    print("Investment Recommendation Agent - Conversational Mode")
    print("=" * 80)
    print("This is an interactive session with the Investment Recommendation Agent.")
    print("Try asking questions like:")
    print("  - What is the CIK number for Apple?")
    print("  - Find recent 10-K filings for Apple using its CIK")
    print("  - Analyze Apple's latest 10-K filing and provide a buy/hold/sell recommendation")
    print("  - Should I buy, hold, or sell Tesla stock based on their most recent quarterly report?")
    print("  - Find the CIK for Amazon, then get its recent filings, and give me a recommendation based on the latest one")
    print("\nType 'exit', 'quit', or 'bye' to end the conversation.")
    print("=" * 80)

    try:
        # Create the agent using the simplified function
        agent = create_investment_recommendation_agent()

        # Create a session service
        session_service = InMemorySessionService()

        # Create a runner for the agent
        runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=session_service
        )

        # Create a session using the constants from investment_recommendation_agent
        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

        # Display a welcome message from the agent
        print("\n[Investment-Recommendation-Agent]: Hello! I'm the Investment Recommendation Agent. My primary purpose is to provide BUY, HOLD, or SELL recommendations for stocks based on SEC filings analysis. I leverage the SEC Filings Research Agent to obtain comprehensive summaries of SEC filings, which I then analyze to provide investment recommendations. How can I assist you today?")

        # Start the conversation loop
        while True:
            # Get user input
            user_message = input("\nYou: ")

            # Check if the user wants to exit
            if user_message.lower() in ["exit", "quit", "bye"]:
                print("\n[Investment-Recommendation-Agent]: Thank you for using the Investment Recommendation Agent. Goodbye!")
                break

            # Create a new message from user input
            new_message = UserContent(user_message)

            print("\n[Investment-Recommendation-Agent]: ", end="")
            # Track if we've started printing the response
            response_started = False

            # Add a fallback message in case the agent doesn't respond
            fallback_message = None
            # Set a helpful fallback message based on the user's request
            if "summarize" in user_message.lower() and "filing" in user_message.lower():
                fallback_message = "[SEC-Filings-Research-Agent]: I'm having trouble summarizing the filing. Please make sure you've provided a valid filing URL or try finding the filing first using the find_filings tool."

            # Run the agent with the required parameters
            try:
                async for event in runner.run_async(
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    new_message=new_message
                ):
                    # Process the event to extract meaningful content
                    if hasattr(event, 'content') and event.content and event.content.parts:
                        for part in event.content.parts:
                            # Handle text responses
                            if hasattr(part, 'text') and part.text:
                                # If this is the first text part, don't add a newline
                                if not response_started:
                                    print(part.text, end="")
                                    response_started = True
                                else:
                                    print(part.text, end="")

                            # Handle function calls (show what the agent is doing)
                            elif hasattr(part, 'function_call') and part.function_call:
                                func_call = part.function_call
                                if not response_started:
                                    # Provide specific messages based on the function being called
                                    # SEC Filings Research Agent functions
                                    if func_call.name == "find_cik":
                                        print(f"[SEC-Filings-Research-Agent]: Searching for the company's CIK number...", end="")
                                    elif func_call.name == "find_filings":
                                        print(f"[SEC-Filings-Research-Agent]: Finding the company's recent SEC filings...", end="")
                                    elif func_call.name == "summarize_filing":
                                        print(f"[SEC-Filings-Research-Agent]: Extracting and analyzing the filing content...", end="")
                                    # Market Data Agent functions
                                    elif func_call.name == "get_stock_price":
                                        print(f"[Market-Data-Agent]: Retrieving current stock price...", end="")
                                    elif func_call.name == "get_historical_data":
                                        print(f"[Market-Data-Agent]: Retrieving historical stock data...", end="")
                                    elif func_call.name == "calculate_technical_indicators":
                                        print(f"[Market-Data-Agent]: Calculating technical indicators...", end="")
                                    elif func_call.name == "get_company_info_from_yahoo":
                                        print(f"[Market-Data-Agent]: Retrieving company information...", end="")
                                    elif func_call.name == "get_market_news":
                                        print(f"[Market-Data-Agent]: Retrieving market news...", end="")
                                    # Default for any other functions
                                    else:
                                        print(f"[Investment-Recommendation-Agent]: Processing your request...", end="")
                                    response_started = True

                            # Handle function responses (don't display raw responses)
                            elif hasattr(part, 'function_response') and part.function_response:
                                # We don't need to process the function response
                                # The model will handle it automatically

                                # We don't need to print the raw function response
                                # The model will summarize it in the next text response

                                # For summarize_filing responses, provide a simple message
                                func_response = part.function_response
                                if func_response.name == "summarize_filing":
                                    print("[SEC-Filings-Research-Agent]: (Processing filing content...)", end="")

                                    # Get the response data
                                    response_data = func_response.response

                                    # Print a message indicating that we've successfully extracted the filing content
                                    if isinstance(response_data, str):
                                        print(f" [SEC-Filings-Research-Agent]: (Successfully extracted {len(response_data)} characters of filing content)", end="")

                                        # Print a small preview of the content
                                        summary_length = min(500, len(response_data))
                                        print(f"\n\n[SEC-Filings-Research-Agent]: Filing Summary (first {summary_length} characters):\n{response_data[:summary_length]}...\n", end="")
                                    else:
                                        print(f" [SEC-Filings-Research-Agent]: (Response format not recognized: {type(response_data)})", end="")

                            # Handle image responses (warn and skip)
                            elif hasattr(part, 'inline_data') and part.inline_data:
                                # Skip images and warn the user
                                if not response_started:
                                    print("[Investment-Recommendation-Agent]: Warning: The agent tried to include an image in the response, but images are not supported. Displaying text only.", end="")
                                    response_started = True
                                else:
                                    print(" [Investment-Recommendation-Agent]: (Image removed - text only mode)", end="")
            except ClientError as e:
                # Check if this is the empty text parameter error
                if "empty text parameter" in str(e):
                    # Use the fallback message if available, otherwise provide a generic error message
                    if fallback_message:
                        print(f"[Investment-Recommendation-Agent]: {fallback_message}", end="")
                    else:
                        print("[Investment-Recommendation-Agent]: I'm having trouble generating a response. Please try a different question or rephrase your request.", end="")
                    response_started = True
                else:
                    # Re-raise other ClientErrors to be handled by the outer try-except block
                    raise

            # Add a newline after the agent's response
            if not response_started:
                if fallback_message:
                    print(f"[Investment-Recommendation-Agent]: {fallback_message}")
                else:
                    print("[Investment-Recommendation-Agent]: (No response)")
            else:
                print()

    except ValueError as e:
        print(f"Error: {e}")
        # The detailed instructions are already included in the error message from create_sec_filings_research_agent()

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example())
