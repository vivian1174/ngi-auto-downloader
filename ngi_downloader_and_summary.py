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

# 帳號密碼（從 GitHub Actions 的環境變數讀取）
username_str = os.getenv("NGI_USERNAME")
password_str = os.getenv("NGI_PASSWORD")

# 下載資料夾（確保存在）
download_dir = "pdf_downloads"
os.makedirs(download_dir, exist_ok=True)

# 設定 Selenium Chrome Driver
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": os.path.abspath(download_dir),
    "plugins.always_open_pdf_externally": True,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
}
options.add_experimental_option("prefs", prefs)
options.add_argument("--headless=new")
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

    # 等待登入欄位，如果找不到就截圖
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "id_username")))
    except Exception:
        with open("login_fail_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("login_fail_screenshot.png")
        raise Exception("登入頁面找不到 id_username 欄位，已截圖")

    # 輸入帳號密碼並登入
    driver.find_element(By.ID, "id_username").send_keys(username_str)
    driver.find_element(By.ID, "field-password").send_keys(password_str)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()

    # 進入每日價格頁面
    driver.get("https://www.naturalgasintel.com/news/daily-gas-price-index/")

    # 嘗試點擊 Cookie 接受按鈕
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookie_button.click()
    except Exception:
        print("沒有 cookie 按鈕，跳過")

    # 點擊 "View Issue"
    try:
        view_issue_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "View Issue"))
        )
        print("找到按鈕:", view_issue_button)

        old_url = driver.current_url

        # 改為 JS 點擊，較穩定
        driver.execute_script("arguments[0].click();", view_issue_button)
        print("已觸發 JS 點擊 'View Issue'")

        # 等待 URL 改變
        WebDriverWait(driver, 15).until(EC.url_changes(old_url))
        current_url = driver.current_url
        print(f"✅ 跳轉後 URL: {current_url}")

    except Exception:
        current_url = driver.current_url
        print(f"⚠️ URL 沒有變化（仍為: {current_url}），可能點擊失敗或內容未載入")
        with open("view_issue_fail.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("view_issue_fail.png")
        raise Exception("找不到 'View Issue' 按鈕或無法跳轉，已截圖")

    # 跳轉並取得 URL
    time.sleep(5)
    current_url = driver.current_url
    print(f"跳轉後 URL: {current_url}")

    # 抓出日期字串
    match = re.search(r'dg(\d{8})', current_url)
    if not match:
        raise Exception("無法從 URL 中擷取日期")
    date_str = match.group(1)
    pdf_filename = f"NGI_daily_index_{date_str}.pdf"
    pdf_path = os.path.join(download_dir, pdf_filename)

    # 找出 PDF 連結並點擊下載
    try:
        pdf_link_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.pdf')]"))
        )
        pdf_url = pdf_link_elem.get_attribute("href")
        print(f"🔗 PDF 下載連結: {pdf_url}")

        pdf_link_elem.click()
        print("📥 已觸發瀏覽器下載 PDF")

        # 等待下載完成
        for i in range(30):
            if os.path.exists(pdf_path):
                print(f"✅ PDF 已成功下載: {pdf_filename}")
                break
            time.sleep(1)
        else:
            print("❌ PDF 檔案未在 30 秒內下載完成")

    except Exception as e:
        print(f"❌ 找不到 PDF 或下載失敗: {e}")

finally:
    driver.quit()
