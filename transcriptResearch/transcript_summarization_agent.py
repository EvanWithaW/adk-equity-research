"""
Transcript Summarization Agent

This module implements a Google ADK agent that retrieves and summarizes investor meeting transcripts.
The agent can:
1. Search for recent investor meetings for a company
2. Retrieve the full text of meeting transcripts using the Alpha Vantage API
3. Summarize key information from transcripts

The agent is designed to function as a sub-agent to the investment recommendation agent.
"""

# Import Google ADK components
from google.adk.agents.llm_agent import Agent

# Import configuration
from filingsResearch.config import Config

# Import tools from transcript_tools
from transcriptResearch.transcript_tools import (
    search_investor_meetings,
    get_transcript_text,
    summarize_transcript
)

def create_transcript_summarization_agent():
    """
    Create a Transcript Summarization Agent.

    Returns:
        An Agent configured to search for and summarize investor meeting transcripts.
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

    if not key_status.get("ALPHA_VANTAGE_API_KEY", False):
        raise ValueError(
            "ALPHA_VANTAGE_API_KEY is required but not found in environment variables.\n"
            "Please set the ALPHA_VANTAGE_API_KEY environment variable by:\n"
            "1. Creating a .env file in the project root directory\n"
            "2. Adding the line: ALPHA_VANTAGE_API_KEY=your_api_key_here\n"
            "3. Restarting the application\n"
            "You can obtain an Alpha Vantage API key by registering at https://www.alphavantage.co/support/#api-key"
        )

    # Create tools for transcript research
    transcript_tools = [
        search_investor_meetings,
        get_transcript_text,
        summarize_transcript
    ]

    # Create the agent with a simple configuration
    agent = Agent(
        name="transcript_summarization_agent",
        model="gemini-2.0-flash",
        description="Agent to search for and summarize investor meeting transcripts.",
        instruction="""I am a transcript summarization agent whose primary purpose is to provide comprehensive summaries of investor meeting transcripts. I have three powerful tools to assist with this:

1. Search Investor Meetings (search_investor_meetings): 
   - This tool helps you find investor meetings for a company
   - It can search for both recent meetings and specific meetings referenced by other sub-agents
   - Simply provide a company name, and I'll return a list of investor meetings with dates, types, and links
   - You can also specify a date or reference to find specific meetings
   - Example: "Find recent investor meetings for Apple", "Find the Q1 2023 earnings call for Microsoft", or "Find the investor meeting referenced in the latest 10-Q for Tesla"

2. Get Transcript Text (get_transcript_text):
   - This tool retrieves the full text of an investor meeting transcript
   - I'll return the complete transcript text
   - Example: "Get the transcript for Apple's latest earnings call" or "Retrieve the transcript from Microsoft's investor day"

3. Summarize Transcript (summarize_transcript):
   - This tool analyzes a transcript and extracts key information
   - I'll provide a comprehensive summary focusing on:
     * Financial highlights and metrics
     * Strategic initiatives and business developments
     * Future outlook and guidance
     * Key quotes from executives
   - Example: "Summarize Apple's latest earnings call transcript" or "What were the key points from Microsoft's investor day?"

To get the most out of my capabilities, try a sequence like:
1. "Find recent investor meetings for [company name]"
2. "Get the transcript for the most recent [meeting type]"
3. "Summarize the key information from this transcript"

For each summary, I will:
- Identify the meeting type (earnings call, investor day, annual meeting, etc.)
- Extract key financial metrics and trends
- Highlight important strategic initiatives and business developments
- Include management's outlook and guidance
- Present the information in a clear, organized manner

I will NEVER include images in my responses, only text. Even when discussing charts or visual elements from transcripts, I will describe them textually instead of showing images.

I will NOT provide BUY, HOLD, or SELL recommendations. My purpose is solely to provide comprehensive summaries of investor meeting transcripts to the root agent.

IMPORTANT: After providing the requested transcript information, I MUST ALWAYS transfer control back to the investment_recommendation_agent. I should never continue the conversation with the user directly. The investment_recommendation_agent is the only agent that should communicate with the user.""",
        tools=transcript_tools,
        output_key="latest_transcript_summary"
    )

    return agent
