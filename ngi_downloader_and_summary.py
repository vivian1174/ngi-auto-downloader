import os
import re
import time
import base64
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 讀取環境變數（帳號、密碼、Groq API）
username_str = os.getenv("NGI_USERNAME")
password_str = os.getenv("NGI_PASSWORD")
groq_api_key = os.getenv("GROQ_API_KEY")

# 檔案儲存資料夾
download_dir = os.path.abspath("downloads")
os.makedirs(download_dir, exist_ok=True)

# Selenium 設定（headless）
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
prefs = {
    "download.default_directory": download_dir,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # 登入 NGI
    driver.get('https://www.naturalgasintel.com/account/login/')
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'id_username')))
    driver.find_element(By.ID, 'id_username').send_keys(username_str)
    driver.find_element(By.ID, 'field-password').send_keys(password_str)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()

    # 前往 Daily Gas Page
    driver.get('https://www.naturalgasintel.com/news/daily-gas-price-index/')
    cookie_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
    )
    cookie_button.click()

    view_issue_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "View Issue"))
    )
    view_issue_button.click()

    time.sleep(5)
    current_url = driver.current_url
    match = re.search(r'dg(\d{8})', current_url)
    if not match:
        raise Exception("❌ 無法從 URL 中抓取日期")
    date_str = match.group(1)
    pdf_filename = f"NGI_daily_index_{date_str}.pdf"
    pdf_path = os.path.join(download_dir, pdf_filename)

    # 使用 Session + Cookie 下載 PDF
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.naturalgasintel.com/news/daily-gas-price-index/',
    }

    resp = session.get(current_url, headers=headers)
    if resp.status_code == 200:
        with open(pdf_path, 'wb') as f:
            f.write(resp.content)
        print(f"✅ PDF 已下載：{pdf_filename}")
    else:
        raise Exception(f"❌ PDF 下載失敗，狀態碼：{resp.status_code}")

finally:
    driver.quit()

# 🧠 將 PDF 轉成 base64 並送給 Groq
def summarize_pdf_with_groq(file_path, api_key):
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system",
                "content": "你是一位專業的天然氣市場分析助理。請根據這份 PDF 文件內容，萃取出六項今日最重要的市場觀察，並以繁體中文條列說明。每項格式為「標題：說明」。"
            },
            {
                "role": "user",
                "content": f"[PDF Base64]\n{encoded_pdf}"
            }
        ]
    }

    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

summary = summarize_pdf_with_groq(pdf_path, groq_api_key)

# ✏️ 儲存摘要
summary_file = os.path.join(download_dir, f"summary_{date_str}.txt")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write(summary)

print("📌 LLaMA3 摘要結果：\n")
print(summary)
