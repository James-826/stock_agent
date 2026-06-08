# -*- coding: utf-8 -*-

# 假设我们有5天的DIF值
dif_values = [0, -0.02, -0.19, -0.95, 1.37]

print("=== DEA 计算演示 ===")
print()
print("假设DIF值: ", dif_values)
print()

# DEA = DIF的EMA，权重0.5
dea_values = []
for i, dif in enumerate(dif_values):
    if i == 0:
        dea = dif  # 第一天直接等于DIF
    else:
        dea = dif * 0.5 + dea_values[i-1] * 0.5  # 今天的DIF占50%，昨天的DEA占50%
    dea_values.append(dea)
    
    print("Day{}: DIF={:.2f}".format(i+1, dif))
    if i == 0:
        print("      DEA = DIF = {:.2f} (第一天直接等于DIF)".format(dea))
    else:
        print("      DEA = DIF * 0.5 + 昨天DEA * 0.5")
        print("           = {:.2f} * 0.5 + {:.2f} * 0.5".format(dif, dea_values[i-1]))
        print("           = {:.2f} + {:.2f}".format(dif * 0.5, dea_values[i-1] * 0.5))
        print("           = {:.2f}".format(dea))
    print()

print("=== 最终结果 ===")
print("DIF: ", [round(x, 2) for x in dif_values])
print("DEA: ", [round(x, 2) for x in dea_values])
