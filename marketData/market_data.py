"""
Market Data Module

This module provides functions for retrieving and analyzing market data.
It includes functions for:
1. Retrieving current stock prices
2. Retrieving historical stock data
3. Calculating technical indicators
4. Retrieving company information
5. Getting market news

The module uses the yfinance package to access Yahoo Finance data reliably.
"""

import requests
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import re
import os
import yfinance as yf

# Yahoo Finance API Information:
# 
# This module uses the yfinance package to retrieve market data:
# 
# 1. yfinance package (no API key required)
#    - Used for stock prices, historical data, and market news
#    - No registration or API key needed
#    - More reliable than direct Yahoo Finance API requests

# Import helper functions for technical indicators
from marketData.helper_functions import (
    calculate_moving_average,
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_obv
)

def get_stock_price(ticker: str) -> Dict[str, Any]:
    """
    Get the current stock price and basic information for a given ticker symbol.

    This tool retrieves the current stock price, along with other basic information
    such as the day's high, low, volume, and market cap.

    HOW TO USE THIS TOOL:
    1. Provide a valid ticker symbol (e.g., "AAPL" for Apple Inc.)
    2. The tool will return current price data and basic information

    EXAMPLE:
    ```
    # Get Apple's current stock price
    apple_price = get_stock_price("AAPL")
    print(f"Current price: ${apple_price['price']}")
    print(f"Change: {apple_price['change']}%")
    ```

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL" for Apple Inc.)

    Returns:
        dict: A dictionary containing current stock price information
    """
    # Ensure ticker is properly formatted
    ticker = ticker.strip().upper()

    try:
        # Print debugging information
        print(f"Requesting stock price for {ticker} using yfinance")

        # Get the ticker information using yfinance
        stock = yf.Ticker(ticker)

        # Get the ticker information
        info = stock.info

        # Get the current price (last price)
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            current_price = info['regularMarketPrice']
        elif 'currentPrice' in info and info['currentPrice'] is not None:
            current_price = info['currentPrice']
        elif 'previousClose' in info and info['previousClose'] is not None:
            current_price = info['previousClose']  # Fallback to previous close if current price is not available
        else:
            current_price = None

        # Get the previous close
        previous_close = info.get('regularMarketPreviousClose', info.get('previousClose', None))

        # Calculate the change percentage
        if current_price is not None and previous_close is not None and previous_close != 0:
            change_percent = ((current_price - previous_close) / previous_close) * 100
        else:
            change_percent = None

        # Create a dictionary with the relevant information
        result = {
            "ticker": ticker,
            "price": current_price,
            "change": change_percent,
            "previous_close": previous_close,
            "open": info.get('regularMarketOpen', info.get('open', None)),
            "day_high": info.get('regularMarketDayHigh', info.get('dayHigh', None)),
            "day_low": info.get('regularMarketDayLow', info.get('dayLow', None)),
            "volume": info.get('regularMarketVolume', info.get('volume', None)),
            "market_cap": info.get('marketCap', None),
            "pe_ratio": info.get('trailingPE', None),
            "dividend_yield": info.get('dividendYield', None),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "yfinance"
        }

        # Format the market cap for better readability
        if result["market_cap"]:
            if result["market_cap"] >= 1_000_000_000_000:  # Trillion
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000_000_000:.2f}T"
            elif result["market_cap"] >= 1_000_000_000:  # Billion
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000_000:.2f}B"
            elif result["market_cap"] >= 1_000_000:  # Million
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000:.2f}M"
            else:
                result["market_cap_formatted"] = f"${result['market_cap']:,.2f}"

        # Format the change percentage
        if result["change"] is not None:
            result["change_formatted"] = f"{result['change']:.2f}%"

        # Format the price
        if result["price"] is not None:
            result["price_formatted"] = f"${result['price']:.2f}"

        print(f"Successfully retrieved stock price for {ticker} using yfinance")
        return result

    except Exception as e:
        print(f"yfinance failed to retrieve stock price: {str(e)}")
        return {"error": f"Failed to retrieve stock price: {str(e)}"}

def get_historical_data(ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    """
    Get historical stock price data for a given ticker symbol.

    This tool retrieves historical stock price data, including open, high, low, close prices,
    and volume. It can be used to analyze price trends over different time periods.

    HOW TO USE THIS TOOL:
    1. Provide a valid ticker symbol (e.g., "AAPL" for Apple Inc.)
    2. Optionally specify the period (default: "1y" for 1 year) and interval (default: "1d" for daily)
    3. The tool will return historical price data for the specified period

    Valid period values: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
    Valid interval values: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"

    Note: Intraday data (intervals less than 1d) is only available for periods less than or equal to 60 days.

    EXAMPLE:
    ```
    # Get Apple's historical stock data for the past year with daily intervals
    apple_history = get_historical_data("AAPL", "1y", "1d")
    print(f"Number of data points: {len(apple_history['data'])}")
    print(f"Latest closing price: ${apple_history['data'][-1]['close']}")
    ```

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL" for Apple Inc.)
        period (str, optional): The time period to retrieve data for. Default is "1y" (1 year).
        interval (str, optional): The interval between data points. Default is "1d" (1 day).

    Returns:
        dict: A dictionary containing historical stock price data
    """
    # Ensure ticker is properly formatted
    ticker = ticker.strip().upper()

    # Validate period and interval
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]

    if period not in valid_periods:
        return {"error": f"Invalid period: {period}. Valid periods are: {', '.join(valid_periods)}"}

    if interval not in valid_intervals:
        return {"error": f"Invalid interval: {interval}. Valid intervals are: {', '.join(valid_intervals)}"}

    # Check if intraday data is requested for a period longer than 60 days
    intraday_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]
    long_periods = ["1y", "2y", "5y", "10y", "max"]

    if interval in intraday_intervals and period in long_periods:
        return {"error": "Intraday data (intervals less than 1d) is only available for periods less than or equal to 60 days."}

    try:
        # Print debugging information
        print(f"Requesting historical data for {ticker} using yfinance with period={period} and interval={interval}")

        # Get the ticker information using yfinance
        stock = yf.Ticker(ticker)

        # Get historical data
        hist_data = stock.history(period=period, interval=interval)

        # Check if we have valid data
        if hist_data.empty:
            return {"error": f"No historical data found for ticker symbol: {ticker}"}

        # Create a list of data points
        data_points = []
        for index, row in hist_data.iterrows():
            # Convert timestamp to date string
            date_str = index.strftime("%Y-%m-%d")

            # Add the data point
            data_points.append({
                "date": date_str,
                "open": row.get('Open', None),
                "high": row.get('High', None),
                "low": row.get('Low', None),
                "close": row.get('Close', None),
                "volume": row.get('Volume', None)
            })

        # Calculate some basic statistics
        if data_points:
            latest_close = data_points[-1]["close"]
            earliest_close = data_points[0]["close"]
            price_change = latest_close - earliest_close
            percent_change = (price_change / earliest_close) * 100 if earliest_close != 0 else 0

            # Find the highest and lowest prices in the period
            highest_price = max(point["high"] for point in data_points)
            lowest_price = min(point["low"] for point in data_points)

            # Calculate average volume
            average_volume = sum(point["volume"] for point in data_points) / len(data_points)

            # Calculate volatility (standard deviation of daily returns)
            if len(data_points) > 1:
                daily_returns = [(data_points[i]["close"] / data_points[i-1]["close"]) - 1 for i in range(1, len(data_points))]
                mean_return = sum(daily_returns) / len(daily_returns)
                variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
                volatility = (variance ** 0.5) * 100  # Convert to percentage
            else:
                volatility = 0
        else:
            latest_close = None
            earliest_close = None
            price_change = None
            percent_change = None
            highest_price = None
            lowest_price = None
            average_volume = None
            volatility = None

        # Create the result dictionary
        result = {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data_points": len(data_points),
            "start_date": data_points[0]["date"] if data_points else None,
            "end_date": data_points[-1]["date"] if data_points else None,
            "latest_close": latest_close,
            "earliest_close": earliest_close,
            "price_change": price_change,
            "percent_change": percent_change,
            "highest_price": highest_price,
            "lowest_price": lowest_price,
            "average_volume": average_volume,
            "volatility": volatility,
            "data": data_points
        }

        # Format the percent change
        if result["percent_change"] is not None:
            result["percent_change_formatted"] = f"{result['percent_change']:.2f}%"

        # Format the volatility
        if result["volatility"] is not None:
            result["volatility_formatted"] = f"{result['volatility']:.2f}%"

        print(f"Successfully retrieved historical data for {ticker} using yfinance")
        return result

    except Exception as e:
        print(f"yfinance failed to retrieve historical data: {str(e)}")
        return {"error": f"Failed to retrieve historical data: {str(e)}"}

def calculate_technical_indicators(ticker: str, period: str = "1y") -> Dict[str, Any]:
    """
    Calculate technical indicators for a given ticker symbol.

    This tool calculates various technical indicators based on historical price data,
    including moving averages, RSI, MACD, and Bollinger Bands. These indicators can
    be used for technical analysis of stock price trends.

    HOW TO USE THIS TOOL:
    1. Provide a valid ticker symbol (e.g., "AAPL" for Apple Inc.)
    2. Optionally specify the period (default: "1y" for 1 year)
    3. The tool will calculate and return various technical indicators

    EXAMPLE:
    ```
    # Calculate technical indicators for Apple
    apple_indicators = calculate_technical_indicators("AAPL", "1y")
    print(f"Current RSI: {apple_indicators['rsi']}")
    print(f"50-day MA: ${apple_indicators['ma_50']}")
    ```

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL" for Apple Inc.)
        period (str, optional): The time period to retrieve data for. Default is "1y" (1 year).

    Returns:
        dict: A dictionary containing calculated technical indicators
    """
    # Get historical data for the ticker
    historical_data = get_historical_data(ticker, period, "1d")

    # Check if there was an error retrieving the historical data
    if "error" in historical_data:
        return historical_data

    # Check if we have enough data points
    if len(historical_data["data"]) < 50:
        return {"error": f"Not enough historical data points to calculate indicators. Found {len(historical_data['data'])}, need at least 50."}

    # Extract closing prices
    closes = [point["close"] for point in historical_data["data"]]

    # Calculate moving averages
    ma_20 = calculate_moving_average(closes, 20)
    ma_50 = calculate_moving_average(closes, 50)
    ma_200 = calculate_moving_average(closes, 200) if len(closes) >= 200 else None

    # Calculate RSI (Relative Strength Index)
    rsi = calculate_rsi(closes, 14)

    # Calculate MACD (Moving Average Convergence Divergence)
    macd, signal, histogram = calculate_macd(closes)

    # Calculate Bollinger Bands
    upper_band, middle_band, lower_band = calculate_bollinger_bands(closes, 20, 2)

    # Calculate Average True Range (ATR)
    highs = [point["high"] for point in historical_data["data"]]
    lows = [point["low"] for point in historical_data["data"]]
    atr = calculate_atr(closes, highs, lows, 14)

    # Calculate On-Balance Volume (OBV)
    volumes = [point["volume"] for point in historical_data["data"]]
    obv = calculate_obv(closes, volumes)

    # Create the result dictionary
    result = {
        "ticker": ticker,
        "period": period,
        "latest_price": closes[-1] if closes else None,
        "ma_20": ma_20,
        "ma_50": ma_50,
        "ma_200": ma_200,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": signal,
        "macd_histogram": histogram,
        "bollinger_upper": upper_band,
        "bollinger_middle": middle_band,
        "bollinger_lower": lower_band,
        "atr": atr,
        "obv": obv,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Add technical signals
    result["signals"] = {}

    # Moving Average signals
    if ma_20 and ma_50:
        if closes[-1] > ma_20:
            result["signals"]["price_above_ma_20"] = "Bullish"
        else:
            result["signals"]["price_above_ma_20"] = "Bearish"

        if closes[-1] > ma_50:
            result["signals"]["price_above_ma_50"] = "Bullish"
        else:
            result["signals"]["price_above_ma_50"] = "Bearish"

        if ma_20 > ma_50:
            result["signals"]["ma_20_above_ma_50"] = "Bullish (Golden Cross)"
        else:
            result["signals"]["ma_20_above_ma_50"] = "Bearish (Death Cross)"

    # RSI signals
    if rsi:
        if rsi > 70:
            result["signals"]["rsi"] = "Overbought (Bearish)"
        elif rsi < 30:
            result["signals"]["rsi"] = "Oversold (Bullish)"
        else:
            result["signals"]["rsi"] = "Neutral"

    # MACD signals
    if macd and signal:
        if macd > signal:
            result["signals"]["macd"] = "Bullish"
        else:
            result["signals"]["macd"] = "Bearish"

    # Bollinger Bands signals
    if upper_band and lower_band:
        if closes[-1] > upper_band:
            result["signals"]["bollinger_bands"] = "Overbought (Bearish)"
        elif closes[-1] < lower_band:
            result["signals"]["bollinger_bands"] = "Oversold (Bullish)"
        else:
            result["signals"]["bollinger_bands"] = "Neutral"

    # Overall technical outlook
    bullish_signals = sum(1 for signal in result["signals"].values() if "Bullish" in signal)
    bearish_signals = sum(1 for signal in result["signals"].values() if "Bearish" in signal)

    if bullish_signals > bearish_signals:
        result["technical_outlook"] = "Bullish"
    elif bearish_signals > bullish_signals:
        result["technical_outlook"] = "Bearish"
    else:
        result["technical_outlook"] = "Neutral"

    return result

def get_company_info_from_yahoo(ticker: str) -> Dict[str, Any]:
    """
    Get detailed company information from Yahoo Finance.

    This tool retrieves comprehensive information about a company, including its
    business description, sector, industry, key executives, and more.

    HOW TO USE THIS TOOL:
    1. Provide a valid ticker symbol (e.g., "AAPL" for Apple Inc.)
    2. The tool will return detailed company information

    EXAMPLE:
    ```
    # Get information about Apple
    apple_info = get_company_info_from_yahoo("AAPL")
    print(f"Company: {apple_info['name']}")
    print(f"Sector: {apple_info['sector']}")
    print(f"Industry: {apple_info['industry']}")
    ```

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL" for Apple Inc.)

    Returns:
        dict: A dictionary containing company information
    """
    # Ensure ticker is properly formatted
    ticker = ticker.strip().upper()

    # Yahoo Finance API endpoint for company information
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=assetProfile,summaryProfile,summaryDetail,financialData,defaultKeyStatistics"

    # Set headers to mimic a browser request with additional headers to avoid 401 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://finance.yahoo.com',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

    try:
        # Make the GET request
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code != 200:
            return {"error": f"Failed to retrieve company information. Status code: {response.status_code}"}

        # Parse the JSON response
        data = response.json()

        # Check if the result contains valid data
        if not data or 'quoteSummary' not in data or 'result' not in data['quoteSummary'] or not data['quoteSummary']['result']:
            return {"error": f"No company information found for ticker symbol: {ticker}"}

        # Extract the company data
        company_data = data['quoteSummary']['result'][0]

        # Extract profile information
        profile = company_data.get('assetProfile', {})
        summary_profile = company_data.get('summaryProfile', {})
        summary_detail = company_data.get('summaryDetail', {})
        financial_data = company_data.get('financialData', {})
        key_stats = company_data.get('defaultKeyStatistics', {})

        # Combine profile data from both sources
        combined_profile = {**profile, **summary_profile}

        # Create the result dictionary
        result = {
            "ticker": ticker,
            "name": combined_profile.get('name', None),
            "sector": combined_profile.get('sector', None),
            "industry": combined_profile.get('industry', None),
            "business_summary": combined_profile.get('longBusinessSummary', None),
            "website": combined_profile.get('website', None),
            "market_cap": summary_detail.get('marketCap', {}).get('raw', None),
            "pe_ratio": summary_detail.get('trailingPE', {}).get('raw', None),
            "forward_pe": summary_detail.get('forwardPE', {}).get('raw', None),
            "dividend_yield": summary_detail.get('dividendYield', {}).get('raw', None),
            "beta": summary_detail.get('beta', {}).get('raw', None),
            "52_week_high": summary_detail.get('fiftyTwoWeekHigh', {}).get('raw', None),
            "52_week_low": summary_detail.get('fiftyTwoWeekLow', {}).get('raw', None),
            "50_day_average": summary_detail.get('fiftyDayAverage', {}).get('raw', None),
            "200_day_average": summary_detail.get('twoHundredDayAverage', {}).get('raw', None),
            "profit_margins": financial_data.get('profitMargins', {}).get('raw', None),
            "return_on_equity": financial_data.get('returnOnEquity', {}).get('raw', None),
            "return_on_assets": financial_data.get('returnOnAssets', {}).get('raw', None),
            "revenue_growth": financial_data.get('revenueGrowth', {}).get('raw', None),
            "earnings_growth": financial_data.get('earningsGrowth', {}).get('raw', None),
            "current_ratio": financial_data.get('currentRatio', {}).get('raw', None),
            "debt_to_equity": financial_data.get('debtToEquity', {}).get('raw', None),
            "free_cash_flow": financial_data.get('freeCashflow', {}).get('raw', None),
            "operating_cash_flow": financial_data.get('operatingCashflow', {}).get('raw', None),
            "shares_outstanding": key_stats.get('sharesOutstanding', {}).get('raw', None),
            "float_shares": key_stats.get('floatShares', {}).get('raw', None),
            "held_percent_insiders": key_stats.get('heldPercentInsiders', {}).get('raw', None),
            "held_percent_institutions": key_stats.get('heldPercentInstitutions', {}).get('raw', None),
            "short_ratio": key_stats.get('shortRatio', {}).get('raw', None),
            "short_percent_of_float": key_stats.get('shortPercentOfFloat', {}).get('raw', None),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Format the market cap for better readability
        if result["market_cap"]:
            if result["market_cap"] >= 1_000_000_000_000:  # Trillion
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000_000_000:.2f}T"
            elif result["market_cap"] >= 1_000_000_000:  # Billion
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000_000:.2f}B"
            elif result["market_cap"] >= 1_000_000:  # Million
                result["market_cap_formatted"] = f"${result['market_cap'] / 1_000_000:.2f}M"
            else:
                result["market_cap_formatted"] = f"${result['market_cap']:,.2f}"

        # Format the dividend yield
        if result["dividend_yield"] is not None:
            result["dividend_yield_formatted"] = f"{result['dividend_yield'] * 100:.2f}%"

        # Format the profit margins
        if result["profit_margins"] is not None:
            result["profit_margins_formatted"] = f"{result['profit_margins'] * 100:.2f}%"

        # Format the ROE and ROA
        if result["return_on_equity"] is not None:
            result["return_on_equity_formatted"] = f"{result['return_on_equity'] * 100:.2f}%"
        if result["return_on_assets"] is not None:
            result["return_on_assets_formatted"] = f"{result['return_on_assets'] * 100:.2f}%"

        # Format the growth rates
        if result["revenue_growth"] is not None:
            result["revenue_growth_formatted"] = f"{result['revenue_growth'] * 100:.2f}%"
        if result["earnings_growth"] is not None:
            result["earnings_growth_formatted"] = f"{result['earnings_growth'] * 100:.2f}%"

        # Format the insider and institutional holdings
        if result["held_percent_insiders"] is not None:
            result["held_percent_insiders_formatted"] = f"{result['held_percent_insiders'] * 100:.2f}%"
        if result["held_percent_institutions"] is not None:
            result["held_percent_institutions_formatted"] = f"{result['held_percent_institutions'] * 100:.2f}%"

        # Format the short percent of float
        if result["short_percent_of_float"] is not None:
            result["short_percent_of_float_formatted"] = f"{result['short_percent_of_float'] * 100:.2f}%"

        return result

    except Exception as e:
        return {"error": f"Failed to retrieve company information: {str(e)}"}




def get_market_news(ticker: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the latest market news, optionally filtered by a specific ticker.

    This tool retrieves recent news articles related to the market or a specific company.
    It can be used to stay informed about market developments and company-specific news.

    HOW TO USE THIS TOOL:
    1. Optionally provide a ticker symbol to get news specific to that company
    2. If no ticker is provided, general market news will be returned
    3. The tool will return a list of recent news articles with titles, sources, and summaries

    EXAMPLE:
    ```
    # Get general market news
    market_news = get_market_news()

    # Get news specific to Apple
    apple_news = get_market_news("AAPL")
    ```

    Args:
        ticker (str, optional): The stock ticker symbol (e.g., "AAPL" for Apple Inc.). Default is None.

    Returns:
        dict: A dictionary containing recent market news
    """
    # Format ticker if provided
    if ticker:
        ticker = ticker.strip().upper()

    try:
        # Print debugging information
        print(f"Requesting market news for {ticker if ticker else 'general market'} using yfinance")

        # Get the ticker information using yfinance
        if ticker:
            stock = yf.Ticker(ticker)

            # Try to get news from the ticker info
            # Note: yfinance doesn't have a direct method for retrieving news
            # We'll extract what we can from the available data

            # Get company information that might contain news
            info = stock.info

            # Create a list of news articles
            articles = []

            # Add company description as a "news" item if available
            if 'longBusinessSummary' in info and info['longBusinessSummary']:
                articles.append({
                    "title": f"About {ticker}: Company Overview",
                    "publisher": "Company Information",
                    "published_time": "N/A",
                    "published_time_formatted": "N/A",
                    "summary": info['longBusinessSummary'],
                    "url": f"https://finance.yahoo.com/quote/{ticker}"
                })

            # Add recent earnings information if available
            if 'lastDividendDate' in info and info['lastDividendDate']:
                try:
                    dividend_date = datetime.fromtimestamp(info['lastDividendDate'])
                    articles.append({
                        "title": f"{ticker} Last Dividend Information",
                        "publisher": "Financial Data",
                        "published_time": info['lastDividendDate'],
                        "published_time_formatted": dividend_date.strftime("%Y-%m-%d"),
                        "summary": f"Last dividend date: {dividend_date.strftime('%Y-%m-%d')}. Amount: ${info.get('lastDividendValue', 'N/A')}",
                        "url": f"https://finance.yahoo.com/quote/{ticker}"
                    })
                except:
                    pass

            # Add a note about using a dedicated news API
            articles.append({
                "title": "Note: Limited News Availability",
                "publisher": "System Message",
                "published_time": int(datetime.now().timestamp()),
                "published_time_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": "For comprehensive and up-to-date news, consider using a dedicated financial news API or service. The yfinance package has limited news retrieval capabilities.",
                "url": "#"
            })

            # Create the result dictionary
            result = {
                "ticker": ticker,
                "article_count": len(articles),
                "articles": articles,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "yfinance (limited news capability)"
            }
        else:
            # For general market news, provide a message about using a dedicated news API
            articles = [{
                "title": "Market News Not Available",
                "publisher": "System Message",
                "published_time": int(datetime.now().timestamp()),
                "published_time_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": "General market news is not available through the yfinance package. For comprehensive market news, consider using a dedicated financial news API or service.",
                "url": "#"
            }]

            # Create the result dictionary
            result = {
                "ticker": None,
                "article_count": len(articles),
                "articles": articles,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "System Message"
            }

        print(f"Returning available information for {ticker if ticker else 'general market'}")
        return result

    except Exception as e:
        print(f"Failed to retrieve market news: {str(e)}")
        return {"error": f"Failed to retrieve market news: {str(e)}"}
