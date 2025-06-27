import asyncio
import os
from playwright.async_api import async_playwright
import requests

NGI_USERNAME = os.getenv("NGI_USERNAME")
NGI_PASSWORD = os.getenv("NGI_PASSWORD")
TARGET_DATE = "20250627"
SAVE_PDF_PATH = f"NGI_{TARGET_DATE}.pdf"
LOGIN_URL = "https://www.naturalgasintel.com/my-account/"
TARGET_PAGE = f"https://www.naturalgasintel.com/protected_documents/dg{TARGET_DATE}/"

async def download_pdf(pdf_url):
    print(f"📥 嘗試下載 PDF: {pdf_url}")
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(SAVE_PDF_PATH, "wb") as f:
            f.write(response.content)
        print(f"✅ PDF 已儲存為 {SAVE_PDF_PATH}")
    else:
        print(f"❌ 無法下載 PDF，狀態碼: {response.status_code}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🔐 登入中...")
        await page.goto(LOGIN_URL)
        await page.screenshot(path="step_1_login_page.png")

        await page.fill('input[name="username"]', NGI_USERNAME)
        await page.fill('input[name="password"]', NGI_PASSWORD)
        await page.click('button[type="submit"]')

        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="step_2_after_login.png")
        print("✅ 登入完成")

        print(f"🔗 前往期刊頁面: {TARGET_PAGE}")
        await page.goto(TARGET_PAGE)
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="step_3_journal_page.png")

        # 嘗試找出 PDF 連結
        links = await page.query_selector_all("a")
        found = False
        for link in links:
            href = await link.get_attribute("href")
            if href and href.endswith(".pdf") and "NGIMethodology" not in href:
                print(f"✅ 發現 PDF 連結: {href}")
                await download_pdf(href)
                found = True
                break

        if not found:
            print("❌ 沒找到期刊 PDF")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())


