"""检查Excel文件的列名"""
import pandas as pd

excel_path = r'D:\work\oilMCP\well_data.xlsx'

# 读取前几行
df = pd.read_excel(excel_path, nrows=3)

print("Excel列名:")
print(df.columns.tolist())
print("\n前3行数据:")
print(df.head(3))
