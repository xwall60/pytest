
# -*- coding: utf-8 -*-
"""
cpolar 官网后台抓取 + HTML 报告
- 登录 https://dashboard.cpolar.com/login
- 访问 https://dashboard.cpolar.com/status
- 解析在线隧道（账号下所有设备）
- 导出 JSON/CSV/HTML

依赖：requests, beautifulsoup4
安装（Debian/Ubuntu/Armbian）：sudo apt install -y python3-requests python3-bs4

用法示例：
  export CPOLAR_EMAIL="your_email@example.com"
  export CPOLAR_PASSWORD="your_password"
  python3 cpolar_dashboard_fetch.py \
    --out-json /opt/cpolar/online_tunnels.json \
    --out-csv  /opt/cpolar/online_tunnels.csv \
    --out-html /opt/cpolar/online_tunnels.html
"""
import os
import re
import csv
import json
import argparse
import sys
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

DASHBOARD_BASE = "https://dashboard.cpolar.com"
LOGIN_URL = f"{DASHBOARD_BASE}/login"
STATUS_URL = f"{DASHBOARD_BASE}/status"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

def get_csrf_from_login(session: requests.Session) -> Optional[str]:
    resp = session.get(LOGIN_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    inp = soup.find("input", {"name": "csrf_token"})
    return inp.get("value") if inp else None

def login_dashboard(session: requests.Session, email: str, password: str) -> None:
    csrf = get_csrf_from_login(session)
    payload = {"login": email, "password": password}
    if csrf:
        payload["csrf_token"] = csrf
    resp = session.post(LOGIN_URL, data=payload, headers=HEADERS,
                        timeout=20, allow_redirects=True)
    if resp.url.rstrip("/") == LOGIN_URL.rstrip("/"):
        raise RuntimeError("官网后台登录失败：请检查邮箱/密码（或稍后重试）")

def fetch_status_html(session: requests.Session) -> str:
    resp = session.get(STATUS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

def parse_online_tunnels(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table") or soup.find("table", {"class": re.compile(r".*table.*", re.I)})
    if not table:
        raise RuntimeError("未在状态页中找到在线隧道的表格；页面结构可能变化。")

    tunnels = []
    rows = table.find_all("tr")
    body_rows = rows[1:] if len(rows) >= 2 else rows
    for row in body_rows:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue

        name = cols[0].get_text(" ", strip=True)
        a = row.find("a", href=True)
        public_url = a["href"].strip() if a else None

        local_addr = None
        for c in cols:
            txt = c.get_text(" ", strip=True)
            if ":" in txt and not txt.startswith(("http://", "https://", "tcp://")):
                part = txt.split(":")[-1]
                if part.isdigit():
                    local_addr = txt
                    break

        proto = None
        if public_url:
            if public_url.startswith("https://"):
                proto = "https"
            elif public_url.startswith("http://"):
                proto = "http"
            elif public_url.startswith("tcp://"):
                proto = "tcp"

        region = None
        maybe_texts = " ".join(c.get_text(" ", strip=True) for c in cols)
        m = re.search(r"\b(CN|HK|US|TW|EUR|cn|hk|us|tw|eur)\b", maybe_texts)
        if m:
            region = m.group(0)

        if name or public_url:
            tunnels.append({
                "name": name,
                "url": public_url,
                "proto": proto,
                "local": local_addr,
                "region": region,
            })
    return tunnels

def save_json(tunnels: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tunnels, f, ensure_ascii=False, indent=2)

def save_csv(tunnels: List[Dict], path: str) -> None:
    fields = ["name", "proto", "url", "local", "region"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in tunnels:
            w.writerow({k: t.get(k) or "" for k in fields})

def _group_by_name(tunnels: List[Dict]) -> Dict[str, List[Dict]]:
    grouped = {}
    for t in tunnels:
        grouped.setdefault(t.get("name") or "(未命名隧道)", []).append(t)
    return grouped

def save_html(tunnels: List[Dict], path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(tunnels)
    grouped = _group_by_name(tunnels)

    # 简洁样式：自适应暗/亮色，中文表头，协议标签色块
    css = """
:root { color-scheme: light dark; }
body { margin: 24px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif; }
h1 { margin: 0 0 8px; font-size: 20px; }
.meta { color: gray; margin-bottom: 16px; }
.section { margin: 18px 0; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
th { background: #f6f6f6; }
.proto { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; color: #fff; }
.proto-http { background: #0ea5e9; }     /* 青 */
.proto-https { background: #22c55e; }    /* 绿 */
.proto-tcp { background: #f59e0b; }      /* 橙 */
.url a { word-break: break-all; text-decoration: none; color: #2563eb; }
.group-title { font-weight: 600; margin-top: 22px; }
.footer { margin-top: 20px; font-size: 12px; color: gray; }
.count { font-weight: 600; }
    """

    def proto_badge(proto: Optional[str]) -> str:
        if proto == "https":
            cls, text = "proto proto-https", "HTTPS"
        elif proto == "http":
            cls, text = "proto proto-http", "HTTP"
        elif proto == "tcp":
            cls, text = "proto proto-tcp", "TCP"
        else:
            cls, text = "proto", (proto or "未知")
        return f'<span class="{cls}">{text}</span>'

    def render_group(name: str, items: List[Dict]) -> str:
        rows = []
        for t in items:
            rows.append(f"""
<tr>
  <td class="proto">{proto_badge(t.get('proto'))}</td>
  <td class="url">{('%s%s</a>' % (t['url'], t['url'])) if t.get('url') else ''}</td>
  <td>{t.get('local','')}</td>
  <td>{t.get('region','')}</td>
</tr>""")
        return f"""
<div class="section">
  <div class="group-title">隧道：{name}（{len(items)} 条地址）</div>
  <table>
    <thead><tr><th>协议</th><th>公网 URL</th><th>本地地址</th><th>地区</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>"""

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>cpolar 在线隧道报告</title>
<style>{css}</style>
</head>
<body>
  <h1>🌐 cpolar 在线隧道报告</h1>
  <div class="meta">更新时间：{now}　共 <span class="count">{total}</span> 条在线地址（按隧道名称分组）</div>
  {''.join(render_group(name, items) for name, items in grouped.items())}
  <div class="footer">
    数据来源：cpolar 官网后台状态页（账号下所有设备） · {STATUS_URL}
  </div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def run(email: str, password: str, out_json: Optional[str], out_csv: Optional[str],
        out_html: Optional[str], name_filter: Optional[str]) -> List[Dict]:
    sess = requests.Session()
    login_dashboard(sess, email, password)
    html = fetch_status_html(sess)
    tunnels = parse_online_tunnels(html)

    if name_filter:
        tunnels = [t for t in tunnels if t.get("name") and name_filter.lower() in t["name"].lower()]

    if out_json:
        save_json(tunnels, out_json)
    if out_csv:
        save_csv(tunnels, out_csv)
    if out_html:
        save_html(tunnels, out_html)
    return tunnels

def main():
    p = argparse.ArgumentParser(description="抓取 cpolar 官网后台在线隧道列表并生成 HTML 报告")
    p.add_argument("--email", default=os.getenv("CPOLAR_EMAIL"),
                   help="cpolar 登录邮箱（也可用环境变量 CPOLAR_EMAIL）")
    p.add_argument("--password", default=os.getenv("CPOLAR_PASSWORD"),
                   help="cpolar 登录密码（也可用环境变量 CPOLAR_PASSWORD）")
    p.add_argument("--out-json", default=None, help="输出 JSON 文件路径（可选）")
    p.add_argument("--out-csv", default=None, help="输出 CSV 文件路径（可选）")
    p.add_argument("--out-html", default="./online_tunnels.html",
                   help="输出 HTML 报告路径（默认 ./online_tunnels.html）")
    p.add_argument("--filter", default=None, help="按隧道名称关键词过滤（可选）")
    args = p.parse_args()

    if not args.email or not args.password:
        print("缺少邮箱或密码：请使用 --email/--password 或设置环境变量 CPOLAR_EMAIL/CPOLAR_PASSWORD")
        sys.exit(2)

    try:
        tunnels = run(args.email, args.password, args.out_json, args.out_csv, args.out_html, args.filter)
        # 控制台也打印一份简要的 JSON 结果
        print(json.dumps(tunnels, ensure_ascii=False, indent=2))
    except Exception as e:
        print("获取失败：", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
