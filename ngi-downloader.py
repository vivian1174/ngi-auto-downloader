import requests
import os
from datetime import datetime

# 模擬登入後的 Cookie （你要用瀏覽器手動抓）
cookies = {
    "sessionid": os.getenv("NGI_SESSION_ID"),
    "csrftoken": os.getenv("NGI_CSRF_TOKEN"),
    # 其他必要的 cookie 也加進來
}

# 你想抓的 URL（這裡用例子，之後可以動態生成）
today = datetime.today().strftime("%Y%m%d")
url = f"https://www.naturalgasintel.com/wp-content/dg{today}.pdf"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.naturalgasintel.com/news/daily-gas-price-index/",
}

response = requests.get(url, headers=headers, cookies=cookies)

if response.status_code == 200:
    file_name = f"NGI_Daily_{today}.pdf"
    with open(file_name, "wb") as f:
        f.write(response.content)
    print(f"✅ PDF saved: {file_name}")
else:
    print(f"❌ Failed to download PDF. Status: {response.status_code}")
