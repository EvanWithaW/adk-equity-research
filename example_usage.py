"""
Example Usage of Investment Recommendation Agent

This script demonstrates how to use the Investment Recommendation Agent to get
buy/hold/sell recommendations based on comprehensive analysis of SEC filings,
market data, and investor meeting transcripts.

Usage:
    python example_usage.py

This will start an interactive session with the Investment Recommendation Agent where you can
simply ask about companies or stocks, and the agent will autonomously gather all necessary
information from its specialized sub-agents to provide comprehensive investment recommendations.
No need to guide the agent through a step-by-step process - just ask about a company, and
the agent will do the rest!
"""

import asyncio
import os
import dotenv
import time
import random
from investment_recommendation_agent import create_investment_recommendation_agent, Runner, APP_NAME, USER_ID, SESSION_ID
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import UserContent
from google.genai.errors import ClientError

# Rate limiting parameters
MAX_RETRIES = 5
INITIAL_DELAY = 2.0
BACKOFF_FACTOR = 2.0
JITTER_FACTOR = 0.1

async def run_with_rate_limit(runner, user_id, session_id, new_message):
    """
    Run the agent with rate limiting and retry logic for RESOURCE_EXHAUSTED errors.

    Args:
        runner: The runner instance
        user_id: The user ID
        session_id: The session ID
        new_message: The message to send

    Yields:
        Events from the runner
    """
    retry_count = 0
    delay = INITIAL_DELAY

    while True:
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            ):
                yield event
            # If we get here, the operation completed successfully
            break
        except ClientError as e:
            error_str = str(e)

            # Check if this is a RESOURCE_EXHAUSTED error
            if "RESOURCE_EXHAUSTED" in error_str:
                # Check if we've reached the maximum number of retries
                if retry_count >= MAX_RETRIES:
                    print(f"\n[System]: Rate limit exceeded after {MAX_RETRIES} retries. Please try again later.")
                    raise

                # Extract retry delay from error message if available
                retry_delay = None
                import re
                retry_match = re.search(r'retryDelay": "(\d+)s"', error_str)
                if retry_match:
                    retry_delay = int(retry_match.group(1))
                    print(f"\n[System]: Rate limit exceeded. API suggests waiting {retry_delay} seconds. Retrying...")

                # Calculate delay with jitter
                if retry_delay:
                    actual_delay = retry_delay
                else:
                    actual_delay = delay * (1 + random.random() * JITTER_FACTOR)

                print(f"\n[System]: Rate limit exceeded. Waiting {actual_delay:.1f} seconds before retrying (attempt {retry_count + 1}/{MAX_RETRIES})...")

                # Wait before retrying
                await asyncio.sleep(actual_delay)

                # Increase delay for next retry using exponential backoff
                delay *= BACKOFF_FACTOR
                retry_count += 1
            else:
                # For other types of ClientError, re-raise
                raise

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
    print("Simply ask about a company or stock, and the agent will autonomously gather")
    print("all necessary information to provide a comprehensive investment recommendation.")
    print("Try asking questions like:")
    print("  - What do you think about Apple as an investment?")
    print("  - Should I buy, hold, or sell Tesla stock?")
    print("  - Provide an investment recommendation for Amazon")
    print("  - What's your analysis of Microsoft stock?")
    print("  - Give me a recommendation for Nvidia")
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
        print("\n[Investment-Recommendation-Agent]: Hello! I'm the Investment Recommendation Agent. My primary purpose is to provide BUY, HOLD, or SELL recommendations for stocks based on comprehensive analysis of SEC filings, market data, and investor meeting transcripts. When you ask about a company or stock, I'll automatically gather all necessary information by working with my specialized sub-agents. You don't need to guide me through the process - just ask about a company, and I'll do the rest! How can I assist you today?")

        # Start the conversation loop
        while True:
            # Variable to store the agent's response text
            agent_response_text = ""

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

            # Run the agent with the required parameters and rate limiting
            try:
                async for event in run_with_rate_limit(
                    runner=runner,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    new_message=new_message
                ):
                    # Process the event to extract meaningful content
                    if hasattr(event, 'content') and event.content and event.content.parts:
                        for part in event.content.parts:
                            # Handle text responses
                            if hasattr(part, 'text') and part.text:
                                # Accumulate the text in agent_response_text
                                agent_response_text += part.text

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

            # Variable to store the agent's response text
            agent_response_text = ""

            # Add a newline after the agent's response
            if not response_started:
                if fallback_message:
                    agent_response_text = fallback_message
                    print(f"[Investment-Recommendation-Agent]: {fallback_message}")
                else:
                    print("[Investment-Recommendation-Agent]: (No response)")
            else:
                print()

            # Check if the response contains a transfer control message
            transfer_phrases = [
                "transfer control back to the investment_recommendation_agent",
                "will transfer control back to the investment_recommendation_agent",
                "transferring control back to the investment_recommendation_agent",
                "i will transfer control back to the investment_recommendation_agent",
                "transfer control to the investment_recommendation_agent",
                "returning control to the investment_recommendation_agent",
                "handing control back to the investment_recommendation_agent"
            ]

            if any(phrase in agent_response_text.lower() for phrase in transfer_phrases):
                # Automatically continue with a follow-up request to the investment_recommendation_agent
                print("\n[System]: Detected transfer of control back to Investment Recommendation Agent. Continuing analysis...")
                user_message = "Please continue with your analysis and provide a recommendation based on the information provided."
                print(f"\nYou (Auto): {user_message}")
                # Create a new message from user input
                new_message = UserContent(user_message)
                print("\n[Investment-Recommendation-Agent]: ", end="")
                # Reset response_started and agent_response_text for the new response
                response_started = False
                agent_response_text = ""

                # Run the agent again with the new message and rate limiting
                try:
                    async for event in run_with_rate_limit(
                        runner=runner,
                        user_id=USER_ID,
                        session_id=SESSION_ID,
                        new_message=new_message
                    ):
                        # Process the event to extract meaningful content
                        if hasattr(event, 'content') and event.content and event.content.parts:
                            for part in event.content.parts:
                                # Handle text responses
                                if hasattr(part, 'text') and part.text:
                                    # Accumulate the text in agent_response_text
                                    agent_response_text += part.text

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

                # Skip the input prompt and continue the loop
                continue

    except ValueError as e:
        print(f"Error: {e}")
        # The detailed instructions are already included in the error message from create_sec_filings_research_agent()

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example())
