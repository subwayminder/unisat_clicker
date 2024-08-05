import re
import asyncio
import sys
import requests
import random
import csv
import time
import datetime
import sys
import os
from src.retry import retry
from src.gas_checker import check_gas
from playwright.async_api import async_playwright, expect, Playwright, Page, BrowserContext
from typing import TypedDict, List
from loguru import logger
from src.account_dto import AccountDTO
from typing import Union
from settings import ADS_API_URL, TX_COUNT_MIN, TX_COUNT_MAX, SLOW_MODE_VALUE, ACCOUNT_LATENCY_MIN, ACCOUNT_LATENCY_MAX, QUANTITY_THREADS, TEST_RUN, ROUND_LATENCY
from concurrent.futures import ProcessPoolExecutor
from src.functions import open_profile

@check_gas
@retry
async def unisat_script(ap: Playwright, account: AccountDTO):
    try:
        unisat_url = 'https://unisat.io/runes/inscribe'
        mint_list = requests.get('https://api.unisat.space/query-v4/runes/info-list?rune=&start=0&limit=10&complete=no&sort=sixHourMints').json()['data']['detail']
        random_rune = random.choice(mint_list)
        context = await open_profile(ap, account)

        # Переход на страницу случайной руны
        unisat_page = await context.new_page()
        await unisat_page.bring_to_front()
        await unisat_page.goto('https://unisat.io/runes/inscribe?rune=' + random_rune['spacedRune'])
        await unisat_page.wait_for_load_state()
        # Клик далее по руне
        next_button = unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div[2]/div[5]/div[5]').first
        await asyncio.sleep(5)
        await next_button.click()
        # Логин через кошелек, клик sign
        await unisat_page.locator('//*[@id="__next"]/div[1]/div[2]/div[3]').click()
        await unisat_page.locator('//*[@id="__next"]/div[5]/div/div[3]/div[1]').click()
        await asyncio.sleep(5)
        unisat_wallet_page = context.pages[-1]
        await unlock_wallet(unisat_wallet_page, account.get('password'))
        await asyncio.sleep(5)
        unisat_wallet_page = context.pages[-1]
        await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[2]/div/div[2]').click()
        # Выбираем минимальный газ
        await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div/div[5]/div[2]/div[1]').click()
        # Кликаем customize и откручиваем сатоши слайдер до минимума
        await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div/div[6]/div[1]/div[1]/span[2]').first.click()
        await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div/div[6]/div[2]/div[2]/div[2]/input').first.fill('330')
        # Клик чекбокса
        await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div/label/span[1]/input').check()
        # Клейм
        await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[2]/div/div[8]').click()
        # Скипаем алерт
        # if (await unisat_page.query_selector('text="I have read and agreed to the risk warning"') is not None):
        #     await alerts.get_by_text('I have read and agreed to the risk warning').first.click()
        # Клик по селекту
        await unisat_page.locator('//*[@id="rc-tabs-2-panel-single"]/div/div').click()
        # Клик по опции
        await unisat_page.locator('//html/body/div[2]/div/div/div[2]/div/div/div/div/div/div/span[1]').click()
        # Клик по кнопке далее
        await unisat_page.locator('//*[@id="__next"]/div[3]/div[2]/div/div[4]/div/div').click()
        await unisat_page.wait_for_load_state('domcontentloaded')
        # Клик на оплату
        await unisat_page.locator('//*[@id="__next"]/div[3]/div[2]/div/div[9]/div[2]/div[2]/div/div/div[1]').click()
        # Снова получаем страницу кошелька
        unisat_wallet_page = context.pages[-1]
        if (not TEST_RUN):
            # Кнопка подписать и оплатить в кошельке
            await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[2]').click()
    except Exception as e:
        raise e
    finally:
        await asyncio.sleep(1)
        if ('unisat_page' in locals()):
            await unisat_page.close()
        requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
        await asyncio.sleep(1)

async def wallet_login(unisat_page: Page, seed_phrase: List[str], password: str):
    await unisat_page.bring_to_front()
    await unisat_page.wait_for_load_state()
    await unisat_page.get_by_text("I already have a wallet", exact=True).click()
    await unisat_page.wait_for_load_state()

    await unisat_page.locator(selector='input').first.fill(password)
    await unisat_page.get_by_placeholder("Confirm Password", exact=True).fill(password)
    await unisat_page.get_by_text('Continue', exact=True).click()
    await unisat_page.wait_for_load_state()

    await unisat_page.get_by_text('UniSat Wallet', exact=True).click()
    await unisat_page.wait_for_load_state()
    
    inputs = await unisat_page.locator('input[type="password"]').all()
    for i in range(0, len(inputs)):
        await inputs[i].fill(seed_phrase[i])
    
    await unisat_page.get_by_text('Continue', exact=True).first.click()
    await unisat_page.wait_for_load_state()

    await unisat_page.get_by_text('Continue', exact=True).first.click()
    await unisat_page.wait_for_load_state()

    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[2]/div[2]/div/div/div[3]/div[2]/label/span[1]/input').first.check()
    await unisat_page.wait_for_load_state()
    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[2]/div[2]/div/div/div[3]/div[4]/label/span[1]/input').first.check()
    await unisat_page.wait_for_load_state()
    await asyncio.sleep(3.2)
    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[2]/div[2]/div/div/div[4]/div').first.click()
    await unisat_page.wait_for_load_state()
    # Клик на настройки
    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[4]').first.click()
    # Клик на тип адреса
    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[2]/div/div[1]/div[1]').first.click()
    # Выбор Taproot
    await unisat_page.locator('//*[@id="root"]/div[1]/div/div[2]/div/div[3]/div').first.click()

async def unlock_wallet(unisat_wallet_page: Page, password: str):
    await unisat_wallet_page.get_by_placeholder('Password').first.fill(password)
    await unisat_wallet_page.get_by_text('Unlock').first.click()
    await unisat_wallet_page.wait_for_load_state()

def load_accounts() -> List[AccountDTO]:
    accounts = []
    with open('import.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None)
        for row in reader:
            if (int(row[5]) == 1):
                accounts.append(
                    AccountDTO(**{
                        'number': row[0],
                        'profile_id': row[1], 
                        'password': row[2], 
                        'tx_count': random.randint(int(TX_COUNT_MIN), int(TX_COUNT_MAX)),
                        'public_address': row[3],
                        'proxy': row[4]
                    })
                )
    return accounts

async def run(script, account: AccountDTO):
    async with async_playwright() as playwright:
        await script(playwright, account)

def run_check(address: str, proxy: str, number):
    url = 'https://mempool.space/api/address/'
    headers = {}
    headers = {"proxy": f"http://{proxy}"}
    r = requests.get(url=url + address + '/txs', headers=headers)
    if r.status_code == 200:
        body = r.json()
        return [number, address ,address, str(len(body)), datetime.datetime.fromtimestamp(body[0]['status']['block_time']).strftime("%d.%m.%Y")]

def run_check_wrapper(account: AccountDTO):
    return run_check(account.get('public_address'), account.get('proxy'), account.get('number'))

def main():
    logger.info(f"Старт")
    if (not TEST_RUN):
        if input('Внимание, это не тестовый запуск, продолжить? (y=Да, n=Нет) ') != 'y':
            sys.exit()
    accounts = load_accounts()
    for i in range(int(TX_COUNT_MAX)):
        for account in accounts:
            if (account['tx_count'] > 0):
                logger.info(f"[{account['public_address']}] Запуск минта")
                asyncio.run(run(unisat_script, account))
                account['tx_count'] -= 1
                logger.info(f"[{account['public_address']}] Осталось транзакций - " + str(account['tx_count']))
                pause_time = random.randint(int(ACCOUNT_LATENCY_MIN), int(ACCOUNT_LATENCY_MAX))
                logger.info(f"Пауза " + str(pause_time) + " сек")
                time.sleep(pause_time)
        time.sleep(ROUND_LATENCY)

    # logger.info(f"Запуск чекера")

    # with ProcessPoolExecutor(max_workers=QUANTITY_THREADS) as executor:
    #     res = list(executor.map(run_check_wrapper, accounts))

    # with open(datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.log.csv', 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    #     writer.writerow(["Public address", "Total txs"])
    #     writer.writerows(row for row in res)

    logger.info(f"Конец выполнения")

if (__name__ == '__main__'):
    dirname = os.path.dirname(__file__)
    dirname = os.path.join(dirname, 'logs')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.logging.log')
    logger.add(filepath)
    main()