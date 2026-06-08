# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
close = hist["Close"]

# 布林带计算
ma20 = close.rolling(20).mean()
std20 = close.rolling(20).std()
upper = ma20 + 2 * std20  # 上轨
lower = ma20 - 2 * std20  # 下轨

print("=== 布林带核心概念 ===")
print("中轨 = 20日均线 (MA20)")
print("上轨 = 中轨 + 2倍标准差 (价格波动的上限)")
print("下轨 = 中轨 - 2倍标准差 (价格波动的下限)")
print()
print("价格在上下轨之间波动是正常的")
print("价格突破上轨: 超买，可能要跌回来")
print("价格跌破下轨: 超卖，可能要涨回去")
print()

result = pd.DataFrame({
    "Close": close,
    "MA20": ma20,
    "Upper": upper,
    "Lower": lower
})
print("=== NVDA 最近10天布林带 ===")
print(result.tail(10).round(2))

print()
print("=== 布林带解读 ===")
last_close = close.iloc[-1]
last_upper = upper.iloc[-1]
last_lower = lower.iloc[-1]
last_ma20 = ma20.iloc[-1]

print("当前价格: ${:.2f}".format(last_close))
print("上轨: ${:.2f}".format(last_upper))
print("中轨: ${:.2f}".format(last_ma20))
print("下轨: ${:.2f}".format(last_lower))
print()

if last_close > last_upper:
    print("=> 价格突破上轨，超买，可能要回调")
elif last_close < last_lower:
    print("=> 价格跌破下轨，超卖，可能要反弹")
else:
    print("=> 价格在正常范围内波动")
