"""
Helper Functions for Market Data Module

This module provides helper functions for calculating technical indicators
used by the market_data.py module.
"""

def calculate_moving_average(prices: list, window: int) -> float:
    """
    Calculate the simple moving average for a list of prices.
    
    Args:
        prices (list): List of price values
        window (int): The window size for the moving average
        
    Returns:
        float: The calculated moving average
    """
    if len(prices) < window:
        return None
    
    return sum(prices[-window:]) / window

def calculate_rsi(prices: list, window: int = 14) -> float:
    """
    Calculate the Relative Strength Index (RSI) for a list of prices.
    
    Args:
        prices (list): List of price values
        window (int): The window size for the RSI calculation
        
    Returns:
        float: The calculated RSI value
    """
    if len(prices) < window + 1:
        return None
    
    # Calculate price changes
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Calculate gains and losses
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    # Calculate average gains and losses
    avg_gain = sum(gains[-window:]) / window
    avg_loss = sum(losses[-window:]) / window
    
    # Calculate RS and RSI
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(prices: list, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple:
    """
    Calculate the Moving Average Convergence Divergence (MACD) for a list of prices.
    
    Args:
        prices (list): List of price values
        fast_period (int): The window size for the fast EMA
        slow_period (int): The window size for the slow EMA
        signal_period (int): The window size for the signal line
        
    Returns:
        tuple: (MACD line, Signal line, Histogram)
    """
    if len(prices) < slow_period + signal_period:
        return None, None, None
    
    # Calculate the fast and slow EMAs
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    if fast_ema is None or slow_ema is None:
        return None, None, None
    
    # Calculate the MACD line
    macd_line = fast_ema - slow_ema
    
    # Calculate the signal line (EMA of MACD line)
    # For simplicity, we'll use a simple moving average instead of EMA
    if len(prices) < slow_period + signal_period:
        return macd_line, None, None
    
    signal_line = calculate_moving_average([macd_line], signal_period)
    
    # Calculate the histogram
    histogram = macd_line - signal_line if signal_line is not None else None
    
    return macd_line, signal_line, histogram

def calculate_ema(prices: list, window: int) -> float:
    """
    Calculate the Exponential Moving Average (EMA) for a list of prices.
    
    Args:
        prices (list): List of price values
        window (int): The window size for the EMA
        
    Returns:
        float: The calculated EMA value
    """
    if len(prices) < window:
        return None
    
    # Calculate the multiplier
    multiplier = 2 / (window + 1)
    
    # Start with a simple moving average
    ema = sum(prices[:window]) / window
    
    # Calculate EMA for the remaining prices
    for price in prices[window:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

def calculate_bollinger_bands(prices: list, window: int = 20, num_std_dev: int = 2) -> tuple:
    """
    Calculate Bollinger Bands for a list of prices.
    
    Args:
        prices (list): List of price values
        window (int): The window size for the moving average
        num_std_dev (int): Number of standard deviations for the bands
        
    Returns:
        tuple: (Upper Band, Middle Band, Lower Band)
    """
    if len(prices) < window:
        return None, None, None
    
    # Calculate the middle band (simple moving average)
    middle_band = calculate_moving_average(prices, window)
    
    if middle_band is None:
        return None, None, None
    
    # Calculate the standard deviation
    variance = sum((price - middle_band) ** 2 for price in prices[-window:]) / window
    std_dev = variance ** 0.5
    
    # Calculate the upper and lower bands
    upper_band = middle_band + (std_dev * num_std_dev)
    lower_band = middle_band - (std_dev * num_std_dev)
    
    return upper_band, middle_band, lower_band

def calculate_atr(closes: list, highs: list, lows: list, window: int = 14) -> float:
    """
    Calculate the Average True Range (ATR) for a list of prices.
    
    Args:
        closes (list): List of closing prices
        highs (list): List of high prices
        lows (list): List of low prices
        window (int): The window size for the ATR
        
    Returns:
        float: The calculated ATR value
    """
    if len(closes) < window + 1 or len(highs) < window + 1 or len(lows) < window + 1:
        return None
    
    # Calculate true ranges
    true_ranges = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i-1]
        
        # True range is the greatest of:
        # 1. Current high - current low
        # 2. Absolute value of current high - previous close
        # 3. Absolute value of current low - previous close
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    # Calculate the average true range
    atr = sum(true_ranges[-window:]) / window
    
    return atr

def calculate_obv(closes: list, volumes: list) -> float:
    """
    Calculate the On-Balance Volume (OBV) for a list of prices and volumes.
    
    Args:
        closes (list): List of closing prices
        volumes (list): List of trading volumes
        
    Returns:
        float: The calculated OBV value
    """
    if len(closes) < 2 or len(volumes) < 2:
        return None
    
    # Start with the first volume
    obv = volumes[0]
    
    # Calculate OBV for the remaining prices
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        # If prices are equal, OBV doesn't change
    
    return obv