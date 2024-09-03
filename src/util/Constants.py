import json

credentials = json.load(open('credentials.json'))

OANDA_DEMO_API_KEY = credentials['OANDA_DEMO_API_KEY']
OANDA_DEMO_ACCOUNT_ID = credentials['OANDA_DEMO_ACCOUNT_ID']
OANDA_DEMO_HOSTNAME = "api-fxpractice.oanda.com"

OANDA_LIVE_API_KEY = credentials['OANDA_LIVE_API_KEY']
OANDA_LIVE_ACCOUNT_ID = credentials['OANDA_LIVE_ACCOUNT_ID']
OANDA_LIVE_HOSTNAME = "api-fxtrade.oanda.com"

DATA_FOLDER = 'data'
INSTRUMENTS_FILENAME = '{}/instruments.pkl'.format(DATA_FOLDER)
CANDLE_FOLDER = '{}/historical_data'.format(DATA_FOLDER)
