import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SLOW_MODE_VALUE = os.environ.get("SLOW_MODE_VALUE")
ADS_API_URL = os.environ.get("ADS_API_URL")
TX_COUNT_MIN = os.environ.get("TX_COUNT_MIN")
TX_COUNT_MAX = os.environ.get("TX_COUNT_MAX")
ACCOUNT_LATENCY_MIN = int(os.environ.get("ACCOUNT_LATENCY_MIN"))
ACCOUNT_LATENCY_MAX = int(os.environ.get("ACCOUNT_LATENCY_MAX"))
ROUND_LATENCY = int(os.environ.get("ROUND_LATENCY"))
QUANTITY_THREADS = int(os.environ.get("QUANTITY_THREADS"))
RETRY_COUNT = int(os.environ.get("RETRY_COUNT"))
MAX_GWEI = float(os.environ.get("MAX_GWEI"))
TEST_RUN = str.lower(os.environ.get("TEST_RUN")) == 'true'
RETRY_TIMEOUT_MIN = int(os.environ.get("RETRY_TIMEOUT_MIN"))
RETRY_TIMEOUT_MAX = int(os.environ.get("RETRY_TIMEOUT_MAX"))
DOMAIN_LENGHT_FROM = int(os.environ.get("DOMAIN_LENGHT_FROM"))
DOMAIN_LENGHT_TO = int(os.environ.get("DOMAIN_LENGHT_TO"))