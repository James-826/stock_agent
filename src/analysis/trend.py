# -*- coding: utf-8 -*-
"""Trend Analyzer v2: pure technical analysis module

Design changes from v1:
  v1 mixed VIX, valuation, ETF premium into technical layer -> double-counting
  v2 is pure technical: MA/MACD/RSI/Bollinger + volume + support/resistance

Scoring formula:
  sub_scores = {ma: 0-100, macd: 0-100, rsi: 0-100, bollinger: 0-100}
  base_score = weighted_average(sub_scores, weights)
  volume_bonus = +10/-10/0
  final_score = clamp(base_score + volume_bonus, 0, 100)

Weights: MA 30%, MACD 25%, Bollinger 25%, RSI 20%
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


# ============================================================
# Helper
# ============================================================

def _to_float(val) -> float:
    """numpy float64 -> Python float for JSON serialization."""
    if val is None:
        return 0.0
    if isinstance(val, (np.floating, np.integer)):
        return round(float(val), 4)
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return 0.0
    return round(float(val), 4)


# ============================================================
# Indicator Calculations (pure technical indicators)
# ============================================================

def calculate_macd(close: pd.Series) -> dict:
    """MACD: DIF = EMA12 - EMA26, DEA = DIF EMA9, bar = (DIF-DEA)*2."""
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd_bar = (dif - dea) * 2

    prev_dif, prev_dea = dif.iloc[-2], dea.iloc[-2]
    curr_dif, curr_dea = dif.iloc[-1], dea.iloc[-1]

    signal = "neutral"
    if prev_dif < prev_dea and curr_dif > curr_dea:
        signal = "golden_cross"
    elif prev_dif > prev_dea and curr_dif < curr_dea:
        signal = "death_cross"

    return {
        "DIF": _to_float(dif.iloc[-1]),
        "DEA": _to_float(dea.iloc[-1]),
        "MACD_bar": _to_float(macd_bar.iloc[-1]),
        "signal": signal
    }


def calculate_rsi(close: pd.Series, period: int = 14) -> dict:
    """RSI = 100 - 100/(1+RS). >70 overbought, <30 oversold."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi_value = _to_float(rsi.iloc[-1])
    signal = "neutral"
    if rsi_value > 70:
        signal = "overbought"
    elif rsi_value < 30:
        signal = "oversold"

    return {"RSI": rsi_value, "signal": signal}


def calculate_bollinger(close: pd.Series, period: int = 20) -> dict:
    """Bollinger: middle=MA20, upper/lower = middle +/- 2*std."""
    ma20 = close.rolling(window=period).mean()
    std20 = close.rolling(window=period).std()
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20

    last_close = _to_float(close.iloc[-1])
    last_upper = _to_float(upper.iloc[-1])
    last_lower = _to_float(lower.iloc[-1])
    last_ma20 = _to_float(ma20.iloc[-1])

    band_width = last_upper - last_lower
    position = ((last_close - last_lower) / band_width * 100) if band_width > 0 else 50.0

    signal = "neutral"
    if last_close > last_upper:
        signal = "overbought"
    elif last_close < last_lower:
        signal = "oversold"

    return {
        "upper": last_upper, "middle": last_ma20, "lower": last_lower,
        "position": round(position, 2), "signal": signal
    }


def calculate_ma_alignment(close: pd.Series) -> dict:
    """MA alignment: MA5 > MA10 > MA20 = bullish."""
    ma5 = close.rolling(window=5).mean()
    ma10 = close.rolling(window=10).mean()
    ma20 = close.rolling(window=20).mean()

    last_ma5 = _to_float(ma5.iloc[-1])
    last_ma10 = _to_float(ma10.iloc[-1])
    last_ma20 = _to_float(ma20.iloc[-1])

    signal = "sideways"
    if last_ma5 > last_ma10 > last_ma20:
        signal = "bullish"
    elif last_ma5 < last_ma10 < last_ma20:
        signal = "bearish"

    return {"MA5": last_ma5, "MA10": last_ma10, "MA20": last_ma20, "signal": signal}


# ============================================================
# Volume Analysis (new in v2)
# ============================================================

def calculate_volume_analysis(df: pd.DataFrame) -> dict:
    """Volume-price confirmation.

    volume_ratio = vol_ma5 / vol_ma20
    > 1.5: high volume | 0.7-1.5: normal | < 0.7: low volume

    Signals:
      bullish_confirm: high volume + price up (trend confirmed)
      bearish_confirm: high volume + price down (panic selling)
      bullish_divergence: low volume + price up (weak rally)
      bearish_divergence: low volume + price down (natural pullback)
    """
    if len(df) < 25:
        return {"volume_ratio": 1.0, "signal": "neutral",
                "volume_ma5": 0, "volume_ma20": 0, "error": "insufficient data"}

    volume = df["Volume"]
    vol_ma5 = volume.rolling(window=5).mean()
    vol_ma20 = volume.rolling(window=20).mean()

    curr_vol_ma5 = _to_float(vol_ma5.iloc[-1])
    curr_vol_ma20 = _to_float(vol_ma20.iloc[-1])

    volume_ratio = round(curr_vol_ma5 / curr_vol_ma20, 2) if curr_vol_ma20 > 0 else 1.0

    close = df["Close"]
    price_change_5d = _to_float((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) if len(close) >= 5 else 0

    signal = "neutral"
    if volume_ratio > 1.5:
        signal = "bullish_confirm" if price_change_5d > 0 else "bearish_confirm"
    elif volume_ratio < 0.7:
        signal = "bullish_divergence" if price_change_5d > 0 else "bearish_divergence"

    return {
        "volume_ratio": volume_ratio, "signal": signal,
        "volume_ma5": curr_vol_ma5, "volume_ma20": curr_vol_ma20,
        "price_change_5d": round(price_change_5d * 100, 2)
    }


# ============================================================
# Support / Resistance (new in v2)
# ============================================================

def calculate_support_resistance(df: pd.DataFrame) -> dict:
    """Simple S/R from 60-day high/low."""
    lookback = min(60, len(df))
    recent = df.tail(lookback)
    current_price = _to_float(df["Close"].iloc[-1])
    support = _to_float(recent["Low"].min())
    resistance = _to_float(recent["High"].max())

    support_pct = round((current_price - support) / current_price * 100, 2) if current_price > 0 else 0
    resistance_pct = round((resistance - current_price) / current_price * 100, 2) if current_price > 0 else 0

    return {
        "support": support, "resistance": resistance,
        "support_distance_pct": support_pct, "resistance_distance_pct": resistance_pct
    }


# ============================================================
# Sub-score Calculation (each indicator 0-100 continuous)
# ============================================================

def _score_ma(ma_result: dict) -> int:
    """MA sub-score: alignment + deviation from MA20."""
    signal = ma_result["signal"]
    last_close = ma_result["MA5"]

    if signal == "bullish":
        deviation = (last_close - ma_result["MA20"]) / ma_result["MA20"] * 100 if ma_result["MA20"] > 0 else 0
        if deviation > 10: return 80
        elif deviation > 5: return 90
        elif deviation > 2: return 75
        else: return 65
    elif signal == "bearish":
        deviation = (ma_result["MA20"] - last_close) / ma_result["MA20"] * 100 if ma_result["MA20"] > 0 else 0
        if deviation > 10: return 10
        elif deviation > 5: return 20
        elif deviation > 2: return 35
        else: return 45
    else:
        return 50


def _score_macd(macd_result: dict) -> int:
    """MACD sub-score: crossover + bar direction."""
    signal = macd_result["signal"]
    dif, dea, bar = macd_result["DIF"], macd_result["DEA"], macd_result["MACD_bar"]

    if signal == "golden_cross":
        return 88 if bar > 0 else 78
    elif signal == "death_cross":
        return 12 if bar < 0 else 22
    elif dif > dea:
        return 70 if bar > 0 else 58
    else:
        return 30 if bar < 0 else 42


def _score_rsi(rsi_result: dict) -> int:
    """RSI sub-score: oversold is bullish (high score)."""
    rsi = rsi_result["RSI"]
    if rsi < 20: return 85
    elif rsi < 30: return 75
    elif rsi < 45: return 55 + int((45 - rsi) / 15 * 15)
    elif rsi <= 55: return 50
    elif rsi <= 70: return 50 - int((rsi - 55) / 15 * 15)
    elif rsi <= 80: return 30
    else: return 15


def _score_bollinger(boll_result: dict) -> int:
    """Bollinger sub-score: position 0%=85, 50%=50, 100%=15."""
    pos = boll_result["position"]
    if pos < 0: return 90
    elif pos > 100: return 10
    else: return int(85 - pos * 0.7)


def _score_volume(volume_result: dict) -> int:
    """Volume modifier: +/-10 (not 0-100)."""
    mapping = {
        "bullish_confirm": 10, "bearish_confirm": -10,
        "bullish_divergence": -5, "bearish_divergence": 5, "neutral": 0
    }
    return mapping.get(volume_result.get("signal", "neutral"), 0)


# ============================================================
# Signal Mapping (single source of truth for thresholds)
# ============================================================

def _score_to_signal(score: int) -> str:
    if score >= 80: return "strong_buy"
    if score >= 65: return "buy"
    if score >= 55: return "hold"
    if score >= 45: return "watch"
    if score >= 35: return "reduce"
    return "sell"


# ============================================================
# Trend State & Strength
# ============================================================

def _determine_trend_state(ma_result: dict, macd_result: dict) -> str:
    ma_signal = ma_result["signal"]
    dif_above_dea = macd_result["DIF"] > macd_result["DEA"]
    if ma_signal == "bullish" and dif_above_dea: return "uptrend"
    elif ma_signal == "bearish" and not dif_above_dea: return "downtrend"
    else: return "ranging"


def _determine_trend_strength(sub_scores: dict, volume_result: dict) -> str:
    extreme_count = sum(1 for s in sub_scores.values() if s > 65 or s < 35)
    if volume_result.get("signal") in ("bullish_confirm", "bearish_confirm"):
        extreme_count += 0.5
    if extreme_count >= 3: return "strong"
    elif extreme_count >= 2: return "moderate"
    else: return "weak"


# ============================================================
# Main Entry Point
# ============================================================

def analyze_trend(symbol: str, df: pd.DataFrame) -> dict:
    """Comprehensive technical analysis (technical layer only).

    Returns: score, signal, trend_state, trend_strength,
             sub_scores, volume, support_resistance, indicators, summary
    """
    close = df["Close"]

    ma_result = calculate_ma_alignment(close)
    macd_result = calculate_macd(close)
    rsi_result = calculate_rsi(close)
    boll_result = calculate_bollinger(close)
    volume_result = calculate_volume_analysis(df)
    sr_result = calculate_support_resistance(df)

    sub_scores = {
        "ma": _score_ma(ma_result),
        "macd": _score_macd(macd_result),
        "rsi": _score_rsi(rsi_result),
        "bollinger": _score_bollinger(boll_result),
    }

    weights = {"ma": 0.30, "macd": 0.25, "bollinger": 0.25, "rsi": 0.20}
    base_score = sum(sub_scores[k] * weights[k] for k in weights)
    volume_bonus = _score_volume(volume_result)
    final_score = max(0, min(100, int(base_score + volume_bonus)))

    trend_state = _determine_trend_state(ma_result, macd_result)
    trend_strength = _determine_trend_strength(sub_scores, volume_result)
    signal = _score_to_signal(final_score)

    summary = _build_summary(symbol, final_score, signal, trend_state,
                             trend_strength, sub_scores, volume_result,
                             ma_result, macd_result, rsi_result, boll_result)

    return {
        "score": final_score, "signal": signal,
        "trend_state": trend_state, "trend_strength": trend_strength,
        "sub_scores": sub_scores, "volume": volume_result,
        "support_resistance": sr_result,
        "indicators": {"MA": ma_result, "MACD": macd_result,
                        "RSI": rsi_result, "Bollinger": boll_result},
        "summary": summary,
    }


def _build_summary(symbol, score, signal, trend_state, trend_strength,
                   sub_scores, volume_result, ma, macd, rsi, boll) -> str:
    signal_cn = {"strong_buy": "强烈买入", "buy": "买入", "hold": "持有",
                 "watch": "观望", "reduce": "减仓", "sell": "卖出"}
    trend_cn = {"uptrend": "上升趋势", "downtrend": "下降趋势", "ranging": "震荡盘整"}
    strength_cn = {"strong": "强", "moderate": "中等", "weak": "弱"}
    vol_cn = {"bullish_confirm": "放量上涨(确认)", "bearish_confirm": "放量下跌(恐慌)",
              "bullish_divergence": "缩量上涨(背离)", "bearish_divergence": "缩量下跌(回调)", "neutral": "量能正常"}

    lines = [
        f"【{symbol} 技术面分析】",
        f"综合评分: {score}/100 -> {signal_cn.get(signal, signal)}",
        f"趋势: {trend_cn.get(trend_state, trend_state)} | 强度: {strength_cn.get(trend_strength, trend_strength)}",
        "",
        "子评分 (满分100):",
        f"  均线(MA): {sub_scores['ma']}  |  MACD: {sub_scores['macd']}",
        f"  RSI: {sub_scores['rsi']}  |  布林带: {sub_scores['bollinger']}",
        "",
        f"量价: {vol_cn.get(volume_result.get('signal', 'neutral'), '未知')} (量比: {volume_result.get('volume_ratio', '-')})",
        "",
        f"MA: MA5={ma['MA5']} MA10={ma['MA10']} MA20={ma['MA20']} [{ma['signal']}]",
        f"MACD: DIF={macd['DIF']} DEA={macd['DEA']} bar={macd['MACD_bar']} [{macd['signal']}]",
        f"RSI: {rsi['RSI']} [{rsi['signal']}]",
        f"Bollinger: upper={boll['upper']} mid={boll['middle']} lower={boll['lower']} pos={boll['position']}%",
    ]
    return "\n".join(lines)
