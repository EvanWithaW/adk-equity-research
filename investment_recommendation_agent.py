"""
Investment Recommendation Agent

This module implements a Google ADK root agent that provides buy/hold/sell recommendations
based on summaries of SEC filings provided by the SEC Filings Research Agent.

The agent can:
1. Leverage the SEC Filings Research Agent to obtain summaries of SEC filings
2. Analyze the summaries to identify key financial metrics and trends
3. Provide BUY, HOLD, or SELL recommendations with supporting rationale

The agent is designed to function as a comprehensive equity research assistant that helps
users make informed investment decisions.
"""

import asyncio

# Import Google ADK components
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Import our SEC filings research agent
from filingsResearch.sec_filings_research_agent import create_sec_filings_research_agent

# Import configuration
from filingsResearch.config import Config

# Define constants
APP_NAME = "investment_recommendation_agent"
USER_ID = "user1234"
SESSION_ID = "1234"

# Define the Investment Recommendation Agent
def create_investment_recommendation_agent():
    """
    Create an Investment Recommendation Agent that leverages the SEC Filings Research Agent.

    Returns:
        An Agent configured to provide investment recommendations based on SEC filings summaries.
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

    # Create the SEC Filings Research Agent as a sub-agent
    sec_filings_research_agent = create_sec_filings_research_agent()

    # Create the root agent with a simple configuration
    agent = Agent(
        name="investment_recommendation_agent",
        model="gemini-2.0-flash",
        description="Agent to provide buy/hold/sell recommendations for stocks based on SEC filings analysis.",
        instruction="""I am an investment recommendation agent whose primary purpose is to provide BUY, HOLD, or SELL recommendations for stocks based on SEC filings analysis.

I leverage the SEC Filings Research Agent to obtain comprehensive summaries of SEC filings. The SEC Filings Research Agent has three powerful tools:

1. Find CIK (find_cik): 
   - This tool helps find a company's CIK (Central Index Key) number, which is required to access SEC filings
   - Example: "What is the CIK for Apple?" or "Find the CIK for MSFT"

2. Find Filings (find_filings):
   - This tool finds a company's most recent SEC filings using their CIK number
   - It returns a list of filings with titles, dates, and links
   - You can specify a filing type (like "10-K" or "10-Q") and how many filings to retrieve
   - Example: "Find recent 10-K filings for Apple" or "Get the latest quarterly report for Microsoft"

3. Summarize Filing (summarize_filing):
   - This tool extracts the complete text of an SEC filing
   - The SEC Filings Research Agent analyzes the complete text to identify key financial metrics, growth trends, business developments, risk factors, and management's outlook
   - The agent provides a comprehensive summary of the filing
   - Example: "Analyze Apple's latest 10-K filing and provide a summary"

Based on the summaries provided by the SEC Filings Research Agent, I will:
1. Analyze the key financial metrics and trends
2. Evaluate the company's business developments and risk factors
3. Consider management's outlook and guidance
4. Provide a clear BUY, HOLD, or SELL recommendation with supporting rationale

For each recommendation, I will:
- Clearly state my BUY, HOLD, or SELL recommendation
- Provide key financial metrics and trends that support my recommendation
- Highlight important business developments and risk factors
- Explain my reasoning for the recommendation
- Include any relevant caveats or considerations

To get the most out of my capabilities, try a sequence like:
1. "Find the CIK for [company name]"
2. "Find recent [filing type] filings for this company"
3. "Analyze the most recent filing and provide a buy/hold/sell recommendation"

I will NEVER include images in my responses, only text. Even when discussing charts or visual elements from filings, I will describe them textually instead of showing images.""",
        sub_agents=[sec_filings_research_agent],
        output_key="latest_recommendation_result"
    )

    return agent

# Example of how to run the agent
async def main():
    """
    Run the Investment Recommendation Agent.

    This function creates and runs the agent, allowing users to interact with it
    to get investment recommendations based on SEC filings analysis.
    """
    try:
        # Create the agent
        agent = create_investment_recommendation_agent()

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
        # The detailed instructions are already included in the error message from create_investment_recommendation_agent()

if __name__ == "__main__":
    # Run the main function when the script is executed directly
    asyncio.run(main())
