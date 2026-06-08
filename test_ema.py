# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
close = hist["Close"]

# 1. EMA vs SMA的区别
sma5 = close.rolling(5).mean()      # SMA: 简单平均，每天权重一样
ema5 = close.ewm(span=5).mean()     # EMA: 指数加权，近期权重更大

print("=== EMA vs SMA 对比 ===")
print("注意看：EMA比SMA反应更快（更贴近当前价格）")
compare = pd.DataFrame({"Close": close, "SMA5": sma5, "EMA5": ema5})
print(compare.tail(8).round(2))

print()
print("=== DIF 是什么（用具体数字解释）===")
ema12 = close.ewm(span=12).mean()
ema26 = close.ewm(span=26).mean()
dif = ema12 - ema26

print("假设某一天：")
print("  EMA12 = 200 (短期趋势的平均价格)")
print("  EMA26 = 195 (长期趋势的平均价格)")
print("  DIF = 200 - 195 = +5 (短期比长期高5块，说明近期涨得快)")
print()
print("再假设另一天：")
print("  EMA12 = 190")
print("  EMA26 = 195")
print("  DIF = 190 - 195 = -5 (短期比长期低5块，说明近期跌得快)")
print()

print("=== NVDA 实际的 DIF 变化 ===")
dif_compare = pd.DataFrame({"Close": close, "EMA12": ema12, "EMA26": ema26, "DIF": dif})
print(dif_compare.tail(8).round(2))

print()
print("=== DEA 是什么 ===")
dea = dif.ewm(span=9).mean()
print("DEA = DIF的9日EMA")
print("就是把DIF再做一次EMA平滑，得到一条更平滑的线")
print()
print("实际数据：")
dea_compare = pd.DataFrame({"DIF": dif, "DEA": dea})
print(dea_compare.tail(8).round(2))
