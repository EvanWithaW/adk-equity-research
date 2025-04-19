# ADK Equity Research Agent

## Developed by Evan Weidner

## Project Overview

The ADK Equity Research Agent is a powerful tool built using Google's Agent Development Kit (ADK) that enables comprehensive research on SEC filings for equity research purposes. This agent serves as an intelligent assistant for financial analysts, investors, and researchers who need to quickly access, analyze, and extract insights from SEC filings.

## Key Features

- **Company Information Lookup**: Find CIK (Central Index Key) numbers for companies and retrieve detailed company information from the SEC's EDGAR database.
- **SEC Filings Retrieval**: Fetch recent SEC filings (10-K, 10-Q, 8-K, etc.) for any publicly traded company.
- **Document Scanning**: Scan filing documents to extract specific information, search for keywords, and analyze content.
- **Text Extraction**: Extract and process the full text content from SEC filings.
- **Content Analysis**: Extract and summarize key financial metrics, identify trends, and analyze filing contents with context-aware keyword searching.
- **Web Search Integration**: Supplement SEC data with information from web searches for comprehensive research.
- **Conversational Interface**: Interact with the agent using natural language to perform research tasks.

## How It Works

The agent uses the SEC's EDGAR database to access public company filings. It can:

1. Look up CIK numbers for companies using their name or ticker symbol
2. Retrieve detailed company information from the SEC
3. Fetch recent SEC filings of various types
4. Extract and scan the text content from filings (specifically handling .htm format files)
5. Analyze filing contents to extract key financial metrics, summarize important data points, identify growth trends, and provide context-rich keyword analysis
6. Perform web searches to supplement SEC data

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
   ```

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
- "Search the web for information about recent SEC regulations"

## Project Structure

- `sec_filings_research_agent.py`: Main agent implementation using Google ADK
- `example_usage.py`: Example script demonstrating how to use the agent
- `filingsResearch/`: Package containing core functionality
  - `get_company_cik.py`: Functions for finding company CIK numbers
  - `sec_filings.py`: Functions for retrieving and analyzing SEC filings
  - `config.py`: Configuration settings and API key management

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
