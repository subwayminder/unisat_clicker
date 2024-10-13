import asyncio
import sys
import random
import time
import datetime
import sys
import os
import questionary
from questionary import Separator, Choice
from src.account import AccountDTO, load_accounts
from settings import TX_COUNT_MAX, ACCOUNT_LATENCY_MIN, ACCOUNT_LATENCY_MAX, TEST_RUN, ROUND_LATENCY
from src.playwright import unisat_script, ordinals_names, ordinals_bytes
from loguru import logger
from src.functions import withdraw

async def run(script, account: AccountDTO):
    await script(account)

def choose_script():
    result = questionary.select(
        "Choose option:",
        choices=[
            Separator('Utils:'),
            Separator(''),
            Choice("Coinex - FB withdraw", withdraw),
            Separator(''),
            Separator('Scripts:'),
            Separator(''),
            Choice("Mint Runes", unisat_script),
            Choice("Ordinals - Names", ordinals_names),
            Choice("Ordinals - Bytes Deploy", ordinals_bytes),
            Separator(''),
            Choice("Exit", 'exit'),
        ],
        qmark="⚙️ ",
        pointer="✅ "
    ).ask()
    if result == "exit":
        print("Bye")
        sys.exit()
    return result

def main():
    logger.info(f"Start")
    if (not TEST_RUN):
        if input('Attention, this is not a test run, continue? (y=Yes, n=No) ') != 'y':
            sys.exit()
    accounts = load_accounts()
    script = choose_script()
    iterations = int(TX_COUNT_MAX)
    

    for _ in range(iterations):
        random.shuffle(accounts)
        for account in accounts:
            if (account['tx_count'] > 0):
                logger.info(f"[{account['public_address']}] Запуск минта")
                account['tx_count'] = 0 if script == withdraw else account['tx_count']
                asyncio.run(script(account))
                logger.info(f"[{account['public_address']}] Осталось транзакций - " + str(account['tx_count']))
                pause_time = random.randint(int(ACCOUNT_LATENCY_MIN), int(ACCOUNT_LATENCY_MAX))
                time.sleep(pause_time)
                logger.info(f"Пауза " + str(pause_time) + " сек")
                    
        time.sleep(ROUND_LATENCY)

    logger.info(f"Конец выполнения")

if (__name__ == '__main__'):
    dirname = os.path.dirname(__file__)
    dirname = os.path.join(dirname, 'logs')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, datetime.datetime.now().strftime("%d.%m.%Y_%H-%M-%S%z") + '.logging.log')
    logger.add(filepath)
    main()