# -*- coding: utf-8 -*-
"""Confidence Calibration

Phase 3.2: Why calibrate confidence?

Problem: Agent's score is always 0-100, but is it reliable?
- If Agent predicted "buy" 10 times, and 8 times were correct
- Then when Agent says "buy" again, confidence should be higher
- This is like a weather forecast: "70% chance of rain"

Solution: Track prediction accuracy, adjust confidence

Mathematical basis:
- Bayes' theorem: P(outcome | prediction) = P(prediction | outcome) * P(outcome) / P(prediction)
- Simple version: accuracy = correct / total
- Adjusted score = original_score * accuracy_factor
"""

from dataclasses import dataclass
from typing import List, Optional
import sqlite3
from datetime import datetime, timedelta


@dataclass
class CalibrationResult:
    """Calibration result for a stock.
    
    Why dataclass?
    - Clear structure for LLM consumption
    - Easy to serialize to JSON
    """
    symbol: str
    total_predictions: int
    correct_predictions: int
    accuracy: float  # 0-1
    confidence_factor: float  # 0.5-1.5, multiplier for score
    sample_size_sufficient: bool  # Need >= 30 samples for reliable calibration
    summary: str


class ConfidenceCalibrator:
    """Calibrate confidence based on historical accuracy.
    
    Why this design?
    - Simple accuracy calculation
    - Confidence factor adjusts scores
    - Minimum sample size for reliability
    """
    
    def __init__(self, db_path: str = "analysis_history.db"):
        """Initialize calibrator.
        
        Args:
            db_path: SQLite database file path
        """
        self.db_path = db_path
        self.min_sample_size = 30  # Minimum predictions for reliable calibration
    
    def calibrate(self, symbol: str) -> CalibrationResult:
        """Calculate calibration for a stock.
        
        Args:
            symbol: stock code
        
        Returns:
            CalibrationResult with accuracy and confidence factor
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all analyses for this stock
            rows = conn.execute("""
                SELECT * FROM analysis_history 
                WHERE symbol = ? 
                ORDER BY date ASC
            """, (symbol,)).fetchall()
            
            total = len(rows)
            
            if total < 2:
                return CalibrationResult(
                    symbol=symbol,
                    total_predictions=total,
                    correct_predictions=0,
                    accuracy=0.0,
                    confidence_factor=1.0,
                    sample_size_sufficient=False,
                    summary=f"Insufficient data ({total} predictions). Need >= 2."
                )
            
            # Calculate accuracy
            correct = 0
            for i in range(1, total):
                prev = rows[i-1]
                curr = rows[i]
                
                prev_signal = prev["signal"]
                price_change = curr["price_at_analysis"] - prev["price_at_analysis"]
                
                # Check if prediction was correct
                if prev_signal in ["strong_buy", "buy"] and price_change > 0:
                    correct += 1
                elif prev_signal in ["strong_sell", "sell"] and price_change < 0:
                    correct += 1
                elif prev_signal == "neutral":
                    correct += 1
            
            accuracy = correct / (total - 1)
            
            # Calculate confidence factor
            # If accuracy > 0.5, boost confidence
            # If accuracy < 0.5, reduce confidence
            confidence_factor = 0.5 + accuracy  # Range: 0.5 - 1.5
            
            # Check sample size
            sample_sufficient = total >= self.min_sample_size
            
            # Generate summary
            summary = f"{symbol} Calibration:\n"
            summary += f"Total predictions: {total}\n"
            summary += f"Correct: {correct}\n"
            summary += f"Accuracy: {accuracy:.1%}\n"
            summary += f"Confidence factor: {confidence_factor:.2f}\n"
            summary += f"Sample size sufficient: {'Yes' if sample_sufficient else 'No'}"
            
            return CalibrationResult(
                symbol=symbol,
                total_predictions=total,
                correct_predictions=correct,
                accuracy=accuracy,
                confidence_factor=confidence_factor,
                sample_size_sufficient=sample_sufficient,
                summary=summary
            )
    
    def adjust_score(self, original_score: int, calibration: CalibrationResult) -> int:
        """Adjust score based on calibration.
        
        Args:
            original_score: original score from trend analyzer (0-100)
            calibration: CalibrationResult
        
        Returns:
            Adjusted score (0-100)
        """
        if not calibration.sample_size_sufficient:
            # Not enough data, return original score
            return original_score
        
        # Apply confidence factor
        adjusted = original_score * calibration.confidence_factor
        
        # Clamp to 0-100
        return max(0, min(100, int(adjusted)))
