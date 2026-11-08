"""Paths are independent of cwd; offline imports never read credentials."""
import json
from pathlib import Path

CURRENT_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
PROJECT_ROOT_FOLDER_NAME = 'fxbot'
OANDA_DEMO_HOSTNAME = 'api-fxpractice.oanda.com'
OANDA_LIVE_HOSTNAME = 'api-fxtrade.oanda.com'
DATA_FOLDER = str(Path(CURRENT_PROJECT_ROOT) / 'data')
INSTRUMENTS_FILENAME = str(Path(DATA_FOLDER) / 'instruments.pkl')
CANDLE_FOLDER = str(Path(DATA_FOLDER) / 'historical_data')


def get_oanda_credentials(live):
    path = Path(CURRENT_PROJECT_ROOT) / 'configuration' / 'credentials.json'
    if not path.exists():
        raise FileNotFoundError('OANDA access requires configuration/credentials.json; offline backtests do not')
    credentials = json.loads(path.read_text())
    environment = 'LIVE' if live else 'DEMO'
    return credentials[f'OANDA_{environment}_API_KEY'], credentials[f'OANDA_{environment}_ACCOUNT_ID']
