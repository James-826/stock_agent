# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf

ticker = yf.Ticker("NVDA")
hist = ticker.history(period="6mo")
close = hist["Close"]

# 短期组 (交易者)
short_periods = [3, 5, 8, 10, 12, 15]
short_emas = pd.DataFrame()
for p in short_periods:
    short_emas[f"EMA{p}"] = close.ewm(span=p).mean()

# 长期组 (投资者)
long_periods = [30, 35, 40, 45, 50, 60]
long_emas = pd.DataFrame()
for p in long_periods:
    long_emas[f"EMA{p}"] = close.ewm(span=p).mean()

print("=== GMMA 顾比多重移动平均线 ===")
print()
print("短期组 (交易者): EMA3,5,8,10,12,15")
print("长期组 (投资者): EMA30,35,40,45,50,60")
print()

# 计算短期组和长期组的平均值
short_avg = short_emas.mean(axis=1)
long_avg = long_emas.mean(axis=1)

print("=== 最近10天 ===")
print("{:12} {:10} {:10} {:10}".format("Date", "ShortAvg", "LongAvg", "信号"))
print("-" * 50)

for i in range(-10, 0):
    date = close.index[i].strftime("%m-%d")
    s_avg = short_avg.iloc[i]
    l_avg = long_avg.iloc[i]
    
    if s_avg > l_avg:
        signal = "看涨"
    else:
        signal = "看跌"
    
    print("{:12} {:10.2f} {:10.2f} {:10}".format(date, s_avg, l_avg, signal))

print()
print("=== 当前状态 ===")
last_short = short_avg.iloc[-1]
last_long = long_avg.iloc[-1]
print("短期组均值: {:.2f}".format(last_short))
print("长期组均值: {:.2f}".format(last_long))
if last_short > last_long:
    print("=> 短期组在长期组上方，看涨")
else:
    print("=> 短期组在长期组下方，看跌")
