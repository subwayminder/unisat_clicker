import asyncio
import time
import random
import requests
from settings import MAX_GWEI, MAX_FRACTAL_GAS
from loguru import logger
from src.retry import retry

@retry
async def get_gas(url: str):
    try:
        response = requests.get(url).json()
        fee = response['hourFee']
        return fee
    except Exception as error:
        logger.error(error)


async def wait_gas(url: str, max_gas):
    logger.info("Get GWEI")
    while True:
        gas = await get_gas(url)

        if gas > max_gas:
            pause_time = random.randint(60, 90)
            logger.info(f'Комиссия выше указанной: {gas} > {max_gas}, пауза {pause_time} сек')
            await asyncio.sleep(pause_time)
        else:
            logger.success(f"Комиссия в норме: {gas} < {max_gas}")
            break

def check_gas(func):
    async def _wrapper(*args, **kwargs):
        await wait_gas('https://mempool.space/api/v1/fees/recommended', MAX_GWEI)
        return await func(*args, **kwargs)

    return _wrapper

def check_fractal_gas(func):
    async def _wrapper(*args, **kwargs):
        await wait_gas('https://mempool.fractalbitcoin.io/api/fees/recommended', MAX_FRACTAL_GAS)
        return await func(*args, **kwargs)

    return _wrapper
