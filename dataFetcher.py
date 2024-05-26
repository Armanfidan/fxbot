from http.client import HTTPException
from typing import Dict, List

import v20
import pandas as pd

import constants
from utilities import flatten_candle, save_candles_to_file, save_instruments_to_file


class DataFetcher:
    def __init__(self):
        self.api = v20.Context(
            hostname=constants.OANDA_HOSTNAME,
            token=constants.OANDA_API_KEY
        )

    def get_candles_for_pair(self, pair: str, count: int, granularity: str) -> pd.DataFrame:
        response: v20.response = self.api.instrument.candles(instrument=pair, count=count, granularity=granularity, price='MBA')
        if response.status != 200:
            raise HTTPException("Cannot get candlesticks for currency pair {}, status code: {}".format(pair, response.status))
        candles: List[Dict] = [flatten_candle(vars(candle)) for candle in response.body['candles'] if candle.complete]
        return pd.DataFrame(candles)

    def get_instruments_and_save_to_file(self) -> pd.DataFrame:
        response: v20.response = self.api.account.instruments(constants.OANDA_ACCOUNT_ID)
        instruments = pd.DataFrame([vars(instrument) for instrument in response.body['instruments']])
        save_instruments_to_file(instruments)
        return instruments

    def create_data_for_pair(self, pair: str, granularity: str, count=4000):
        candles: pd.DataFrame = self.get_candles_for_pair(pair, count, granularity)
        print("Loaded {} candles for pair {}, from {} to {}".format(candles.shape[0], pair, candles['time'].min(), candles['time'].max()))
        save_candles_to_file(candles, pair, granularity)
