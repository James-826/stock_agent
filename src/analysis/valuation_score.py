# -*- coding: utf-8 -*-
"""Valuation Analyzer: fundamental valuation layer.

Separate from technical and sentiment analysis.
Focuses on: PE, PB, ROE, market cap, dividend yield.

Each metric scores 0-100 based on comparison with industry norms.
Combined score = weighted average.
"""

import httpx
import os
from typing import Dict, Any


def _get_valuation_data(symbol: str) -> dict:
    """Fetch fundamental data from Yahoo Finance.

    Returns: {PE, PB, ROE, market_cap, dividend_yield, sector, industry}
    """
    try:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        with httpx.Client(proxy=proxy, timeout=15) as client:
            resp = client.get(
                f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
                params={"modules": "defaultKeyStatistics,financialData,summaryProfile"},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = resp.json()["quoteSummary"]["result"][0]

            stats = data.get("defaultKeyStatistics", {})
            financial = data.get("financialData", {})
            profile = data.get("summaryProfile", {})

            def _val(key, obj=stats):
                v = obj.get(key, {})
                return v.get("raw") if isinstance(v, dict) else None

            return {
                "PE": _val("trailingPE"),
                "forward_PE": _val("forwardPE"),
                "PB": _val("priceToBook"),
                "ROE": _val("returnOnEquity"),
                "market_cap": _val("marketCap", financial),
                "dividend_yield": _val("dividendYield"),
                "revenue_growth": _val("revenueGrowth", financial),
                "profit_margin": _val("profitMargins", financial),
                "debt_to_equity": _val("debtToEquity"),
                "sector": profile.get("sector", "Unknown"),
                "industry": profile.get("industry", "Unknown"),
                "error": None,
            }
    except Exception as e:
        return {"PE": None, "PB": None, "ROE": None, "market_cap": None,
                "dividend_yield": None, "revenue_growth": None,
                "profit_margin": None, "debt_to_equity": None,
                "sector": "Unknown", "industry": "Unknown", "error": str(e)}


# ============================================================
# Sub-score Functions (each 0-100)
# ============================================================

def _score_pe(pe: float) -> int:
    """PE score: lower is better (cheaper).

    PE < 10:   very cheap (85)
    PE 10-15:  cheap (75)
    PE 15-25:  fair (55)
    PE 25-40:  expensive (35)
    PE 40-60:  very expensive (20)
    PE > 60:   extreme (10)
    Negative PE: N/A -> 50 (neutral)
    """
    if pe is None or pe <= 0:
        return 50  # negative earnings, can't evaluate
    if pe < 10: return 85
    if pe < 15: return 75
    if pe < 25: return 55
    if pe < 40: return 35
    if pe < 60: return 20
    return 10


def _score_pb(pb: float) -> int:
    """PB score: lower is better (cheaper relative to book value).

    PB < 1:    below book value (85)
    PB 1-2:    fair (65)
    PB 2-5:    expensive (40)
    PB 5-10:   very expensive (20)
    PB > 10:   extreme (10)
    """
    if pb is None or pb <= 0:
        return 50
    if pb < 1: return 85
    if pb < 2: return 65
    if pb < 5: return 40
    if pb < 10: return 20
    return 10


def _score_roe(roe: float) -> int:
    """ROE score: higher is better (more efficient).

    ROE > 25%: excellent (85)
    ROE 15-25%: good (70)
    ROE 10-15%: average (55)
    ROE 5-10%: below average (35)
    ROE < 5%: poor (15)
    """
    if roe is None:
        return 50
    roe_pct = roe * 100 if roe < 1 else roe  # handle both 0.25 and 25 formats
    if roe_pct > 25: return 85
    if roe_pct > 15: return 70
    if roe_pct > 10: return 55
    if roe_pct > 5: return 35
    return 15


def _score_dividend(dividend_yield: float) -> int:
    """Dividend yield score: moderate is best.

    High yield (> 5%): could be value trap (40)
    Moderate (2-5%): good income (70)
    Low (0.5-2%): growth stock (55)
    Zero (0%): no dividend (50)
    """
    if dividend_yield is None or dividend_yield <= 0:
        return 50
    dy = dividend_yield * 100 if dividend_yield < 1 else dividend_yield
    if dy > 8: return 30    # suspiciously high, possible value trap
    if dy > 5: return 40
    if dy > 2: return 70
    if dy > 0.5: return 55
    return 50


def _score_profit_margin(margin: float) -> int:
    """Profit margin: higher is better."""
    if margin is None:
        return 50
    m = margin * 100 if abs(margin) < 1 else margin
    if m > 30: return 80
    if m > 20: return 70
    if m > 10: return 55
    if m > 5: return 40
    if m > 0: return 30
    return 15  # negative margin


def _score_debt(debt_to_equity: float) -> int:
    """Debt-to-equity: lower is safer.

    D/E < 0.5: very safe (80)
    D/E 0.5-1: moderate (60)
    D/E 1-2: elevated (40)
    D/E 2-3: high risk (25)
    D/E > 3: dangerous (10)
    """
    if debt_to_equity is None:
        return 50
    de = debt_to_equity / 100 if debt_to_equity > 10 else debt_to_equity
    if de < 0.5: return 80
    if de < 1: return 60
    if de < 2: return 40
    if de < 3: return 25
    return 10


# ============================================================
# Combined Valuation Score
# ============================================================

def _score_to_signal(score: int) -> str:
    if score >= 80: return "strong_buy"
    if score >= 65: return "buy"
    if score >= 55: return "hold"
    if score >= 45: return "watch"
    if score >= 35: return "reduce"
    return "sell"


def analyze_valuation(symbol: str) -> dict:
    """Valuation analysis: weighted combination of fundamental metrics.

    Weights:
      PE:    30% (most important for value investing)
      PB:    20%
      ROE:   25% (profitability matters)
      Dividend: 10%
      Profit margin: 10%
      Debt:  5% (safety factor)

    Returns: {score, signal, sub_scores, data, summary}
    """
    data = _get_valuation_data(symbol)

    sub_scores = {
        "pe": _score_pe(data["PE"]),
        "pb": _score_pb(data["PB"]),
        "roe": _score_roe(data["ROE"]),
        "dividend": _score_dividend(data["dividend_yield"]),
        "profit_margin": _score_profit_margin(data["profit_margin"]),
        "debt": _score_debt(data["debt_to_equity"]),
    }

    weights = {"pe": 0.30, "pb": 0.20, "roe": 0.25,
               "dividend": 0.10, "profit_margin": 0.10, "debt": 0.05}

    final_score = max(0, min(100, int(sum(sub_scores[k] * weights[k] for k in weights))))
    signal = _score_to_signal(final_score)

    # Format helpers
    def _fmt_pct(v):
        if v is None: return "-"
        return f"{v*100:.1f}%" if abs(v) < 5 else f"{v:.1f}%"

    def _fmt_cap(v):
        if v is None: return "-"
        if v >= 1e12: return f"{v/1e12:.2f}T"
        if v >= 1e9: return f"{v/1e9:.1f}B"
        if v >= 1e6: return f"{v/1e6:.1f}M"
        return str(int(v))

    lines = [
        f"[{symbol} Valuation]",
        f"Score: {final_score}/100 -> {_score_to_signal(final_score)}",
        f"Sector: {data['sector']} | Industry: {data['industry']}",
        f"",
        f"PE: {data['PE'] or '-'} (score: {sub_scores['pe']})",
        f"PB: {data['PB'] or '-'} (score: {sub_scores['pb']})",
        f"ROE: {_fmt_pct(data['ROE'])} (score: {sub_scores['roe']})",
        f"Market Cap: {_fmt_cap(data['market_cap'])}",
        f"Dividend: {_fmt_pct(data['dividend_yield'])} (score: {sub_scores['dividend']})",
        f"Profit Margin: {_fmt_pct(data['profit_margin'])} (score: {sub_scores['profit_margin']})",
        f"Debt/Equity: {data['debt_to_equity'] or '-'} (score: {sub_scores['debt']})",
    ]

    return {
        "score": final_score, "signal": signal,
        "sub_scores": sub_scores, "data": data,
        "summary": "\n".join(lines),
    }