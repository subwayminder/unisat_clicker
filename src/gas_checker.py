import asyncio
import time
import random
import requests
from settings import MAX_GWEI
from loguru import logger


async def get_gas():
    try:
        response = requests.get('https://mempool.space/api/v1/fees/recommended').json()
        fee = response['hourFee']
        return fee
    except Exception as error:
        logger.error(error)


async def wait_gas():
    logger.info("Get GWEI")
    while True:
        gas = await get_gas()

        if gas > MAX_GWEI:
            pause_time = random.randint(60, 90)
            logger.info(f'Комиссия выше указанной: {gas} > {MAX_GWEI}, пауза {pause_time} сек')
            await asyncio.sleep(pause_time)
        else:
            logger.success(f"Комиссия в норме: {gas} < {MAX_GWEI}")
            break


def check_gas(func):
    async def _wrapper(*args, **kwargs):
        await wait_gas()
        return await func(*args, **kwargs)

    return _wrapper
