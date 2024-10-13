from src.coinex import CoinEx
from src.gas_checker import check_fractal_gas
from src.retry import retry
from src.account import AccountDTO
from settings import COINEX_ACCESS_ID, COINEX_SECRET
from loguru import logger
import ccxt.async_support as ccxt


@check_fractal_gas
@retry
async def withdraw(account: AccountDTO):
    logger.info(f"[{account.get('public_address')}] Начинаем вывод {account.get('withdraw_amount')} FB")

    try:
        coinex = CoinEx(account, COINEX_ACCESS_ID, COINEX_SECRET)

        response = await coinex.submitWithdraw()
        resp_info = response['info']

        explorer = resp_info['explorer_address_url']
        amount = resp_info['amount']
        fees = resp_info['fee_amount']
        actual_amount = resp_info['actual_amount']
        logger.info(f"[{account.get('public_address')}] | Withdraw {actual_amount} FB ({amount} (cost) - {fees} (fees)) to {account.get('public_address')} | {explorer}")
    except ccxt.ExchangeError as e:
        raise e
    except Exception as e:
        raise e
    finally:
        if coinex:
            await coinex.exchange.close()