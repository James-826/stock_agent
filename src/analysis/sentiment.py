# -*- coding: utf-8 -*-
"""Sentiment Analyzer: market sentiment layer.

Three sub-scores combined:
  vix:      30% weight (market-wide fear level)
  news:     40% weight (company-specific sentiment via keywords)
  momentum: 30% weight (price action reflects mood)

Each produces 0-100 score. Weighted average = final sentiment score.
"""

import httpx
import os
from typing import List, Dict, Any


# ============================================================
# VIX Fear Index (moved from old trend.py)
# ============================================================

def get_vix() -> dict:
    """VIX fear index via Yahoo Finance.

    VIX < 15: calm (70) | 15-20: normal (55) | 20-25: cautious (40)
    VIX 25-30: tense (30) | > 30: panic (20)

    Returns: {VIX, signal, score (0-100), error}
    """
    try:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        with httpx.Client(proxy=proxy, timeout=10) as client:
            resp = client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            meta = resp.json()["chart"]["result"][0]["meta"]
            vix_value = round(meta["regularMarketPrice"], 2)
            if vix_value < 15: score, signal = 70, "calm"
            elif vix_value < 20: score, signal = 55, "normal"
            elif vix_value < 25: score, signal = 40, "cautious"
            elif vix_value < 30: score, signal = 30, "tense"
            else: score, signal = 20, "panic"
            return {"VIX": vix_value, "signal": signal, "score": score, "error": None}
    except Exception as e:
        return {"VIX": None, "signal": "error", "score": 50, "error": str(e)}


# ============================================================
# News Sentiment (keyword-based, no LLM call)
# ============================================================

BULLISH_KEYWORDS = [
    "surge", "rally", "soar", "jump", "gain", "rise", "beat", "exceed",
    "outperform", "upgrade", "buy", "bull", "boom", "record", "growth",
    "profit", "strong", "optimistic", "recovery", "breakthrough",
    "partnership", "expand", "innovative",
]

BEARISH_KEYWORDS = [
    "crash", "plunge", "drop", "fall", "decline", "miss", "disappoint",
    "downgrade", "sell", "bear", "fear", "recession", "inflation", "risk",
    "loss", "weak", "pessimistic", "lawsuit", "ban", "tariff", "sanction", "cut",
]


def analyze_news_sentiment(news_items: List[Dict[str, str]]) -> dict:
    """Keyword-based news sentiment scoring.

    Each news title+summary scanned for bullish/bearish keywords.
    Net sentiment normalized to 0-100.

    Returns: {score, signal, bullish_hits, bearish_hits, news_count}
    """
    if not news_items:
        return {"score": 50, "signal": "neutral", "bullish_hits": 0,
                "bearish_hits": 0, "news_count": 0, "error": None}

    total_bullish = 0
    total_bearish = 0

    for item in news_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        for kw in BULLISH_KEYWORDS:
            if kw.lower() in text:
                total_bullish += 1
        for kw in BEARISH_KEYWORDS:
            if kw.lower() in text:
                total_bearish += 1

    total = total_bullish + total_bearish
    if total == 0:
        score = 50
    else:
        net_ratio = (total_bullish - total_bearish) / total
        score = max(10, min(90, int(50 + net_ratio * 40)))

    if score >= 75: signal = "very_bullish"
    elif score >= 60: signal = "bullish"
    elif score >= 40: signal = "neutral"
    elif score >= 25: signal = "bearish"
    else: signal = "very_bearish"

    return {"score": score, "signal": signal, "bullish_hits": total_bullish,
            "bearish_hits": total_bearish, "news_count": len(news_items), "error": None}


# ============================================================
# Price Momentum
# ============================================================

def calculate_price_momentum(df) -> dict:
    """Short-term price momentum: 5-day and 20-day returns."""
    close = df["Close"]
    if len(close) < 20:
        return {"momentum_5d": 0, "momentum_20d": 0, "score": 50,
                "signal": "neutral", "error": "insufficient data"}

    mom_5d = round(float((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100), 2)
    mom_20d = round(float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100), 2)

    score_5d = max(10, min(90, int(50 + mom_5d * 4)))
    score_20d = max(10, min(90, int(50 + mom_20d * 2)))
    score = int(score_5d * 0.6 + score_20d * 0.4)

    if score >= 70: signal = "euphoric"
    elif score >= 60: signal = "optimistic"
    elif score >= 40: signal = "neutral"
    elif score >= 30: signal = "anxious"
    else: signal = "panic"

    return {"momentum_5d": mom_5d, "momentum_20d": mom_20d,
            "score": score, "signal": signal, "error": None}


# ============================================================
# Combined Sentiment Score
# ============================================================

def _score_to_signal(score: int) -> str:
    """Unified 6-level signal."""
    if score >= 80: return "strong_buy"
    if score >= 65: return "buy"
    if score >= 55: return "hold"
    if score >= 45: return "watch"
    if score >= 35: return "reduce"
    return "sell"


def analyze_sentiment(symbol: str, df=None, news_items: List[Dict] = None) -> dict:
    """Combined sentiment: VIX 30% + News 40% + Momentum 30%.

    Returns: {score, signal, sub_scores, vix, news_sentiment, momentum, summary}
    """
    vix_result = get_vix()
    news_result = analyze_news_sentiment(news_items or [])
    momentum_result = calculate_price_momentum(df) if df is not None else {
        "score": 50, "signal": "neutral", "momentum_5d": 0, "momentum_20d": 0, "error": "no data"}

    weights = {"vix": 0.30, "news": 0.40, "momentum": 0.30}
    sub_scores = {"vix": vix_result["score"], "news": news_result["score"],
                  "momentum": momentum_result["score"]}

    final_score = max(0, min(100, int(
        sub_scores["vix"] * weights["vix"] +
        sub_scores["news"] * weights["news"] +
        sub_scores["momentum"] * weights["momentum"]
    )))

    signal = _score_to_signal(final_score)

    vix_cn = {"calm": "calm", "normal": "normal", "cautious": "cautious",
              "tense": "tense", "panic": "panic"}
    lines = [
        f"[{symbol} Sentiment]",
        f"Score: {final_score}/100",
        f"VIX: {vix_result.get('VIX', '-')} ({vix_result['signal']})",
        f"News: {news_result['signal']} (bull:{news_result['bullish_hits']}/bear:{news_result['bearish_hits']}/{news_result['news_count']} items)",
        f"Momentum: 5d {momentum_result.get('momentum_5d', 0):+.1f}% / 20d {momentum_result.get('momentum_20d', 0):+.1f}%",
    ]

    return {
        "score": final_score, "signal": signal, "sub_scores": sub_scores,
        "vix": vix_result, "news_sentiment": news_result,
        "momentum": momentum_result, "summary": "\n".join(lines),
    }