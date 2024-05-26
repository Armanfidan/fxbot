import os
from http.client import HTTPException
from pathlib import Path
from typing import Dict, List, Any

import v20
import pandas as pd

import Constants

API = v20.Context(
    hostname=Constants.OANDA_HOSTNAME,
    token=Constants.OANDA_API_KEY
)


def candle_to_dict(candle: Dict[str, Any]):
    prices: List[str] = ['mid', 'bid', 'ask']
    candle_dict: Dict[str, str] = {}
    for price in prices:
        candle_dict.update({'{}.{}'.format(price, subprice): value for subprice, value in vars(candle[price]).items()})
    return {'time': candle['time'], 'volume': candle['volume']} | candle_dict


def get_candles_for_pair(pair: str, count: int, granularity: str) -> pd.DataFrame:
    response: v20.response = API.instrument.candles(instrument=pair, count=count, granularity=granularity, price='MBA')
    if response.status != 200:
        raise HTTPException("Cannot get candlesticks for currency pair {}, status code: {}".format(pair, response.status))
    candles: List[Dict] = [candle_to_dict(vars(candle)) for candle in response.body['candles'] if candle.complete]
    return pd.DataFrame(candles)


def get_instruments() -> pd.DataFrame:
    response: v20.response = API.account.instruments(Constants.OANDA_ACCOUNT_ID)
    return pd.DataFrame([vars(instrument) for instrument in response.body['instruments']])


def save_candles_to_file(candles: pd.DataFrame, pair: str, granularity: str):
    pickle_folder = 'historical_data'
    pickle_path = '%s/{}_{}.pkl' % pickle_folder
    try:
        Path(pickle_folder).mkdir(parents=True, exist_ok=True)
        candles.to_pickle(pickle_path.format(pair, granularity))
    except IOError as e:
        raise IOError("Could not save candles to file. Error: " + e.message)


def create_data_for_pair(pair: str, granularity: str, count=4000):
    candles: pd.DataFrame = get_candles_for_pair(pair, count, granularity)
    print("Loaded {} candles for pair {}, from {} to {}".format(candles.shape[0], pair, candles['time'].min(), candles['time'].max()))
    save_candles_to_file(candles, pair, granularity)
