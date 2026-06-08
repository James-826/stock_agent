# -*- coding: utf-8 -*-
"""Scoring Engine: unified fusion of all three analysis layers.

Architecture:
  trend.py -> technical score (0-100)
  sentiment.py -> sentiment score (0-100)
  valuation_score.py -> valuation score (0-100)

  engine.py -> final score = weighted average
             + confidence calibration
             + signal mapping

This is the SINGLE source of truth for final scores.
All other modules (api.py, frontend) read from here.
"""

from typing import Dict, Any, Optional


# Default weights (configurable per analysis mode)
DEFAULT_WEIGHTS = {
    "technical": 0.40,   # Price action is most actionable
    "sentiment": 0.25,   # Market mood affects short-term
    "valuation": 0.35,   # Fundamentals matter for long-term
}

# Quick mode: rely more on technical (faster, fewer API calls)
QUICK_WEIGHTS = {
    "technical": 0.55,
    "sentiment": 0.25,
    "valuation": 0.20,
}


def _score_to_signal(score: int) -> str:
    """Unified 6-level signal. This is the ONLY place thresholds are defined."""
    if score >= 80: return "strong_buy"
    if score >= 65: return "buy"
    if score >= 55: return "hold"
    if score >= 45: return "watch"
    if score >= 35: return "reduce"
    return "sell"


def _score_to_signal_cn(signal: str) -> str:
    """Chinese signal labels."""
    mapping = {
        "strong_buy": "强烈买入", "buy": "买入", "hold": "持有",
        "watch": "观望", "reduce": "减仓", "sell": "卖出"
    }
    return mapping.get(signal, signal)


def _confidence_level(score: int) -> str:
    """Confidence: how far from neutral (50)?"""
    spread = abs(score - 50)
    if spread >= 30: return "high"
    if spread >= 15: return "medium"
    return "low"


def _confidence_level_cn(level: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(level, level)


def fuse_scores(
    technical: Dict[str, Any],
    sentiment: Dict[str, Any],
    valuation: Dict[str, Any],
    weights: Dict[str, float] = None,
    calibration_factor: float = 1.0,
) -> Dict[str, Any]:
    """Fuse three analysis layers into a final score.

    Args:
        technical: output from analyze_trend() -> has "score" key
        sentiment: output from analyze_sentiment() -> has "score" key
        valuation: output from analyze_valuation() -> has "score" key
        weights: optional custom weights (default: DEFAULT_WEIGHTS)
        calibration_factor: 0.5-1.5, from memory/calibration.py

    Returns: {
        score, signal, confidence, confidence_level,
        block_scores, weights, calibration_applied,
        sub_scores (aggregated from all layers),
        summary
    }
    """
    w = weights or DEFAULT_WEIGHTS

    tech_score = technical.get("score", 50)
    sent_score = sentiment.get("score", 50)
    val_score = valuation.get("score", 50)

    # Weighted average
    raw_score = (
        tech_score * w["technical"] +
        sent_score * w["sentiment"] +
        val_score * w["valuation"]
    )

    # Apply calibration (if historical data is sufficient)
    calibrated = calibration_factor != 1.0
    if calibrated:
        # Calibration shifts score toward 50 (less extreme) when accuracy is low
        # and toward the original when accuracy is high
        raw_score = 50 + (raw_score - 50) * calibration_factor

    final_score = max(0, min(100, int(raw_score)))

    signal = _score_to_signal(final_score)
    confidence = round(min(abs(final_score - 50) / 50, 1.0), 2)
    conf_level = _confidence_level(final_score)

    # Aggregate sub-scores from all layers
    all_sub_scores = {}
    if "sub_scores" in technical:
        for k, v in technical["sub_scores"].items():
            all_sub_scores[f"tech_{k}"] = v
    if "sub_scores" in sentiment:
        for k, v in sentiment["sub_scores"].items():
            all_sub_scores[f"sent_{k}"] = v
    if "sub_scores" in valuation:
        for k, v in valuation["sub_scores"].items():
            all_sub_scores[f"val_{k}"] = v

    # Build opinion list (for frontend multi-agent display)
    opinions = [
        {
            "agent_name": "technical",
            "signal": _score_to_signal(tech_score),
            "confidence": round(min(abs(tech_score - 50) / 50, 1.0), 2),
            "reasoning": f"Technical: {tech_score}/100 | trend: {technical.get('trend_state', '-')} | strength: {technical.get('trend_strength', '-')}",
            "score": tech_score,
        },
        {
            "agent_name": "sentiment",
            "signal": _score_to_signal(sent_score),
            "confidence": round(min(abs(sent_score - 50) / 50, 1.0), 2),
            "reasoning": f"Sentiment: {sent_score}/100 | VIX: {sentiment.get('vix', {}).get('VIX', '-')} | news: {sentiment.get('news_sentiment', {}).get('signal', '-')}",
            "score": sent_score,
        },
        {
            "agent_name": "valuation",
            "signal": _score_to_signal(val_score),
            "confidence": round(min(abs(val_score - 50) / 50, 1.0), 2),
            "reasoning": f"Valuation: {val_score}/100 | PE: {valuation.get('data', {}).get('PE', '-')} | PB: {valuation.get('data', {}).get('PB', '-')}",
            "score": val_score,
        },
    ]

    # Summary
    lines = [
        f"=== Final Score: {final_score}/100 ===",
        f"Signal: {_score_to_signal_cn(signal)} ({signal})",
        f"Confidence: {_confidence_level_cn(conf_level)} ({confidence*100:.0f}%)",
        f"",
        f"Block Scores:",
        f"  Technical:  {tech_score}/100 (weight: {w['technical']*100:.0f}%)",
        f"  Sentiment:  {sent_score}/100 (weight: {w['sentiment']*100:.0f}%)",
        f"  Valuation:  {val_score}/100 (weight: {w['valuation']*100:.0f}%)",
    ]
    if calibrated:
        lines.append(f"  Calibration: factor={calibration_factor:.2f}")

    return {
        "score": final_score,
        "signal": signal,
        "signal_cn": _score_to_signal_cn(signal),
        "confidence": confidence,
        "confidence_level": conf_level,
        "confidence_level_cn": _confidence_level_cn(conf_level),
        "block_scores": {
            "technical": tech_score,
            "sentiment": sent_score,
            "valuation": val_score,
        },
        "weights": w,
        "calibration_applied": calibrated,
        "calibration_factor": calibration_factor,
        "opinions": opinions,
        "sub_scores": all_sub_scores,
        "summary": "\n".join(lines),
    }