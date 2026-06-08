# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent/src")

from analysis.data_loader import load_kline
from analysis.trend import analyze_trend, get_etf_premium

# Test with a Chinese QDII ETF (invests in US stocks)
print("=== Testing ETF Premium/Discount ===")
print()

# Test 513100 (纳指 ETF)
print("Testing 513100 (纳指 ETF)...")
try:
    premium_result = get_etf_premium("513100.SS")
    print(f"Market Price: {premium_result.get('market_price')}")
    print(f"NAV: {premium_result.get('nav')}")
    print(f"Premium Rate: {premium_result.get('premium_rate')}%")
    print(f"Signal: {premium_result.get('signal')}")
except Exception as e:
    print(f"Error: {e}")

print()

# Test NVDA (not an ETF, should have no premium data)
print("Testing NVDA (stock, not ETF)...")
try:
    premium_result = get_etf_premium("NVDA")
    print(f"Market Price: {premium_result.get('market_price')}")
    print(f"NAV: {premium_result.get('nav')}")
    print(f"Premium Rate: {premium_result.get('premium_rate')}%")
    print(f"Signal: {premium_result.get('signal')}")
except Exception as e:
    print(f"Error: {e}")

print()
print("=== Key Insight ===")
print("ETF premium is only meaningful for ETFs, not individual stocks.")
print("For stocks, we focus on technical indicators and valuation.")
