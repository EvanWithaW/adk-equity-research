"""
SEC Filings Research Agent

This module implements a Google ADK agent that provides summaries of SEC filings.
The agent can:
1. Look up CIK numbers for companies
2. Retrieve detailed company information from the SEC
3. Fetch and analyze recent SEC filings
4. Extract and analyze filing contents
5. Provide comprehensive summaries of SEC filings

The agent is designed to function as a sub-agent to a root agent that provides investment recommendations.
"""

import asyncio

# Import Google ADK components
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Import our SEC filings research functions
from filingsResearch.get_company_cik import find_cik
from filingsResearch.sec_filings import (
    find_filings,
    summarize_filing as _summarize_filing
)


# Create a wrapper for summarize_filing that handles chunking
def summarize_filing(filing_url: str, chunk_index: int = 0, max_chunk_size: int = 200000) -> str:
    """
    Wrapper for the summarize_filing function that handles chunking of large filings.

    This function retrieves a specific chunk of a filing to prevent hitting token limits.
    Use chunk_index=-1 to get information about the total number of chunks available.

    Args:
        filing_url (str): The URL of the SEC filing
        chunk_index (int, optional): Index of the chunk to return (0-based). 
                                    Use -1 to get information about total chunks. Defaults to 0.
        max_chunk_size (int, optional): Maximum size of each chunk in characters. Defaults to 200000.

    Returns:
        str: A chunk of the filing text, or information about the total number of chunks
    """
    return _summarize_filing(filing_url, chunk_index=chunk_index, max_chunk_size=max_chunk_size)

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
        raise ValueError(
            "GOOGLE_API_KEY is required but not found in environment variables.\n"
            "Please set the GOOGLE_API_KEY environment variable by:\n"
            "1. Creating a .env file in the project root directory\n"
            "2. Adding the line: GOOGLE_API_KEY=your_api_key_here\n"
            "3. Restarting the application\n"
            "You can obtain a Google API key from https://makersuite.google.com/app/apikey"
        )

    # Create tools for SEC filings research
    sec_tools = [
        find_cik,
        find_filings,
        summarize_filing
    ]

    # Create the agent with a simple configuration
    agent = Agent(
        name="sec_filings_research_agent",
        model="gemini-2.0-flash",
        description="Agent to research SEC filings and provide comprehensive summaries.",
        instruction="""I am an SEC filings research agent whose primary purpose is to provide comprehensive summaries of SEC filings that focus on the COMPANY'S FINANCIAL INFORMATION AND BUSINESS DETAILS, not just lists of the filing documents themselves. I have three powerful tools to assist with this:

1. Find CIK (find_cik): 
   - This tool helps find a company's CIK (Central Index Key) number, which is required to access SEC filings
   - I will automatically use this tool when the investment_recommendation_agent provides a company name or ticker symbol
   - I will NEVER ask the user for this information

2. Find Filings (find_filings):
   - This tool finds a company's most recent SEC filings using their CIK number
   - I'll return a list of filings with titles, dates, and links
   - I will automatically use this tool after obtaining the CIK, focusing on 10-K, 10-Q, and 8-K filings
   - I will NEVER ask the user which filings to retrieve

3. Summarize Filing (summarize_filing):
   - This tool extracts the text of an SEC filing in manageable chunks to prevent hitting token limits
   - I MUST use this tool whenever financial information is needed, as it accesses the actual filing content, not just the filing index
   - All financial information MUST be obtained directly from SEC filings using this tool, not from other sources
   - For large filings, I should:
     * First call summarize_filing with chunk_index=-1 to get information about the total number of chunks
     * Then request each chunk individually by calling summarize_filing with chunk_index=0, 1, 2, etc.
     * Process each chunk before requesting the next one to avoid hitting token limits
   - IMPORTANT: When I receive the filing text, I must NOT simply list the filing documents, exhibits, or XBRL data. Instead, I MUST thoroughly analyze the content to extract and summarize INFORMATION ABOUT THE COMPANY, including:
     * Key financial metrics (revenue, profit, margins, etc.)
     * Growth trends and year-over-year changes
     * Important business developments
     * Risk factors and challenges
     * Management's outlook and guidance
   - I'll create a comprehensive summary focusing on the most relevant information ABOUT THE COMPANY, not about the filing itself

CRITICAL: I MUST OPERATE COMPLETELY AUTONOMOUSLY. I will:
1. AUTOMATICALLY use find_cik when the investment_recommendation_agent provides a company name
2. AUTOMATICALLY use find_filings after obtaining the CIK
3. AUTOMATICALLY use summarize_filing to analyze the most relevant filings
4. NEVER ask the user for any technical information such as CIK numbers, filing types, or filing URLs
5. NEVER wait for user input between these steps - I will gather ALL information myself

For each summary, I will:
- Provide key financial metrics and trends from the filing
- Highlight important business developments and risk factors
- Include management's outlook and guidance
- Present the information in a clear, organized manner
- Include any relevant caveats or considerations

IMPORTANT: I must always obtain financial information directly from SEC filings using the summarize_filing tool. This tool accesses the actual filing content, not just the index. I should never rely on other sources for financial data.

I will NEVER include images in my responses, only text. Even when discussing charts or visual elements from filings, I will describe them textually instead of showing images.

I will NOT provide BUY, HOLD, or SELL recommendations. My purpose is solely to provide comprehensive summaries of SEC filings to the root agent.

IMPORTANT: After providing the requested SEC filing information, I MUST ALWAYS transfer control back to the investment_recommendation_agent. I should never continue the conversation with the user directly. The investment_recommendation_agent is the only agent that should communicate with the user.""",
        tools=sec_tools,
        output_key="latest_analysis_result"
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
        session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

        # Run the agent
        await runner.run_async()
    except ValueError as e:
        print(f"Error: {e}")
        # The detailed instructions are already included in the error message from create_sec_filings_research_agent()

if __name__ == "__main__":
    # Run the main function when the script is executed directly
    asyncio.run(main())
