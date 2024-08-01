from typing import TypedDict
from typing import Union

class AccountDTO(TypedDict):
   number: int
   profile_id: str
   password: str
   tx_count: int
   public_address: str
   proxy: str