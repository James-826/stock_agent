# -*- coding: utf-8 -*-
"""Trend Analysis Tool: wraps analyze_trend() as a tool for the agent loop.

Now returns dict directly (new analyze_trend returns dict, not dataclass).
"""

import json
from ..analysis.trend import analyze_trend
from ..analysis.data_loader import load_kline


def analyze_stock_trend(symbol: str, period: str = "3mo", market: str = "US") -> dict:
    """Run technical trend analysis and return as JSON-serializable dict."""
    try:
        df = load_kline(symbol, market, period)
        # analyze_trend now returns dict directly
        result = analyze_trend(symbol, df)
        return result
    except Exception as e:
        return {"error": "ANALYSIS_ERROR", "message": f"Failed to analyze {symbol}: {str(e)}"}