"""
SEC Filings Research Agent

This module implements a Google ADK agent that can perform comprehensive research on SEC filings.
The agent can:
1. Look up CIK numbers for companies
2. Retrieve detailed company information from the SEC
3. Fetch and analyze recent SEC filings
4. Extract and analyze filing contents

The agent is designed to function as a sub-agent to another main agent for equity research.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional

# Import Google ADK components
from google.adk.agents.llm_agent import Agent
from google.adk.tools.function_tool import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.google_search_tool import google_search

# Import our SEC filings research functions
from filingsResearch.get_company_cik import find_cik
from filingsResearch.sec_filings import (
    get_company_info,
    get_recent_filings,
    extract_filing_text,
    analyze_filing
)

# Import configuration
from filingsResearch.config import Config

# Define constants
APP_NAME = "sec_filings_research_agent"
USER_ID = "user1234"
SESSION_ID = "1234"

# Define the SEC Filings Research Agent
def create_sec_filings_research_agent():
    """
    Create a simple SEC Filings Research Agent.

    Returns:
        An Agent configured to perform SEC filings research.
    """
    # Validate that required API keys are present
    key_status = Config.validate_required_keys()
    if not key_status.get("GOOGLE_API_KEY", False):
        raise ValueError("GOOGLE_API_KEY is required but not found in environment variables")

    # Create tools for SEC filings research
    sec_tools = [
        find_cik,
        get_company_info,
        get_recent_filings,
        extract_filing_text,
        analyze_filing,
    ]

    # Create the agent with a simple configuration
    agent = Agent(
        name="sec_filings_research_agent",
        model="gemini-2.0-flash",
        description="Agent to research SEC filings and answer questions using Google Search.",
        instruction="I can help you research SEC filings for companies and answer questions by searching the internet. Just ask me anything about company filings or financial information!",
        tools=sec_tools
    )

    return agent

# Example of how to run the agent
async def main():
    """
    Run the SEC Filings Research Agent.

    This function creates and runs the agent, allowing users to interact with it
    to research SEC filings for companies.
    """
    try:
        # Create the agent
        agent = create_sec_filings_research_agent()

        # Create a session service
        session_service = InMemorySessionService()

        # Create a runner for the agent
        runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=session_service
        )

        # Create a session
        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

        # Run the agent
        await runner.run_async()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please ensure that the GOOGLE_API_KEY environment variable is set.")

if __name__ == "__main__":
    # Run the main function when the script is executed directly
    asyncio.run(main())
