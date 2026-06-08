# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="1mo")
close = hist["Close"]

# 只取最近10天，方便看
close = close.tail(10)

print("=== Step 1: 原始收盘价 ===")
for i in range(len(close)):
    print("Day{}: ${:.2f}".format(i+1, close.iloc[i]))

print()
print("=== Step 2: 计算EMA12和EMA26 ===")
# 简化：用5日EMA和10日EMA来演示（原理一样）
ema5 = close.ewm(span=5).mean()
ema10 = close.ewm(span=10).mean()

print("EMA5(短期趋势): ", [round(x, 2) for x in ema5.values])
print("EMA10(长期趋势): ", [round(x, 2) for x in ema10.values])

print()
print("=== Step 3: DIF = EMA5 - EMA10 ===")
dif = ema5 - ema10
for i in range(len(close)):
    print("Day{}: DIF = {:.2f} - {:.2f} = {:.2f}".format(
        i+1, ema5.iloc[i], ema10.iloc[i], dif.iloc[i]))

print()
print("=== Step 4: DEA = DIF的3日EMA ===")
dea = dif.ewm(span=3).mean()
print("公式: DEA_today = DIF_today * 0.5 + DEA_yesterday * 0.5")
print()
for i in range(len(close)):
    if i == 0:
        print("Day{}: DEA = {:.2f} (初始值)".format(i+1, dea.iloc[i]))
    else:
        prev_dea = dea.iloc[i-1]
        manual = dif.iloc[i] * 0.5 + prev_dea * 0.5
        print("Day{}: DIF={:.2f}, DEA={:.2f} (手动计算: {:.2f}x0.5 + {:.2f}x0.5 = {:.2f})".format(
            i+1, dif.iloc[i], dea.iloc[i], dif.iloc[i], prev_dea, manual))

print()
print("=== 最终结果 ===")
result = pd.DataFrame({"Close": close, "DIF": dif, "DEA": dea})
print(result.round(2))
