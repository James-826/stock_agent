# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent/src")

from analysis.data_loader import load_kline
from analysis.trend import analyze_trend

# Test with NVDA
print("Loading NVDA data...")
df = load_kline("NVDA", "US", "3mo")
print(f"Data points: {len(df)}")

print()
print("Running comprehensive trend analysis with VIX and valuation...")
result = analyze_trend("NVDA", df)

print()
print(result.summary)

print()
print("=== Detailed Indicators ===")
for indicator, data in result.indicators.items():
    print(f"\n{indicator}:")
    for key, value in data.items():
        print(f"  {key}: {value}")
