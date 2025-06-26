import os
import re
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 帳號密碼從環境變數中讀取
username_str = os.getenv("NGI_USERNAME")
password_str = os.getenv("NGI_PASSWORD")

# 建立下載資料夾
download_dir = os.path.abspath("downloads")
os.makedirs(download_dir, exist_ok=True)

# Selenium 設定（headless）
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_dir,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920x1080')
options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # 1️⃣ 登入
    driver.get("https://www.naturalgasintel.com/account/login/")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "id_username")))
    driver.find_element(By.ID, "id_username").send_keys(username_str)
    driver.find_element(By.ID, "field-password").send_keys(password_str)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()

    # 2️⃣ 進入 Daily Gas Page 並接受 cookie
    driver.get("https://www.naturalgasintel.com/news/daily-gas-price-index/")
    cookie_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
    )
    cookie_btn.click()

    # 3️⃣ 點選 View Issue
    view_issue_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "View Issue"))
    )
    view_issue_button.click()

    # 4️⃣ 等待頁面跳轉 & 擷取 PDF 頁面 URL
    time.sleep(5)
    current_url = driver.current_url
    print(f"View Issue 頁面 URL: {current_url}")

    # 從 URL 抓日期
    match = re.search(r'dg(\d{8})', current_url)
    if not match:
        raise Exception("❌ 無法從 URL 中抓取日期")
    date_str = match.group(1)
    file_name = f"NGI_daily_index_{date_str}.pdf"
    pdf_path = os.path.join(download_dir, file_name)

    # 5️⃣ 使用 requests + cookies 抓頁面內容（PDF）
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.naturalgasintel.com/news/daily-gas-price-index/"
    }

    response = session.get(current_url, headers=headers)
    if response.status_code == 200:
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        print(f"✅ PDF 已成功下載至：{pdf_path}")
    else:
        raise Exception(f"❌ PDF 下載失敗，狀態碼：{response.status_code}")

finally:
    driver.quit()
