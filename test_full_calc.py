# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="1mo")
close = hist["Close"].tail(10)

# 计算所有值
ema5 = close.ewm(span=5).mean()
ema10 = close.ewm(span=10).mean()
dif = ema5 - ema10
dea = dif.ewm(span=3).mean()

print("=== 完整10天计算过程 ===")
print()
print("Step 1: 原始收盘价")
print("-" * 60)
for i in range(len(close)):
    print("Day{:2d}: ${:.2f}".format(i+1, close.iloc[i]))

print()
print("Step 2: 计算EMA5和EMA10")
print("-" * 60)
for i in range(len(close)):
    print("Day{:2d}: EMA5={:.2f}, EMA10={:.2f}".format(i+1, ema5.iloc[i], ema10.iloc[i]))

print()
print("Step 3: DIF = EMA5 - EMA10")
print("-" * 60)
for i in range(len(close)):
    print("Day{:2d}: DIF = {:.2f} - {:.2f} = {:.2f}".format(
        i+1, ema5.iloc[i], ema10.iloc[i], dif.iloc[i]))

print()
print("Step 4: DEA = DIF的3日EMA")
print("-" * 60)
print("公式: DEA_today = DIF_today * 0.5 + DEA_yesterday * 0.5")
print()
for i in range(len(close)):
    if i == 0:
        print("Day{:2d}: DEA = {:.2f} (第一天，直接等于DIF)".format(i+1, dea.iloc[i]))
    else:
        prev_dea = dea.iloc[i-1]
        print("Day{:2d}: DEA = {:.2f} * 0.5 + {:.2f} * 0.5 = {:.2f}".format(
            i+1, dif.iloc[i], prev_dea, dea.iloc[i]))

print()
print("=== 最终汇总表 ===")
print("-" * 60)
print("{:6} {:8} {:8} {:8} {:8} {:8}".format("Day", "Close", "EMA5", "EMA10", "DIF", "DEA"))
print("-" * 60)
for i in range(len(close)):
    print("{:6} {:8.2f} {:8.2f} {:8.2f} {:8.2f} {:8.2f}".format(
        "Day{}".format(i+1), close.iloc[i], ema5.iloc[i], ema10.iloc[i], dif.iloc[i], dea.iloc[i]))
