import json

credentials = json.load(open('credentials.json'))

OANDA_DEMO_API_KEY = credentials['OANDA_DEMO_API_KEY']
OANDA_DEMO_ACCOUNT_ID = credentials['OANDA_DEMO_ACCOUNT_ID']
OANDA_DEMO_HOSTNAME = "api-fxpractice.oanda.com"

OANDA_LIVE_API_KEY = credentials['OANDA_LIVE_API_KEY']
OANDA_LIVE_ACCOUNT_ID = credentials['OANDA_LIVE_ACCOUNT_ID']
OANDA_LIVE_HOSTNAME = "api-fxtrade.oanda.com"

INSTRUMENTS_FILENAME = 'data/instruments.pkl'
CANDLE_FOLDER = 'data/historical_data'
