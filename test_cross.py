# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="1mo")
close = hist["Close"].tail(10)

ema5 = close.ewm(span=5).mean()
ema10 = close.ewm(span=10).mean()
dif = ema5 - ema10
dea = dif.ewm(span=3).mean()

print("=== DIF和DEA的交叉信号 ===")
print()
print("{:6} {:8} {:8} {:8} {:20}".format("Day", "Close", "DIF", "DEA", "信号"))
print("-" * 60)

for i in range(1, len(close)):
    prev_dif = dif.iloc[i-1]
    prev_dea = dea.iloc[i-1]
    curr_dif = dif.iloc[i]
    curr_dea = dea.iloc[i]
    
    signal = ""
    if prev_dif < prev_dea and curr_dif > curr_dea:
        signal = "金叉 (买入信号)"
    elif prev_dif > prev_dea and curr_dif < curr_dea:
        signal = "死叉 (卖出信号)"
    elif curr_dif > curr_dea:
        signal = "DIF > DEA (看涨)"
    else:
        signal = "DIF < DEA (看跌)"
    
    print("{:6} {:8.2f} {:8.2f} {:8.2f} {}".format(
        "Day{}".format(i+1), close.iloc[i], curr_dif, curr_dea, signal))

print()
print("=== 金叉死叉的含义 ===")
print()
print("金叉 (Golden Cross):")
print("  DIF从下往上穿过DEA")
print("  含义: 短期趋势突然变强，超过长期趋势")
print("  操作: 买入信号")
print()
print("死叉 (Death Cross):")
print("  DIF从上往下穿过DEA")
print("  含义: 短期趋势突然变弱，低于长期趋势")
print("  操作: 卖出信号")
