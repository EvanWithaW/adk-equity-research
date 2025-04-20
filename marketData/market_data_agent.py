"""
Market Data Agent

This module implements a Google ADK agent that provides market data.
The agent can:
1. Retrieve current stock prices
2. Retrieve historical stock data
3. Calculate technical indicators
4. Retrieve company information
5. Get market news

The agent is designed to function as a sub-agent to a root agent that provides investment recommendations.
"""

import asyncio

# Import Google ADK components
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Import our market data functions
from marketData.market_data import (
    get_stock_price,
    get_historical_data,
    calculate_technical_indicators,
    get_company_info_from_yahoo,
    get_market_news
)


# Define constants
APP_NAME = "market_data_agent"
USER_ID = "user1234"
SESSION_ID = "1234"

# Define the Market Data Agent
def create_market_data_agent():
    """
    Create a Market Data Agent.

    Returns:
        An Agent configured to provide market data.
    """
    # Create tools for market data
    market_tools = [
        get_stock_price,
        get_historical_data,
        calculate_technical_indicators,
        get_company_info_from_yahoo,
        get_market_news
    ]

    # Create the agent with a simple configuration
    agent = Agent(
        name="market_data_agent",
        model="gemini-2.0-flash",
        description="Agent to retrieve and analyze market data.",
        instruction="""I am a market data agent whose primary purpose is to provide current and historical market data. I have five powerful tools to assist with this:

1. Get Stock Price (get_stock_price): 
   - This tool retrieves the current stock price and basic information for a given ticker symbol
   - I will automatically use this tool when the investment_recommendation_agent provides a ticker symbol
   - I will NEVER ask the user for ticker symbols or any other technical information

2. Get Historical Data (get_historical_data):
   - This tool retrieves historical stock price data for a given ticker symbol
   - I will automatically use appropriate period (e.g., "1y" for 1 year) and interval (e.g., "1d" for daily) parameters
   - I will NEVER ask the user for these technical parameters

3. Calculate Technical Indicators (calculate_technical_indicators):
   - This tool calculates various technical indicators based on historical price data
   - It provides moving averages, RSI, MACD, Bollinger Bands, and more
   - I will automatically use this tool to provide comprehensive technical analysis

4. Get Company Info (get_company_info_from_yahoo):
   - This tool retrieves detailed company information including sector, industry, business description, and key metrics
   - I will automatically use this tool to get additional context about the company

5. Get Market News (get_market_news):
   - This tool retrieves recent news articles related to the market or a specific company
   - I will automatically use this tool to get recent news that might impact the stock

CRITICAL: I MUST OPERATE COMPLETELY AUTONOMOUSLY. I will:
1. AUTOMATICALLY use get_stock_price when the investment_recommendation_agent provides a ticker symbol
2. AUTOMATICALLY use get_historical_data to understand price trends
3. AUTOMATICALLY use calculate_technical_indicators to get technical analysis insights
4. AUTOMATICALLY use get_company_info_from_yahoo to get additional company context
5. AUTOMATICALLY use get_market_news to get recent news that might impact the stock
6. NEVER ask the user for any technical information such as ticker symbols, time periods, or technical parameters
7. NEVER wait for user input between these steps - I will gather ALL information myself

I will NEVER include images in my responses, only text. Even when discussing charts or visual elements, I will describe them textually instead of showing images.

I will NOT provide BUY, HOLD, or SELL recommendations. My purpose is solely to provide market data to the root agent.

IMPORTANT: After providing the requested market data, I MUST ALWAYS transfer control back to the investment_recommendation_agent. I should never continue the conversation with the user directly. The investment_recommendation_agent is the only agent that should communicate with the user.""",
        tools=market_tools,
        output_key="latest_market_data_result"
    )

    return agent

# Example of how to run the agent
async def main():
    """
    Run the Market Data Agent.

    This function creates and runs the agent, allowing users to interact with it
    to retrieve market data.
    """
    try:
        # Create the agent
        agent = create_market_data_agent()

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
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Run the main function when the script is executed directly
    asyncio.run(main())
