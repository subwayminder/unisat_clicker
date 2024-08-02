import requests
from settings import ADS_API_URL, SLOW_MODE_VALUE
from playwright.async_api import async_playwright, expect, Playwright, Page, BrowserContext
from src.account_dto import AccountDTO

async def open_profile(ap: Playwright, account: AccountDTO) -> BrowserContext:
    ads_api_response = requests.get(ADS_API_URL + '/api/v1/browser/start?user_id=' + account.get('profile_id')).json()
    browser = await ap.chromium.connect_over_cdp(ads_api_response['data']['ws']['puppeteer'], slow_mo=int(SLOW_MODE_VALUE))
    context = browser.contexts[0]
