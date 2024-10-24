import requests
import random
import asyncio
import string
from typing import List
from src.gas_checker import check_gas, check_fractal_gas
from src.retry import retry
from settings import ADS_API_URL, ADS_API_PORT, SLOW_MODE_VALUE, DOMAIN_LENGHT_FROM, DOMAIN_LENGHT_TO, TEST_RUN
from playwright.async_api import async_playwright, Playwright, Page, BrowserContext
from src.account import AccountDTO

async def open_profile(ap: Playwright, account: AccountDTO) -> BrowserContext:
    ads_api_response = requests.get(f"http://{ADS_API_URL}:{ADS_API_PORT}" + '/api/v1/browser/start?user_id=' + account.get('profile_id')).json()
    browser = await ap.chromium.connect_over_cdp(
        str(ads_api_response['data']['ws']['puppeteer'])
            .replace(f"127.0.0.1:{ADS_API_PORT}", f"{ADS_API_URL}:{ADS_API_PORT}"), 
        slow_mo=int(SLOW_MODE_VALUE),
    )
    context = browser.contexts[0]
    return context

@check_gas
@retry
async def unisat_script(account: AccountDTO):
    async with async_playwright() as ap:
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
            await sign_with_wallet(context=context, unisat_page=unisat_page, account=account)

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
            await unisat_page.wait_for_load_state()
            await asyncio.sleep(2)

            # Клик на оплату
            await unisat_page.locator('//*[@id="__next"]/div[3]/div[2]/div/div[9]/div[2]/div[2]/div/div/div[1]').click()

            # Снова получаем страницу кошелька
            unisat_wallet_page = context.pages[-1]
            if (not TEST_RUN):
                await sign_tx(unisat_wallet_page)
        except Exception as e:
            raise e
        finally:
            await asyncio.sleep(1)
            if ('unisat_page' in locals()):
                await unisat_page.close()
            requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
            account['tx_count'] -= 1
            await asyncio.sleep(1)

def generate_string(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

@check_gas
async def sign_tx(unisat_wallet_page: Page):
    # Кнопка подписать и оплатить в кошельке
    await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[2]').click()

@check_fractal_gas
async def sign_fractal_tx(unisat_wallet_page: Page):
    # Кнопка подписать и оплатить в кошельке
    await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[2]').click()

@check_gas
@retry
async def ordinals_names(account: AccountDTO):
    async with async_playwright() as ap:
        try:
            ordinals_names_url = 'https://unisat.io/inscribe'
            context = await open_profile(ap, account)

            # Переход на страницу с ординалами
            unisat_page = await context.new_page()
            await unisat_page.bring_to_front()
            await unisat_page.goto(ordinals_names_url)

            # Логин через кошелек, клик sign
            await sign_with_wallet(context=context, unisat_page=unisat_page, account=account)

            # Выбираем имена на .unisat домене
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[3]/div[1]/div[2]/div').click()
            await unisat_page.locator('//html/body/div[2]/div/div[2]/div/div/div/div/div[2]').click()

            # Генерируем случайный домен
            name = generate_string(size=random.randint(int(DOMAIN_LENGHT_FROM), int(DOMAIN_LENGHT_TO)))

            # Вставляем его в текстовое поле, нажимаем далее
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div/textarea').fill(name)
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div/div[3]').click()
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div/div[5]/div[2]').click()

            # Выбираем эконом
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[5]/div[2]/div[1]').click()
            await unisat_page.wait_for_load_state()

            # Кликаем customize и откручиваем сатоши слайдер до минимума
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[6]/div[1]/div[1]/span[2]').first.click()
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[6]/div[2]/div[2]/div[2]/input').first.fill('330')

            # Клик по селекту
            await asyncio.sleep(2)
            await unisat_page.locator('//*[@id="rc-tabs-1-panel-single"]/div/div/span[1]').click()

            # Клик по опции
            await unisat_page.locator('//html/body/div[3]/div').click()
            await asyncio.sleep(1)

            # Нажимаем Submit & Pay
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[8]/div').click()
            await unisat_page.wait_for_load_state()
            await unisat_page.locator('//*[@id="__next"]/div[3]/div[2]/div/div[9]/div[2]/div[2]/div/div/div[1]').click()

            # Снова получаем страницу кошелька
            unisat_wallet_page = context.pages[-1]
            if (not TEST_RUN):
                # Кнопка подписать и оплатить в кошельке
                await sign_tx(unisat_wallet_page)

            if ('unisat_page' in locals()):
                await unisat_page.close()
            requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
            account['tx_count'] -= 1
            await asyncio.sleep(1)

        except Exception as e:
            raise e

        finally:
            await asyncio.sleep(1)
            if ('unisat_page' in locals()):
                await unisat_page.close()
            requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
            account['tx_count'] -= 1
            await asyncio.sleep(1)
    
@check_gas
@retry
async def ordinals_bytes(account: AccountDTO):
    async with async_playwright() as ap:
        try:
            ordinals_names_url = 'https://unisat.io/inscribe'
            context = await open_profile(ap, account)

            # Переход на страницу с ординалами
            unisat_page = await context.new_page()
            await unisat_page.bring_to_front()
            await unisat_page.goto(ordinals_names_url)
            # Логин через кошелек, клик sign
            await sign_with_wallet(context=context, unisat_page=unisat_page, account=account)

            # Выбираем деплой 5 байт
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[1]/div[1]/div[4]/div[2]/div[1]').click()

            # Заполняем инпут
            await unisat_page.locator('//html/body/div/div[3]/div/div[4]/div[3]/div[2]/div[1]/div[2]/input').fill(generate_string(5))

            # Клик next
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[3]/div').click()
            
            # Еще клик next
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div/div[4]/div[2]').click()

            # Скипаем алерт если он появился
            try:
                await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[2]/div/div[4]/label').click(timeout=1000)
                await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[2]/div/div[5]').click(timeout=1000)
            except:
                pass

            # Клик по селекту
            await unisat_page.locator('//*[@id="rc-tabs-1-panel-single"]/div/div/span[1]').click()

            # Клик по опции
            await unisat_page.locator('//html/body/div[2]/div/div/div[2]').click()

            # Выбираем эконом
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[5]/div[2]/div[1]').click()
            await unisat_page.wait_for_load_state()

            # Кликаем customize и откручиваем сатоши слайдер до минимума
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[6]/div[1]/div[1]/span[2]').first.click()
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[6]/div[2]/div[2]/div[2]/input').first.fill('330')

            # Клик на сабмит
            await unisat_page.locator('//*[@id="__next"]/div[3]/div/div[4]/div[3]/div[8]/div/span').click()
            await unisat_page.wait_for_load_state()

            # Клик на оплату
            await unisat_page.locator('//*[@id="__next"]/div[3]/div[2]/div/div[9]/div[2]/div[2]/div/div').click()

            # Снова получаем страницу кошелька
            unisat_wallet_page = get_wallet_page(context)
            if (not TEST_RUN):
                # Кнопка подписать и оплатить в кошельке
                await sign_tx(unisat_wallet_page)

        except Exception as e:
            raise e

        finally:
            await asyncio.sleep(1)
            if ('unisat_page' in locals()):
                await unisat_page.close()
            requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
            account['tx_count'] -= 1
            await asyncio.sleep(1)

@check_fractal_gas
@retry
async def fractal_mint(account: AccountDTO):
    async with async_playwright() as ap:
        try:
            context = await open_profile(ap, account)
            unisat_page = await context.new_page()
            await unisat_page.bring_to_front()
            await unisat_page.goto('https://fractal.unisat.io/explorer/brc20')
            await unisat_page.wait_for_load_state()

            # Переход на страницу случайной руны
            await unisat_page.locator('//*[@id="__next"]/div[2]/div/div/div/div/div[2]/div[2]/div/div/label[2]/div').first.click()
            await unisat_page.locator('//*[@id="__next"]/div[2]/div/div/div/div/div[3]/div/div/div[4]').first.click()
            await asyncio.sleep(5)
            mint_collection = await unisat_page.locator("span:has-text('Mint')").all()
            count = await unisat_page.locator("span:has-text('Mint')").count()
            index = random.randint(0, count - 1)
            await mint_collection[index].click()
            await unisat_page.wait_for_load_state()


            # await unisat_page.goto('https://fractal.unisat.io/inscribe?tick=' + random_rune['ticker'])

            # Логин через кошелек, клик sign
            await sign_with_wallet_fractal(context=context, unisat_page=unisat_page, account=account)

            # Ставим repeat 50
            repeat_rune_input = unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[2]/div[4]/div[2]/input').first
            await repeat_rune_input.fill('50')

            # Жмем далее
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[3]/div/div').first.click()
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div/div[4]/div[2]').first.click()

            # Скипаем алерт если он появился
            try:
                await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[2]/div/div[4]/label').click(timeout=1000)
                await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[2]/div/div[5]').click(timeout=1000)
            except:
                pass

            # Клик по селекту
            await unisat_page.locator('//*[@id="rc-tabs-1-panel-single"]/div/div/span[1]').first.click()

            # Клик по опции
            await unisat_page.locator('//html/body/div[2]/div').first.click()

            # Выбираем эконом
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[5]/div[2]/div[1]').first.click()
            await unisat_page.wait_for_load_state()

            # Подтверждаем минт
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/label').first.click()
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[2]/div[3]/div[3]/div[8]/div').first.click()

            # Скипаем еще один алерт если он есть
            try:
                await unisat_page.get_by_text('I have read and agreed to the risk warning').first.click(timeout=1000)
            except:
                pass

            # Клик на оплату
            await unisat_page.locator('//*[@id="__next"]/div[4]/div[3]/div/div[9]/div[2]/div[2]/div/div/div[1]').click()

            # Снова получаем страницу кошелька
            unisat_wallet_page = get_wallet_page(context)
            if (not TEST_RUN):
                # Кнопка подписать и оплатить в кошельке
                await sign_fractal_tx(unisat_wallet_page)

        except Exception as e:
            raise e

        finally:
            await asyncio.sleep(1)
            if ('unisat_page' in locals()):
                await unisat_page.close()
            requests.get(ADS_API_URL + '/api/v1/browser/stop?user_id=' + account.get('profile_id')).json()
            account['tx_count'] -= 1
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

async def sign_with_wallet(unisat_page: Page, context: BrowserContext, account: AccountDTO):
    # Логин через кошелек, клик sign
    await unisat_page.locator('//*[@id="__next"]/div[1]/div[2]/div[3]').click()
    await unisat_page.locator('//*[@id="__next"]/div[5]/div/div[3]/div[1]').click()
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]
    # Пробуем разблокировать кошелек, скип если уже разблокирован
    try:
        await unlock_wallet(unisat_wallet_page, account.get('password'))
    except:
        pass
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]

    # Переключаем сеть если нужно
    try:
        await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[2]').click(timeout=1500)
    except:
        pass
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]

    await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[2]/div/div[2]').click()

async def sign_with_wallet_fractal(unisat_page: Page, context: BrowserContext, account: AccountDTO):
    # Логин через кошелек, клик sign
    await unisat_page.locator('//*[@id="__next"]/div[1]/div[1]/div[3]/div').click()
    await unisat_page.locator('//*[@id="__next"]/div[6]/div/div[3]/div[1]').click()
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]
    # Пробуем разблокировать кошелек, скип если уже разблокирован
    try:
        await unlock_wallet(unisat_wallet_page, account.get('password'))
    except:
        pass
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]

    # Переключаем сеть если нужно
    try:
        await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[3]/div/div[2]').click(timeout=1500)
    except:
        pass
    await asyncio.sleep(5)
    unisat_wallet_page = context.pages[-1]

    await unisat_wallet_page.locator('//*[@id="root"]/div[1]/div/div[2]/div/div[2]').click()

async def unlock_wallet(unisat_wallet_page: Page, password: str):
    await unisat_wallet_page.get_by_placeholder('Password').first.fill(password, timeout=2000)
    await unisat_wallet_page.get_by_text('Unlock').first.click(timeout=2000)
    await unisat_wallet_page.wait_for_load_state()

def get_wallet_page(context: BrowserContext):
    unisat_wallet_page = None
    while unisat_wallet_page == None:
        unisat_wallet_page = context.pages[-1]
    return unisat_wallet_page
