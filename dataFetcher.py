from datetime import datetime, timedelta
import time
from http.client import HTTPException
from typing import Tuple, List

import v20
import pandas as pd
from pandas import DataFrame

import constants
from utilities import flatten_candle, save_candles_to_file, save_instruments_to_file, Granularity

MAX_CANDLESTICKS: int = 5000


class DataFetcher:
    def __init__(self):
        self.api = v20.Context(
            hostname=constants.OANDA_HOSTNAME,
            token=constants.OANDA_API_KEY,
            datetime_format='UNIX'
        )

    def get_max_candles_possible(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> Tuple[pd.DataFrame, datetime]:

        number_of_candlesticks_from_start_to_now = (to_time - from_time) / Granularity.value
        number_of_candlesticks_to_fetch = min(MAX_CANDLESTICKS, int(number_of_candlesticks_from_start_to_now))
        response: v20.response = self.api.instrument.candles(instrument=pair, fromTime=time.mktime(from_time.timetuple()), granularity=granularity.name, price='MBA',
                                                             count=number_of_candlesticks_to_fetch)
        if response.status != 200:
            raise HTTPException(
                "Cannot get candlesticks for currency pair {}, status code: {}, error message: {}".format(pair, response.status, response.body.errorMessage))
        candles: DataFrame = pd.DataFrame([flatten_candle(vars(candle)) for candle in response.body['candles'] if candle.complete])
        columns: List = list(set(candles.columns) - {'time', 'volume'})
        candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
        candles.rename(columns={col: col.replace('.', '_') for col in columns}, inplace=True)
        candles['time'] = pd.to_datetime(pd.to_numeric(candles['time']), unit='s')
        return candles, candles.iloc[-1]['time']

    def get_candles_for_pair(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> DataFrame:
        """
        For a given pair, retrieves the candles from the start time to the end time.
        :param pair: Currency pair name.
        :param granularity: Candlestick granularity.
        :param from_time:
        :param to_time:
        :return:
        """
        start_time: datetime = from_time
        prev_start_time: datetime = start_time - timedelta(seconds=1)
        candles: List[pd.DataFrame] = []
        while to_time > start_time != prev_start_time:
            prev_start_time = start_time
            start_time += timedelta(seconds=1)
            curr_candles, start_time = self.get_max_candles_possible(pair, granularity, start_time, to_time)
            candles.append(curr_candles)
        return pd.concat(candles).drop_duplicates()

    def get_instruments_and_save_to_file(self) -> DataFrame:
        """
        Retrieves the instruments from the OANDA API and saves them to a file.
        :return: The instruments DataFrame.
        """
        response: v20.response = self.api.account.instruments(constants.OANDA_ACCOUNT_ID)
        instruments = pd.DataFrame([vars(instrument) for instrument in response.body['instruments']])
        save_instruments_to_file(instruments)
        return instruments

    def create_data_for_pair(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime = datetime.now()) -> DataFrame:
        candles: DataFrame = self.get_candles_for_pair(pair=pair, granularity=granularity, from_time=from_time, to_time=to_time)
        print("Loaded {} candles for pair {}, from {} to {}".format(candles.shape[0], pair, candles['time'].min(), candles['time'].max()))
        save_candles_to_file(candles, pair, granularity, from_time, to_time)
        return candles
