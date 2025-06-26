import os
import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 帳號密碼（請從環境變數讀取，GitHub Actions 安全）
username_str = os.getenv("NGI_USERNAME")
password_str = os.getenv("NGI_PASSWORD")

# 下載資料夾 (GitHub Actions 工作目錄下的 pdf_downloads)
download_dir = os.path.join(os.getcwd(), "pdf_downloads")
os.makedirs(download_dir, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_dir,
    "plugins.always_open_pdf_externally": True,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
}
options.add_experimental_option("prefs", prefs)
options.add_argument("--headless=new")  # 新版 headless 模式
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36"
)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("https://www.naturalgasintel.com/account/login/")

    # 等待登入欄位，並且加錯誤捕獲來截圖跟存 HTML
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "id_username")))
    except Exception:
        with open("login_fail_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("login_fail_screenshot.png")
        raise Exception("登入頁面 id_username 欄位找不到，已截圖並存 HTML")

    driver.find_element(By.ID, "id_username").send_keys(username_str)
    driver.find_element(By.ID, "field-password").send_keys(password_str)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()

    # 進入 Daily Gas Price Index 頁面
    driver.get("https://www.naturalgasintel.com/news/daily-gas-price-index/")

    # 點擊接受 cookie（如果有）
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookie_button.click()
    except Exception:
        print("cookie 接受按鈕不存在，跳過")

    # 點擊 "View Issue"
    try:
        view_issue_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "View Issue"))
        )
        view_issue_button.click()
    except Exception:
        # 如果找不到，截圖存 HTML
        with open("view_issue_fail.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("view_issue_fail.png")
        raise Exception("找不到 'View Issue' 按鈕，已截圖並存 HTML")

    # 等待跳轉並取得 URL
    time.sleep(5)
    current_url = driver.current_url
    print(f"跳轉後 URL: {current_url}")

    # 抓日期
    match = re.search(r'dg(\d{8})', current_url)
    if not match:
        raise Exception("無法從 URL 中擷取日期")
    date_str = match.group(1)
    pdf_filename = f"NGI_daily_index_{date_str}.pdf"
    pdf_path = os.path.join(download_dir, pdf_filename)

    # 用 requests Session 下載 PDF，帶 cookie
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36",
        "Referer": "https://www.naturalgasintel.com/news/daily-gas-price-index/",
    }

    resp = session.get(current_url, headers=headers)
    if resp.status_code == 200:
        with open(pdf_path, "wb") as f:
            f.write(resp.content)
        print(f"✅ PDF 下載成功: {pdf_filename}")
    else:
        raise Exception(f"❌ PDF 下載失敗，HTTP 狀態碼: {resp.status_code}")

except Exception as e:
    print(f"發生錯誤: {e}")

finally:
    driver.quit()

