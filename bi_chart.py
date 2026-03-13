import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import csv
# plt.rcParams['font.family'] = "WenQuanYi Zen Hei"
# matplotlib.rcParams['font.family'] = 'WenQuanYi Zen Hei'
# # 避免负号显示异常
# matplotlib.rcParams['axes.unicode_minus'] = False
fig_path='/home/xwall/data/bi_chart.png'
# 读取 CSV 文件
df = pd.read_csv('/home/xwall/data/stockdata.csv')  # 请确保文件名正确

# 将 'date' 列转换为日期格式
df['date'] = pd.to_datetime(df['date'])

# 按日期排序（可选）
df = df.sort_values('date')
x=df['date']
y=df['BI']
# 设置上下限
upper_limit = 0.75
lower_limit = 0.55



# 绘制折线图
plt.figure(figsize=(20, 9))
plt.plot(x, y, marker='o', linestyle='-', color='#4682B4')
plt.title('BI Chart')
plt.xlabel('Date')
plt.ylabel('BI')
plt.grid(True)

# 高于上限的区域
plt.fill_between(x, y,  upper_limit, where=(y > upper_limit),
                 interpolate=True, color='red', alpha=0.5, label='High')

# 低于下限的区域
plt.fill_between(x, y,  lower_limit, where=(y < lower_limit),
                 interpolate=True, color='green', alpha=0.5, label='Low')

# 添加上下限线
plt.axhline(upper_limit, color='red', linestyle='--', linewidth=1)
plt.axhline(lower_limit, color='green', linestyle='--', linewidth=1)


plt.legend()
plt.tight_layout()
plt.savefig(fig_path)
# plt.show()
print("BI Chart has been created")
