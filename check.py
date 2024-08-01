import csv
import random
import requests
import datetime
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
            if (int(row[4]) == 1):
                accounts.append(
                    AccountDTO(**{
                        'profile_id': row[0], 
                        'password': row[1], 
                        'tx_count': random.randint(int(TX_COUNT_MIN), int(TX_COUNT_MAX)),
                        'public_address': row[2],
                        'proxy': row[3]
                    })
                )
    return accounts

def run_check(address: str, proxy: str):
    url = 'https://mempool.space/api/address/'
    headers = {}
    headers = {"proxy": f"http://{proxy}"}
    r = requests.get(url=url + address + '/txs', headers=headers)
    if r.status_code == 200:
        body = r.json()
        return [address, str(len(body))]

def run_check_wrapper(account: AccountDTO):
    return run_check(account.get('public_address'), account.get('proxy'))

def main():
    accounts = load_accounts()

    with ProcessPoolExecutor(max_workers=QUANTITY_THREADS) as executor:
        res = list(executor.map(run_check_wrapper, accounts))

    with open(datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.log.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Public address", "Total txs"])
        writer.writerows(row for row in res)


if (__name__ == '__main__'):
    main()