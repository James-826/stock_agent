# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
close = hist["Close"]

# 计算RSI
def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

rsi14 = calc_rsi(close, 14)

print("=== RSI 核心概念 ===")
print("RSI = 最近涨的幅度 / (涨的幅度 + 跌的幅度) * 100")
print("范围: 0-100")
print()
print("RSI > 70: 超买 (涨太多，可能要跌)")
print("RSI < 30: 超卖 (跌太多，可能要涨)")
print()

print("=== NVDA 最近10天 RSI ===")
result = pd.DataFrame({"Close": close, "RSI14": rsi14})
print(result.tail(10).round(2))

print()
print("=== RSI 解读 ===")
last_rsi = rsi14.iloc[-1]
print("当前RSI: {:.2f}".format(last_rsi))
if last_rsi > 70:
    print("=> 超买区域，涨太多，可能要回调")
elif last_rsi < 30:
    print("=> 超卖区域，跌太多，可能要反弹")
else:
    print("=> 正常区域，没有明显信号")
