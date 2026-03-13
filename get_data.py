from playwright.sync_api import sync_playwright
from datetime import datetime
from bs4 import BeautifulSoup
import csv
import os

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # 使用 Chromium，无需安装 Chrome
    page = browser.new_page()
    page.goto("https://data.eastmoney.com/gzfx/scgk.html")
    page.wait_for_selector("tbody tr")
   
    # 获取第一个 tr 元素
    first_tr = page.query_selector("tbody tr")
    
    today_sse = first_tr.inner_html()
    browser.close()
 



# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(today_sse , 'html.parser')
td_elements = soup.find_all('td')
data_values = [td.get_text(strip=True) for td in td_elements]
# print(data_values[0])
# formatted_date = datetime.strptime(data_values[0],"%Y%m%d")
# print(formatted_date)
# CSV 文件路径
csv_file = '/home/xwall/data/stockdata.csv'
date_obj = datetime.strptime(data_values[0], "%Y-%m-%d")

# 手动去除前导零
month = date_obj.strftime("%m").lstrip("0")
day = date_obj.strftime("%d").lstrip("0")
year = date_obj.strftime("%Y")

a_date=f"{month}/{day}/{year}"
all_value=float(data_values[5].removesuffix('万亿'))
gdp=140
bi=round(all_value/gdp,4)
new_rows=[a_date,all_value,gdp,bi]
# print(new_rows)
# 写入或追加数据
with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file,lineterminator='\n') 
    writer.writerow(new_rows)
print("数据已成功追加保存到 CSV 文件中。")



