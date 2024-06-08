from datetime import datetime, timedelta
import time
from http.client import HTTPException
from typing import Dict, Tuple, List

import v20
import pandas as pd

import constants
from utilities import flatten_candle, save_candles_to_file, save_instruments_to_file


MAX_CANDLESTICKS: int = 5000

GRANULARITY_TO_TIMEDELTA: Dict[str, timedelta] = {
    'S5': timedelta(seconds=5),
    'S10': timedelta(seconds=10),
    'S15': timedelta(seconds=15),
    'S30': timedelta(seconds=30),
    'M1': timedelta(minutes=1),
    'M2': timedelta(minutes=2),
    'M3': timedelta(minutes=3),
    'M4': timedelta(minutes=4),
    'M5': timedelta(minutes=5),
    'M10': timedelta(minutes=10),
    'M15': timedelta(minutes=15),
    'M30': timedelta(minutes=30),
    'H1': timedelta(hours=1),
    'H2': timedelta(hours=2),
    'H3': timedelta(hours=3),
    'H4': timedelta(hours=4),
    'H6': timedelta(hours=6),
    'H8': timedelta(hours=8),
    'H12': timedelta(hours=12),
    'D': timedelta(days=1),
    'W': timedelta(weeks=1),
    'M': timedelta(days=30),
}


class DataFetcher:
    def __init__(self):
        self.api = v20.Context(
            hostname=constants.OANDA_HOSTNAME,
            token=constants.OANDA_API_KEY,
            datetime_format='UNIX'
        )

    def get_max_candles_possible(self, pair: str, granularity: str, from_time: datetime, to_time: datetime) -> Tuple[pd.DataFrame, datetime]:

        number_of_candlesticks_from_start_to_now = (to_time - from_time) / GRANULARITY_TO_TIMEDELTA[granularity]
        number_of_candlesticks_to_fetch = min(MAX_CANDLESTICKS, int(number_of_candlesticks_from_start_to_now))
        response: v20.response = self.api.instrument.candles(instrument=pair, fromTime=time.mktime(from_time.timetuple()), granularity=granularity, price='MBA',
                                                             count=number_of_candlesticks_to_fetch)
        if response.status != 200:
            raise HTTPException(
                "Cannot get candlesticks for currency pair {}, status code: {}, error message: {}".format(pair, response.status, response.body.errorMessage))
        candles: pd.DataFrame = pd.DataFrame([flatten_candle(vars(candle)) for candle in response.body['candles'] if candle.complete])
        columns = [col for col in candles.columns if col not in ['time', 'volume']]
        candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
        candles['time'] = pd.to_datetime(pd.to_numeric(candles['time']), unit='s')
        return candles, candles.iloc[-1]['time']

    def get_candles_for_pair(self, pair: str, granularity: str, from_time: datetime, to_time: datetime) -> pd.DataFrame:
        start_time: datetime = from_time
        prev_start_time: datetime = start_time - timedelta(seconds=1)
        candles: List[pd.DataFrame] = []
        while to_time > start_time != prev_start_time:
            prev_start_time = start_time
            start_time += timedelta(seconds=1)
            curr_candles, start_time = self.get_max_candles_possible(pair, granularity, start_time, to_time)
            candles.append(curr_candles)
        return pd.concat(candles).drop_duplicates()

    def get_instruments_and_save_to_file(self) -> pd.DataFrame:
        response: v20.response = self.api.account.instruments(constants.OANDA_ACCOUNT_ID)
        instruments = pd.DataFrame([vars(instrument) for instrument in response.body['instruments']])
        save_instruments_to_file(instruments)
        return instruments

    def create_data_for_pair(self, pair: str, granularity: str, from_time: datetime, to_time: datetime = datetime.now()) -> pd.DataFrame:
        candles: pd.DataFrame = self.get_candles_for_pair(pair=pair, granularity=granularity, from_time=from_time, to_time=to_time)
        print("Loaded {} candles for pair {}, from {} to {}".format(candles.shape[0], pair, candles['time'].min(), candles['time'].max()))
        save_candles_to_file(candles, pair, granularity, from_time, to_time)
        return candles
