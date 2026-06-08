# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd

# 获取VIX数据
vix = yf.Ticker("^VIX")
vix_hist = vix.history(period="1mo")

print("=== VIX 恐慌指数 ===")
print("VIX > 30: 恐慌 (市场大跌)")
print("VIX 20-30: 紧张 (市场波动)")
print("VIX < 20: 平静 (市场稳定)")
print()

print("最近10天 VIX:")
print(vix_hist["Close"].tail(10).round(2))

print()
last_vix = vix_hist["Close"].iloc[-1]
print("当前VIX: {:.2f}".format(last_vix))
if last_vix > 30:
    print("=> 恐慌状态，市场大跌")
elif last_vix > 20:
    print("=> 紧张状态，市场波动")
else:
    print("=> 平静状态，市场稳定")
