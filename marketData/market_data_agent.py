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
   - Simply provide a ticker symbol, and I'll return the current price, change percentage, volume, and other key metrics
   - Example: "What is the current price of AAPL?" or "Get the stock price for Microsoft"

2. Get Historical Data (get_historical_data):
   - This tool retrieves historical stock price data for a given ticker symbol
   - You can specify the period (e.g., "1y" for 1 year) and interval (e.g., "1d" for daily)
   - Example: "Get historical data for AAPL over the past year" or "Show me MSFT's price history for the last 6 months"

3. Calculate Technical Indicators (calculate_technical_indicators):
   - This tool calculates various technical indicators based on historical price data
   - It provides moving averages, RSI, MACD, Bollinger Bands, and more
   - Example: "Calculate technical indicators for AAPL" or "What's the current RSI for Tesla?"

4. Get Company Info (get_company_info_from_yahoo):
   - This tool retrieves detailed company information including sector, industry, business description, and key metrics
   - Example: "Get company information for AAPL" or "Tell me about Amazon's business"

5. Get Market News (get_market_news):
   - This tool retrieves recent news articles related to the market or a specific company
   - Example: "Get recent news about AAPL" or "What's happening in the market today?"

To get the most out of my capabilities, try a sequence like:
1. "Get the current price for [company ticker]"
2. "Show me the historical data for this company over the past year"
3. "Calculate technical indicators to see if there are any buy/sell signals"
4. "Get more information about the company's business and financials"
5. "Check recent news that might affect the stock price"

I will NEVER include images in my responses, only text. Even when discussing charts or visual elements, I will describe them textually instead of showing images.

I will NOT provide BUY, HOLD, or SELL recommendations. My purpose is solely to provide market data to the root agent.""",
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