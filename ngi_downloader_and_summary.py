import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 讀取帳密
username_str = os.getenv("NGI_USERNAME")
password_str = os.getenv("NGI_PASSWORD")

# 建立下載資料夾
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
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,720")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("https://www.naturalgasintel.com/account/login/")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "id_username")))

    driver.find_element(By.ID, "id_username").send_keys(username_str)
    driver.find_element(By.ID, "field-password").send_keys(password_str)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()

    driver.get("https://www.naturalgasintel.com/news/daily-gas-price-index/")

    # Cookie 同意按鈕
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookie_button.click()
    except:
        pass  # 沒有 cookie 按鈕也 OK

    # 找到 "View Issue" 並取得 href
    view_issue_button = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.LINK_TEXT, "View Issue"))
    )
    issue_url = view_issue_button.get_attribute("href")
    print(f"🔗 即將前往期刊頁面: {issue_url}")
    driver.get(issue_url)

    # 🔍 抓所有 PDF 連結，過濾掉 NGIMethodology
    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
    target_pdf_url = None

    for link in pdf_links:
        href = link.get_attribute("href")
        if "NGIMethodology" not in href and "dg" in href:
            target_pdf_url = href
            break

    if not target_pdf_url:
        raise Exception("❌ 無找到有效 PDF 下載連結")

    print(f"🔗 PDF 下載連結: {target_pdf_url}")

    # 抓日期並命名檔案
    match = re.search(r'dg(\d{8})', issue_url)
    if not match:
        raise Exception("❌ 無法從 URL 擷取日期")
    date_str = match.group(1)
    pdf_filename = f"NGI_daily_index_{date_str}.pdf"
    pdf_path = os.path.join(download_dir, pdf_filename)

    # 使用 JS 直接觸發下載
    driver.execute_script("window.open(arguments[0]);", target_pdf_url)
    print("📥 已開啟 PDF 下載頁面")

    # 等待 PDF 出現
    for _ in range(30):
        if os.path.exists(pdf_path):
            print(f"✅ PDF 已成功下載: {pdf_filename}")
            break
        time.sleep(1)
    else:
        print("❌ PDF 檔案未在 30 秒內下載完成")

except Exception as e:
    print(f"❌ 發生例外錯誤: {e}")
    driver.save_screenshot("error_screenshot.png")
    with open("error_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

finally:
    driver.quit()


