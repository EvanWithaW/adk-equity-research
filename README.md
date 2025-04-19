# ADK Equity Research Agent

## Developed by Evan Weidner

## Project Overview

The ADK Equity Research Agent is a powerful tool built using Google's Agent Development Kit (ADK) that enables comprehensive equity research by analyzing SEC filings, market data, and investor meeting transcripts. This agent serves as an intelligent assistant for financial analysts, investors, and researchers who need to quickly access, analyze, and extract insights from multiple sources of financial information.

## Key Features

- **Company Information Lookup**: Find CIK (Central Index Key) numbers for companies and retrieve detailed company information from the SEC's EDGAR database.
- **SEC Filings Retrieval**: Fetch recent SEC filings (10-K, 10-Q, 8-K, etc.) for any publicly traded company.
- **Document Scanning**: Scan filing documents to extract specific information, search for keywords, and analyze content.
- **Text Extraction**: Extract and process the full text content from SEC filings.
- **Content Analysis**: Extract and summarize key financial metrics, identify trends, and analyze filing contents with context-aware keyword searching.
- **Market Data Analysis**: Retrieve and analyze current stock prices, historical data, and technical indicators.
- **Investor Meeting Transcripts**: Search for, retrieve, and summarize transcripts from recent investor meetings and earnings calls.
- **Holistic Investment Recommendations**: Integrate information from SEC filings, market data, and investor meeting transcripts to provide comprehensive BUY, HOLD, or SELL recommendations.
- **Web Search Integration**: Supplement financial data with information from web searches for comprehensive research.
- **Conversational Interface**: Interact with the agent using natural language to perform research tasks.

## How It Works

The agent integrates multiple data sources to provide comprehensive equity research. It can:

1. Look up CIK numbers for companies using their name or ticker symbol
2. Retrieve detailed company information from the SEC
3. Fetch recent SEC filings of various types
4. Extract and scan the text content from filings (specifically handling .htm format files)
5. Analyze filing contents to extract key financial metrics, summarize important data points, identify growth trends, and provide context-rich keyword analysis
6. Retrieve current stock prices, historical data, and calculate technical indicators
7. Search for recent investor meetings and earnings calls for a company
8. Retrieve and analyze transcripts from investor meetings to extract key information
9. Integrate information from all sources to provide holistic investment recommendations
10. Perform web searches to supplement financial data

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Google API Key (for the ADK and LLM capabilities)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/adk-equity-research.git
   cd adk-equity-research
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your API keys:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
   ```

   You can obtain an Alpha Vantage API key by registering at [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

### Usage

Run the example script to start an interactive session with the agent:

```
python example_usage.py
```

This will start a conversational interface where you can ask questions like:
- "What is the CIK number for Apple?"
- "Get detailed information about Microsoft using its CIK"
- "Fetch recent 10-K filings for Tesla"
- "Analyze the latest 10-Q filing for Amazon for mentions of 'supply chain'"
- "Get the current stock price and technical indicators for Google"
- "Find recent investor meetings for Netflix"
- "Get the transcript for Apple's latest earnings call"
- "Summarize the key information from this transcript"
- "Provide a buy/hold/sell recommendation for Amazon based on all available information"
- "Search the web for information about recent SEC regulations"

## Project Structure

- `investment_recommendation_agent.py`: Main root agent implementation using Google ADK
- `example_usage.py`: Example script demonstrating how to use the agent
- `filingsResearch/`: Package containing SEC filings research functionality
  - `sec_filings_research_agent.py`: SEC filings research sub-agent implementation
  - `get_company_cik.py`: Functions for finding company CIK numbers
  - `sec_filings.py`: Functions for retrieving and analyzing SEC filings
  - `config.py`: Configuration settings and API key management
- `marketData/`: Package containing market data functionality
  - `market_data_agent.py`: Market data sub-agent implementation
  - `market_data.py`: Functions for retrieving and analyzing market data
  - `helper_functions.py`: Helper functions for market data analysis
- `transcriptResearch/`: Package containing transcript research functionality
  - `transcript_summarization_agent.py`: Transcript summarization sub-agent implementation
  - `transcript_tools.py`: Tools for searching, retrieving, and summarizing investor meeting transcripts

## Dependencies

- google-adk: Google's Agent Development Kit
- beautifulsoup4: For HTML/XML parsing
- requests: For making HTTP requests
- python-dotenv: For loading environment variables
- lxml: For XML parsing in BeautifulSoup

## Future Enhancements

- Financial data extraction and visualization
- Comparative analysis between multiple filings or companies
- Integration with financial data APIs for comprehensive analysis
- Support for additional filing types and regulatory documents
- Real-time transcription of live investor meetings and earnings calls
- Sentiment analysis of investor meeting transcripts
- Tracking changes in management tone and language across multiple meetings
- Integration with audio sources for direct transcription of investor meetings
