# -*- coding: utf-8 -*-
"""K-line data loader: fetch historical data and convert to pandas DataFrame.

Phase 2.1: Why pandas?

Before (tools/kline.py): raw JSON arrays, manual calculation
After (analysis/data_loader.py): pandas DataFrame, one-line indicators

pandas is the standard for quantitative analysis because:
- Vectorized operations (fast, no Python loops)
- Built-in rolling windows (MA, RSI, MACD all need this)
- Easy date handling and alignment
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def _normalize_symbol(symbol: str, market: str) -> str:
    """Convert user input to yfinance format."""
    if market == "US":
        return symbol.upper()
    if market == "CN":
        code = symbol.strip()
        return f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
    if market == "HK":
        return f"{symbol}.HK"
    return symbol


def load_kline(symbol: str, market: str = "US", period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch K-line data and return as pandas DataFrame.

    Args:
        symbol: stock code, e.g. NVDA, 600519
        market: US, CN, HK
        period: 1mo, 3mo, 6mo, 1y
        interval: 1d (daily), 1wk (weekly)

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume, Date(index)

    Example:
        df = load_kline("NVDA", "US", "3mo")
        print(df.columns)  # Index(['Open', 'High', 'Low', 'Close', 'Volume'], dtype='object')
        print(df.tail(3))  # Last 3 days of data
    """
    yf_symbol = _normalize_symbol(symbol, market)

    ticker = yf.Ticker(yf_symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data found for {symbol} ({market})")

    # Keep only OHLCV columns
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    # Add date column from index
    df["Date"] = df.index.strftime("%Y-%m-%d")
    df.index.name = None

    # Drop rows where Close is NaN (holidays, incomplete data)
    df = df.dropna(subset=["Close"])

    return df


def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add basic technical indicators to DataFrame.

    This uses pandas built-in rolling() for efficient calculation.
    No Python loops needed - pandas does it in C internally.

    Args:
        df: DataFrame with 'Close' and 'Volume' columns

    Returns:
        DataFrame with added columns: MA5, MA10, MA20, MA60, Volume_MA5
    """
    df = df.copy()

    # Moving Averages (MA) - pandas rolling window
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA10"] = df["Close"].rolling(window=10).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()

    # Volume MA
    df["Volume_MA5"] = df["Volume"].rolling(window=5).mean()

    # Price change
    df["Change"] = df["Close"].pct_change() * 100  # percentage change

    return df


if __name__ == "__main__":
    # Test: fetch NVDA data
    print("Loading NVDA data...")
    df = load_kline("NVDA", "US", "3mo")
    print(f"Data points: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print()
    print("Last 5 days:")
    print(df.tail(5).to_string())

    print()
    print("Adding indicators...")
    df = add_basic_indicators(df)
    print(f"New columns: {[c for c in df.columns if c.startswith('MA')]}")
    print()
    print("Last 5 days with indicators:")
    print(df[["Close", "MA5", "MA10", "MA20", "Volume", "Volume_MA5"]].tail(5).to_string())