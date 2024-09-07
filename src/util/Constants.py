import json
import os

PROJECT_ROOT_FOLDER_NAME = 'fxbot'

CURRENT_PROJECT_ROOT: str = os.path.dirname(os.getcwd())
if not CURRENT_PROJECT_ROOT.endswith(PROJECT_ROOT_FOLDER_NAME):
    raise RuntimeError("Please run this project from the project root. Current directory: {}".format(CURRENT_PROJECT_ROOT))

credentials = json.load(open(os.path.join(CURRENT_PROJECT_ROOT, 'configuration/credentials.json')))

OANDA_DEMO_API_KEY = credentials['OANDA_DEMO_API_KEY']
OANDA_DEMO_ACCOUNT_ID = credentials['OANDA_DEMO_ACCOUNT_ID']
OANDA_DEMO_HOSTNAME = "api-fxpractice.oanda.com"

OANDA_LIVE_API_KEY = credentials['OANDA_LIVE_API_KEY']
OANDA_LIVE_ACCOUNT_ID = credentials['OANDA_LIVE_ACCOUNT_ID']
OANDA_LIVE_HOSTNAME = "api-fxtrade.oanda.com"

DATA_FOLDER = 'data'
INSTRUMENTS_FILENAME = '{}/{}/instruments.pkl'.format(CURRENT_PROJECT_ROOT, DATA_FOLDER)
CANDLE_FOLDER = '{}/{}/historical_data'.format(CURRENT_PROJECT_ROOT, DATA_FOLDER)
