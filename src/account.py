import csv
import random
from src.gas_checker import check_gas
from src.retry import retry
from settings import TX_COUNT_MIN, TX_COUNT_MAX
from typing import Union, TypedDict, List

class AccountDTO(TypedDict):
   number: int
   profile_id: str
   password: str
   tx_count: int
   public_address: str
   proxy: str
   withdraw_amount: str
   usd_price: Union[int, None]

def load_accounts(include_inactive: bool = False, current_usd_price = 0):
   accounts = []
   with open('import.csv', newline='') as csvfile:
      reader = csv.reader(csvfile, delimiter=';')
      next(reader, None)
      for row in reader:
         if (int(row[7]) == 1 or include_inactive):
               accounts.append(
                  AccountDTO(**{
                     'number': row[0],
                     'profile_id': row[1], 
                     'password': row[2], 
                     'tx_count': random.randint(int(TX_COUNT_MIN), int(TX_COUNT_MAX)),
                     'public_address': row[3],
                     'proxy': row[4],
                     'withdraw_amount': round(random.uniform(float(row[5]), float(row[6])), 2),
                     'usd_price': current_usd_price
                  })
               )
   return accounts