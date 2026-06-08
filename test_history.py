# -*- coding: utf-8 -*-
import sys
import os
os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")
sys.path.insert(0, "src")

from memory.history import AnalysisHistory, AnalysisRecord
from datetime import datetime, timedelta

print("=== Analysis History Test ===")
print()

# Create history instance
history = AnalysisHistory("test_history.db")

# Simulate saving analysis records
print("Saving analysis records...")

# Record 1: Yesterday
record1 = AnalysisRecord(
    symbol="NVDA",
    date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    score=65,
    signal="buy",
    trend="bullish",
    price_at_analysis=210.50,
    indicators={"MA": "bullish", "RSI": 45, "MACD": "golden_cross"},
    summary="NVDA shows bullish signals"
)
id1 = history.save_analysis(record1)
print(f"  Saved record {id1}: {record1.date} - {record1.signal} @ ${record1.price_at_analysis}")

# Record 2: Today
record2 = AnalysisRecord(
    symbol="NVDA",
    date=datetime.now().strftime("%Y-%m-%d"),
    score=56,
    signal="neutral",
    trend="sideways",
    price_at_analysis=205.10,
    indicators={"MA": "sideways", "RSI": 34, "MACD": "neutral"},
    summary="NVDA is neutral"
)
id2 = history.save_analysis(record2)
print(f"  Saved record {id2}: {record2.date} - {record2.signal} @ ${record2.price_at_analysis}")

print()
print("=== Query Recent Analyses ===")
recent = history.get_recent_analyses("NVDA", limit=5)
for record in recent:
    print(f"  {record.date}: {record.signal} (score={record.score}) @ ${record.price_at_analysis}")

print()
print("=== Query by Date ===")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
record = history.get_analysis_by_date("NVDA", yesterday)
if record:
    print(f"  Found: {record.date} - {record.signal} @ ${record.price_at_analysis}")
else:
    print(f"  No record found for {yesterday}")

print()
print("=== Accuracy Stats ===")
stats = history.get_accuracy_stats("NVDA")
print(f"  Total predictions: {stats['total']}")
print(f"  Correct: {stats['correct']}")
print(f"  Accuracy: {stats['accuracy']}%")

# Clean up
os.remove("test_history.db")
print()
print("Test database cleaned up.")
