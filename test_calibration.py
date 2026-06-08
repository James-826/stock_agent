# -*- coding: utf-8 -*-
import sys
import os
os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")
sys.path.insert(0, "src")

from memory.history import AnalysisHistory, AnalysisRecord
from memory.calibration import ConfidenceCalibrator
from datetime import datetime, timedelta
import random

print("=== Confidence Calibration Test ===")
print()

# Create history with sample data
history = AnalysisHistory("test_calibration.db")

# Simulate 35 predictions (enough for calibration)
print("Simulating 35 predictions...")
for i in range(35):
    date = (datetime.now() - timedelta(days=35-i)).strftime("%Y-%m-%d")
    
    # Random signal
    signals = ["buy", "sell", "neutral"]
    signal = random.choice(signals)
    
    # Random price (with some trend)
    base_price = 200 + random.uniform(-20, 20)
    
    record = AnalysisRecord(
        symbol="NVDA",
        date=date,
        score=random.randint(40, 80),
        signal=signal,
        trend="bullish" if signal == "buy" else "bearish" if signal == "sell" else "sideways",
        price_at_analysis=base_price,
        indicators={},
        summary=f"Prediction: {signal}"
    )
    history.save_analysis(record)

print(f"  Saved {35} predictions")

print()
print("=== Calibration Results ===")
calibrator = ConfidenceCalibrator("test_calibration.db")
calibration = calibrator.calibrate("NVDA")

print(f"Symbol: {calibration.symbol}")
print(f"Total predictions: {calibration.total_predictions}")
print(f"Correct: {calibration.correct_predictions}")
print(f"Accuracy: {calibration.accuracy:.1%}")
print(f"Confidence factor: {calibration.confidence_factor:.2f}")
print(f"Sample sufficient: {calibration.sample_size_sufficient}")

print()
print("=== Score Adjustment Example ===")
original_score = 70
adjusted_score = calibrator.adjust_score(original_score, calibration)
print(f"Original score: {original_score}")
print(f"Adjusted score: {adjusted_score}")
print(f"Adjustment: {original_score} -> {adjusted_score} ({calibration.confidence_factor:.2f}x)")

# Clean up
os.remove("test_calibration.db")
print()
print("Test database cleaned up.")
