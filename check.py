import csv
import random
import requests
import datetime
import os
import time
from concurrent.futures import ProcessPoolExecutor
from src.account_dto import AccountDTO
from typing import List
from settings import TX_COUNT_MIN, TX_COUNT_MAX, QUANTITY_THREADS

def load_accounts() -> List[AccountDTO]:
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
                    'proxy': row[4]
                })
            )
    return accounts

def run_check(address: str, proxy: str, number):
    url = 'https://mempool.space/api/address/'
    url_price = 'https://mempool.space/api/v1/prices'
    headers = {}
    headers = {"proxy": f"http://{proxy}"}
    r_tx = requests.get(url=url + address + '/txs', headers=headers)
    r_data = requests.get(url=url + address, headers=headers)
    r_price = requests.get(url=url_price, headers=headers)
    if (r_tx.status_code == 200) & (r_data.status_code == 200) & (r_price.status_code == 200):
        body = r_tx.json()
        body_data = r_data.json()
        body_price = r_price.json()
        last_date = 'No data'
        if (bool(body)):
            for tx in enumerate(body, start=0):
                if ('status' in tx):
                    last_date = datetime.datetime.fromtimestamp(tx['status']['block_time']).strftime("%d.%m.%Y")
                    break

        btc_balance = (int(body_data['chain_stats']['funded_txo_sum']) - int(body_data['chain_stats']['spent_txo_sum'])) / 100000000
        usd_balance = round(btc_balance * body_price['USD'], 2)
        return [
            number, 
            address, 
            str(len(body)), 
            btc_balance,
            usd_balance,
            last_date
        ]

def run_check_wrapper(account: AccountDTO):
    return run_check(account.get('public_address'), account.get('proxy'), account.get('number'))

def main():
    accounts = load_accounts()

    with ProcessPoolExecutor(max_workers=QUANTITY_THREADS) as executor:
        res = list(executor.map(run_check_wrapper, accounts))

    dirname = os.path.dirname(__file__)
    dirname = os.path.join(dirname, 'logs')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.log.csv')

    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Number", "Public address", "Total txs", "BTC balance", "USD balance", "Last tx date"])
        writer.writerows(row for row in res)


if (__name__ == '__main__'):
    main()