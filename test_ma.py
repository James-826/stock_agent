# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
close = hist["Close"]

ma5 = close.rolling(5).mean()
ma10 = close.rolling(10).mean()
ma20 = close.rolling(20).mean()

result = pd.DataFrame({"Close": close, "MA5": ma5, "MA10": ma10, "MA20": ma20})

print("=== Last 10 trading days ===")
print(result.tail(10).round(2))

print()
print("=== MA Alignment (most recent day) ===")
last = result.iloc[-1]
print("Close: {:.2f}".format(last["Close"]))
print("MA5: {:.2f}".format(last["MA5"]))
print("MA10: {:.2f}".format(last["MA10"]))
print("MA20: {:.2f}".format(last["MA20"]))

if last["MA5"] > last["MA10"] > last["MA20"]:
    print("=> BULLISH: short-term MAs above long-term MAs (upward trend)")
elif last["MA5"] < last["MA10"] < last["MA20"]:
    print("=> BEARISH: short-term MAs below long-term MAs (downward trend)")
else:
    print("=> SIDEWAYS: MAs crossing, direction unclear")
