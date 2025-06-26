import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# 從環境變數讀帳號密碼（設定於 GitHub Secrets）
username = os.getenv("NGI_USERNAME")
password = os.getenv("NGI_PASSWORD")

# PDF 下載目錄
download_dir = "./pdf_downloads"
os.makedirs(download_dir, exist_ok=True)

# 建立 requests session
session = requests.Session()

# Step 1: 開啟登入頁面，取得 CSRF token（NGI 是 Django 架構）
login_url = "https://www.naturalgasintel.com/account/login/"
res = session.get(login_url)
soup = BeautifulSoup(res.text, "html.parser")

csrf_token_tag = soup.find("input", {"name": "csrfmiddlewaretoken"})
csrf_token = csrf_token_tag["value"] if csrf_token_tag else None

# Step 2: 帳密登入
login_data = {
    "username": username,
    "password": password,
}
if csrf_token:
    login_data["csrfmiddlewaretoken"] = csrf_token
    session.headers.update({"Referer": login_url})

login_response = session.post(login_url, data=login_data)

if login_response.status_code not in [200, 302] or "Logout" not in login_response.text:
    print("❌ 登入失敗，請檢查帳號密碼或網站變動")
    exit()

print("✅ 成功登入 NGI")

# Step 3: 抓 Daily Gas Index 主頁
daily_url = "https://www.naturalgasintel.com/news/daily-gas-price-index/"
res = session.get(daily_url)
soup = BeautifulSoup(res.text, "html.parser")

# Step 4: 找出 "View Issue" 的連結（連到 PDF 頁面）
view_issue_link = soup.find("a", string=re.compile("View Issue", re.IGNORECASE))

if not view_issue_link:
    print("❌ 無法找到 'View Issue' 連結")
    exit()

issue_url = view_issue_link["href"]
if not issue_url.startswith("http"):
    issue_url = "https://www.naturalgasintel.com" + issue_url

print(f"🔗 View Issue URL: {issue_url}")

# Step 5: 抓 PDF 連結（一般會在這頁）
issue_page = session.get(issue_url)
pdf_link_match = re.search(r'https://[^"]+\.pdf', issue_page.text)

if not pdf_link_match:
    print("❌ 沒找到 PDF 下載連結")
    exit()

pdf_url = pdf_link_match.group(0)

# Step 6: 抓日期作為檔名
date_str = re.search(r'dg(\d{8})', pdf_url)
date_label = date_str.group(1) if date_str else datetime.now().strftime("%Y%m%d")
filename = f"NGI_daily_index_{date_label}.pdf"
filepath = os.path.join(download_dir, filename)

# Step 7: 下載 PDF
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": issue_url,
}
pdf_res = session.get(pdf_url, headers=headers)

if pdf_res.status_code == 200:
    with open(filepath, "wb") as f:
        f.write(pdf_res.content)
    print(f"✅ PDF 已下載：{filename}")
else:
    print(f"❌ PDF 下載失敗，狀態碼: {pdf_res.status_code}")
