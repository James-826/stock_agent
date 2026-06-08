# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
close = hist["Close"]

# Step 1: 计算 DIF
ema12 = close.ewm(span=12).mean()
ema26 = close.ewm(span=26).mean()
dif = ema12 - ema26

# Step 2: 计算 DEA = DIF 的 9日 EMA
dea = dif.ewm(span=9).mean()

print("=== DEA 的计算过程 ===")
print("DEA = DIF的9日EMA")
print("公式: DEA_today = DIF_today * (2/10) + DEA_yesterday * (8/10)")
print()

# 手动验证
print("=== 手动验证最后5天 ===")
print("EMA公式: 新值 = 当前值 * 权重 + 昨天EMA * (1-权重)")
print("权重 = 2/(9+1) = 0.2")
print()

for i in range(-5, 0):
    date = dif.index[i].strftime("%m-%d")
    dif_val = dif.iloc[i]
    dea_val = dea.iloc[i]
    
    if i > -5:
        prev_dea = dea.iloc[i-1]
        weight = 2 / (9 + 1)
        manual_dea = dif_val * weight + prev_dea * (1 - weight)
        print("{}: DIF={:.2f}, DEA={:.2f}, 手动计算={:.2f}".format(
            date, dif_val, dea_val, manual_dea))
    else:
        print("{}: DIF={:.2f}, DEA={:.2f} (第一天,无法手动验证)".format(
            date, dif_val, dea_val))
