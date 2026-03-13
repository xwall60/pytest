# #wwa9210f02a1e0aec4,R0vrTevBNCaAmXeXYeXTLbmgOWje68roOVGr_pajOHo,WangLeiLei,1000002
import requests
import json
from r2_uploader import upload_png_to_r2

import pandas as pd
csv_file = '/home/xwall/data/stockdata.csv'
# ===== 1) 配置区（按你的应用信息修改） =====
CORP_ID = "wwa9210f02a1e0aec4"          # 企业ID
CORP_SECRET = "R0vrTevBNCaAmXeXYeXTLbmgOWje68roOVGr_pajOHo"  # 应用密钥
AGENT_ID = 1000002                      # 应用AgentId（整数）
TO_USER = "WangLeiLei"                        # 也可以用 userid 列表： "leo.wang|alice.zhang"


def get_access_token():
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    r = requests.get(url, params={"corpid": CORP_ID, "corpsecret": CORP_SECRET}, timeout=10)
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {data}")
    return data["access_token"]

def send_news(access_token: str, title: str, desc: str, jump_url: str, picurl: str):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    payload = {
        "touser": TO_USER,
        "msgtype": "news",
        "agentid": AGENT_ID,
        "news": {
            "articles": [{
                "title": title,
                "description": desc,
                "url": jump_url,
                "picurl": picurl  # 必须是公网 HTTPS 地址
            }]
        }
    }
    r = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=10)
    return r.json()

def send_mpnews(access_token: str, title: str, content_html: str, digest: str, thumb_media_id: str = None):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    article = {
        "title": title,
        "content": content_html,
        "digest": digest,
        "show_cover_pic": 1
    }
    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id
    payload = {
        "touser": TO_USER,
        "msgtype": "mpnews",
        "agentid": AGENT_ID,
        "mpnews": {"articles": [article]},
        "enable_duplicate_check": 1,
        "duplicate_check_interval": 1800
    }
    r = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=10)
    return r.json()

def send_txtnews(access_token: str, content: str):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

    payload = {
        "touser": TO_USER,
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {
            "content": content
        },
        "safe": "0"
    }

    
    r = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=10)
    return r.json()

def upload_image(access_token: str, file_path: str) -> str:
    """
    上传图片临时素材，返回 media_id。
    - 请求为 multipart/form-data
    - 文件字段名必须是 'media'
    """
    url = "https://qyapi.weixin.qq.com/cgi-bin/media/upload"
    params = {"access_token": access_token, "type": "image"}
    with open(file_path, "rb") as f:
        files = {"media": (file_path.split("/")[-1], f, "application/octet-stream")}
        resp = requests.post(url, params=params, files=files, timeout=30)
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"upload failed: {data}")
    return data["media_id"]


def read_csv_last_row_values_pd(file_path: str, encoding: str = "utf-8"):
    df = pd.read_csv(file_path, encoding=encoding)
    if df.empty:
        raise ValueError("CSV 文件为空。")
    last = df.iloc[-1]  # 最后一行（Series）
    # iloc 使用 0-based 索引；下面取第 1、3、4 个值
    v1 = last.iloc[0]
    v2 = last.iloc[1] if len(last) >= 2 else None
    v4 = last.iloc[3] if len(last) >= 4 else None
    return last.to_list(), v1, v2, v4



if __name__ == "__main__":
    # 1) 上传本地 PNG 到 R2，并拿到返回值
    LOCAL_PNG_PATH = "/home/xwall/data/bi_chart.png"
    r2 = upload_png_to_r2(LOCAL_PNG_PATH)

    print("R2 返回：", r2)
    public_url = r2["public_url"]
    # presigned_url = r2["presigned_url"]

    # 2) 获取企业微信 token
    token = get_access_token()
    media_id = upload_image(token, LOCAL_PNG_PATH)

    last_row, v1, v2, v4=read_csv_last_row_values_pd(csv_file)
    # 3A) 若你有公开 URL，推荐使用 `news`
    # if public_url:
    #     resp = send_news(
    #         access_token=token,
    #         title="系统公告",
    #         desc="点击查看详情",
    #         jump_url=public_url,
    #         picurl=public_url
    #     )
    #     print("NEWS 发送结果：", resp)
    # else:
        # 3B) 若无公开 URL（桶为私有）：用 `mpnews`，正文插图采用预签名 URL
    content_html = f"""
                    <p><strong>市场状态</strong></p>
                    <ul><li>日期：{v1}</li><li>总市值：{v2} (万亿)</li><li>巴菲特指数：{v4*100}%</li></ul>
                    <p>{public_url}</p>
                    <p>点击链接查看趋势</p>
                    """
    resp = send_mpnews(
            access_token=token,
            title="市场状态",
            content_html=content_html,
            digest=f"总市值：{v2} (万亿)\n巴菲特指数：{v4*100} %",
            thumb_media_id=media_id
        )
   
    print("MPNEWS 发送结果：", resp)

    if v4 >= 0.75:
       resp1 =  send_txtnews(token,"📉📉📉警告📉📉📉\n到达75%，考虑出清")
       print("TXTNEWS 发送结果：", resp1)
    elif v4 <= 0.55:
       resp1 = send_txtnews(token,"🚩🚩🚩建议🚩🚩🚩\n到达55%，考虑进入")
       print("TXTNEWS 发送结果：", resp1)
   

  



