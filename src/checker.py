import csv
import random
import requests
import datetime
import os
import time
import asyncio
import aiohttp
from loguru import logger
from concurrent.futures import ProcessPoolExecutor
from settings import QUANTITY_THREADS
from src.account import AccountDTO, load_accounts
from src.retry import retry
from typing import Union

class Checker:
    def __init__(self, account: AccountDTO) -> None:
        self.account = account
        pass

    async def get_address_info(self, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, proxy=f"http://{self.account.get('proxy')}") as resp:
                if (resp.status == 200):
                    return await resp.json()
                else:
                    raise RuntimeError(
                        f'[{self.account.get()}] [{self.account.get('public_address')}] - ' 
                        + url 
                        + ' returns with ' 
                        + resp.status
                    )

    @retry
    async def run_check(self):
        logger.info("Start address: " + self.account.get('public_address'))
        mempool_url = 'https://mempool.space/api/address/'
        body = await self.get_address_info(url=mempool_url  + self.account.get('public_address') + '/txs')
        body_data = await self.get_address_info(url=mempool_url + self.account.get('public_address'))
        fb_data = await self.get_address_info(url="https://explorer.unisat.io/fractal-mainnet/api/address/summary" 
                                              + f'?address={self.account.get('public_address')}')
        last_date = 'No data'
        if (body):
            for tx in body:
                if ('status' in tx) and ('block_time' in tx['status']):
                    last_date = datetime.datetime.fromtimestamp(tx['status']['block_time']).strftime("%d.%m.%Y")
                    break
        btc_balance = (int(body_data['chain_stats']['funded_txo_sum']) 
                       - int(body_data['chain_stats']['spent_txo_sum'])) / 100000000
        usd_balance = round(btc_balance * self.account.get('usd_price'), 2)
        return [
            self.account.get('number'), 
            self.account.get('public_address'), 
            body_data['chain_stats']['spent_txo_count'], 
            btc_balance,
            usd_balance,
            last_date,
            fb_data['data']['balance'] / 100000000,
            fb_data['data']['available'] / 100000000
        ]

    def run_check_wrapper(account: AccountDTO):
        checker = Checker(account=account)
        return asyncio.run(checker.run_check())
    
def start_checker():
    url_price = 'https://mempool.space/api/v1/prices'
    r_price = requests.get(url=url_price)
    if r_price.status_code != 200:
        raise RuntimeError
    body_price = r_price.json()
    usd_price = body_price['USD']
    accounts = load_accounts(usd_price)

    with ProcessPoolExecutor(max_workers=QUANTITY_THREADS) as executor:
        res = list(executor.map(Checker.run_check_wrapper, accounts))

    dirname = os.path.dirname(os.path.dirname(__file__))
    dirname = os.path.join(dirname, 'logs')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.log.csv')

    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "Number", 
            "Public address", 
            "Confirmed txo", 
            "BTC balance", 
            "USD balance", 
            "Last tx date", 
            "FB balance", 
            "FB available"
        ])
        writer.writerows(row for row in res)