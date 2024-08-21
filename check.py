import csv
import random
import requests
import datetime
import os
import time
import asyncio
from loguru import logger
from concurrent.futures import ProcessPoolExecutor
from src.account_dto import AccountDTO
from typing import List
from settings import TX_COUNT_MIN, TX_COUNT_MAX, QUANTITY_THREADS
from src.retry import retry
from typing import Union

def load_accounts(current_usd_price: Union[int, None]) -> List[AccountDTO]:
    accounts = []
    with open('import.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None)
        for row in reader:
            accounts.append(
                AccountDTO(**{
                    'number': row[0],
                    'profile_id': row[1], 
                    'password': row[2], 
                    'tx_count': random.randint(int(TX_COUNT_MIN), int(TX_COUNT_MAX)),
                    'public_address': row[3],
                    'proxy': row[4],
                    'usd_price': current_usd_price
                })
            )
    return accounts

@retry
async def run_check(address: str, proxy: str, usd_price: int, number):
    logger.info("Start address: " + address)
    url = 'https://mempool.space/api/address/'
    headers = {"proxy": f"http://{proxy}"}
    r_tx = requests.get(url=url + address + '/txs', headers=headers)
    time.sleep(2)
    r_data = requests.get(url=url + address, headers=headers)
    if (r_tx.status_code == 200) & (r_data.status_code == 200):
        body = r_tx.json()
        body_data = r_data.json()
        last_date = 'No data'
        if (body):
            for tx in body:
                if ('status' in tx) and ('block_time' in tx['status']):
                    last_date = datetime.datetime.fromtimestamp(tx['status']['block_time']).strftime("%d.%m.%Y")
                    break

        btc_balance = (int(body_data['chain_stats']['funded_txo_sum']) - int(body_data['chain_stats']['spent_txo_sum'])) / 100000000
        usd_balance = round(btc_balance * usd_price, 2)
        return [
            number, 
            address, 
            body_data['chain_stats']['spent_txo_count'], 
            btc_balance,
            usd_balance,
            last_date
        ]
    else:
        raise RuntimeError

def run_check_wrapper(account: AccountDTO):
    return asyncio.run(run_check(account.get('public_address'), account.get('proxy'), account.get('usd_price'), account.get('number')))

def main():
    url_price = 'https://mempool.space/api/v1/prices'
    r_price = requests.get(url=url_price)
    if r_price.status_code != 200:
        raise RuntimeError
    body_price = r_price.json()
    usd_price = body_price['USD']
    accounts = load_accounts(usd_price)

    with ProcessPoolExecutor(max_workers=QUANTITY_THREADS) as executor:
        res = list(executor.map(run_check_wrapper, accounts))

    dirname = os.path.dirname(__file__)
    dirname = os.path.join(dirname, 'logs')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.log.csv')

    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Number", "Public address", "Confirmed txo", "BTC balance", "USD balance", "Last tx date"])
        writer.writerows(row for row in res)


if (__name__ == '__main__'):
    main()