# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="6mo")
close = hist["Close"]

# MACD的核心：两条EMA的差值
# EMA = Exponential Moving Average（指数加权平均，近期数据权重更大）
ema12 = close.ewm(span=12).mean()  # 12日EMA
ema26 = close.ewm(span=26).mean()  # 26日EMA

dif = ema12 - ema26                  # DIF线（快线 - 慢线）
dea = dif.ewm(span=9).mean()         # DEA线（DIF的9日EMA，信号线）
macd_bar = (dif - dea) * 2           # MACD柱状图（红绿柱）

print("=== MACD 核心概念 ===")
print("DIF = 12日EMA - 26日EMA (快慢线的差)")
print("DEA = DIF的9日EMA (信号线)")
print("MACD柱 = (DIF - DEA) * 2 (红绿柱)")
print()

result = pd.DataFrame({
    "Close": close,
    "EMA12": ema12,
    "EMA26": ema26,
    "DIF": dif,
    "DEA": dea,
    "MACD": macd_bar
})

print("=== Last 10 days ===")
print(result.tail(10).round(2))

print()
print("=== MACD Signal Interpretation ===")
last_dif = dif.iloc[-1]
last_dea = dea.iloc[-1]
last_macd = macd_bar.iloc[-1]
prev_dif = dif.iloc[-2]
prev_dea = dea.iloc[-2]

print("DIF: {:.4f}".format(last_dif))
print("DEA: {:.4f}".format(last_dea))
print("MACD Bar: {:.4f}".format(last_macd))
print()

if last_dif > last_dea:
    print("DIF > DEA => Positive momentum (bullish)")
else:
    print("DIF < DEA => Negative momentum (bearish)")

if prev_dif < prev_dea and last_dif > last_dea:
    print("GOLDEN CROSS: DIF just crossed above DEA => Buy signal!")
elif prev_dif > prev_dea and last_dif < last_dea:
    print("DEATH CROSS: DIF just crossed below DEA => Sell signal!")
else:
    print("No crossover today")
