# -*- coding: utf-8 -*-
import pandas as pd

# 用一个超简单的例子
# 假设我们有7天的DIF值（DIF = EMA12 - EMA26，我们直接假设已知）
dif_series = pd.Series([1, 2, 3, 2, 4, 3, 5])

print("=== 假设我们有7天的DIF值 ===")
print("DIF: ", list(dif_series))

# DEA = DIF的9日EMA，我们简化成3日EMA来看
dea_series = dif_series.ewm(span=3).mean()

print()
print("=== DEA = DIF的3日EMA（简化版）===")
print("公式: DEA_today = DIF_today * 0.5 + DEA_yesterday * 0.5")
print()

for i in range(len(dif_series)):
    date = "Day{}".format(i+1)
    dif_val = dif_series.iloc[i]
    dea_val = dea_series.iloc[i]
    
    if i == 0:
        print("{}: DIF={}, DEA={:.1f} (第一天)".format(date, dif_val, dea_val))
    else:
        prev_dea = dea_series.iloc[i-1]
        manual = dif_val * 0.5 + prev_dea * 0.5
        print("{}: DIF={}, DEA={:.1f}, 手动计算={:.1f}".format(
            date, dif_val, dea_val, manual))

print()
print("=== 关键观察 ===")
print("DIF变化: 1->2->3->2->4->3->5 (波动大)")
print("DEA变化: {:.1f}->{:.1f}->{:.1f}->{:.1f}->{:.1f}->{:.1f}->{:.1f} (更平滑)".format(
    dea_series.iloc[0], dea_series.iloc[1], dea_series.iloc[2],
    dea_series.iloc[3], dea_series.iloc[4], dea_series.iloc[5],
    dea_series.iloc[6]))
