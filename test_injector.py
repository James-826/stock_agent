# -*- coding: utf-8 -*-
import sys
import os
os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")
sys.path.insert(0, "src")

from memory.history import AnalysisHistory, AnalysisRecord
from memory.injector import MemoryInjector
from datetime import datetime, timedelta

print("=== Memory Injector Test ===")
print()

# Create history with sample data
history = AnalysisHistory("test_injector.db")

# Simulate 5 historical analyses
print("Simulating 5 historical analyses...")
for i in range(5):
    date = (datetime.now() - timedelta(days=5-i)).strftime("%Y-%m-%d")
    
    # Simulate different signals
    signals = ["buy", "neutral", "buy", "sell", "neutral"]
    prices = [210.5, 208.3, 212.1, 205.8, 203.2]
    
    record = AnalysisRecord(
        symbol="NVDA",
        date=date,
        score=60 + i * 5,
        signal=signals[i],
        trend="bullish" if signals[i] == "buy" else "bearish" if signals[i] == "sell" else "sideways",
        price_at_analysis=prices[i],
        indicators={"RSI": 45 + i * 3},
        summary=f"Day {i+1} analysis"
    )
    history.save_analysis(record)

print("  Saved 5 records")

print()
print("=== Memory Injection Test ===")
injector = MemoryInjector("test_injector.db")

# Get memory for NVDA
memory_text = injector.inject_memory("NVDA")
print("Memory text:")
print(memory_text)

print()
print("=== Context for Analysis ===")
context = injector.get_context_for_analysis("NVDA")
print(f"Symbol: {context['symbol']}")
print(f"Calibration accuracy: {context['calibration']['accuracy']:.1%}")
print(f"Confidence factor: {context['calibration']['confidence_factor']:.2f}")
print(f"Suggestion: {context['suggestion']}")

# Clean up
os.remove("test_injector.db")
print()
print("Test database cleaned up.")
