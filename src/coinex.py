import hashlib
import json
import time
import aiohttp
import requests
import asyncio
import hmac
import ccxt.async_support as ccxt
from src.account import AccountDTO

class CoinExResponse:
    def __init__(self, success, message, result):
        self.success = success
        self.message = message
        self.result = result

    def __str__(self):
        d = {
            'success': self.success,\
            'message': self.message,\
            'result': self.result
        }
        return str(json.dumps(d, indent = 4))

class CoinEx:
    endpoint = 'https://api.coinex.com/v2/'

    def __init__(self, account: AccountDTO, AccessID=None, Secret=None):
        self.AccessID = AccessID
        self.Secret = Secret
        self.account: AccountDTO = account
        self.exchange = ccxt.coinex({
            'apiKey': AccessID,
            'secret': Secret,
        })

    async def authenticatedRequest(self, method, path, json={}):
        if self.AccessID is None or self.Secret is None:
            raise ValueError('APIKey and Secret must be supplied to use this methods')
        timestamp = str(int(time.time() * 1000))
        json['access_id'] = self.AccessID
        json['tonce'] = timestamp
        url = CoinEx._expandPathToUrl(path=path)
        query_str = '&'.join(f'{key}={value}' for key, value in sorted(json.items()))
        prepared_str = method + url
        print(prepared_str)
        signature = hmac.new(
            self.Secret.encode('utf-8'), 
            str(method + path + query_str), 
            digestmod=hashlib.sha256
        ).hexdigest()
        headers = {
            'X-COINEX-KEY': self.AccessID,
            'X-COINEX-SIGN': signature,
            'X-COINEX-TIMESTAMP': timestamp
        }

        rjson = await self.make_request(method='GET', url=url, headers=headers, json=json)
        return CoinExResponse(rjson['code'], rjson['message'], rjson['data'])
    
    async def submitWithdraw(self):
        params = {
            "ccy": "FB",
            "chain": "FB",
            "to_address": self.account.get('public_address'),
            "amount": self.account.get('withdraw_amount')
        }
        return await self.exchange.withdraw(
            'FB', 
            self.account.get('withdraw_amount'), 
            self.account.get('public_address'), 
            params=params
        )