from __future__ import annotations

from datetime import datetime, timedelta
import time
from http.client import HTTPException
from typing import Tuple, List, Dict

import v20
import pandas as pd
from pandas import DataFrame

from src.util.Constants import OANDA_DEMO_HOSTNAME, OANDA_LIVE_HOSTNAME, OANDA_DEMO_API_KEY, OANDA_LIVE_API_KEY, OANDA_DEMO_ACCOUNT_ID, OANDA_LIVE_ACCOUNT_ID, INSTRUMENTS_FILENAME
from src.util.Utilities import prepare_candle, save_candles_to_file, save_instruments_to_file, validate_candles_df
from src.model.Granularity import Granularity
from src.model.candle.Candle import Candle

from typing_extensions import deprecated

MAX_CANDLESTICKS: int = 5000


class DataClient:
    def __init__(self, live: bool):
        self.live: bool = live
        self.api = v20.Context(
            hostname=OANDA_LIVE_HOSTNAME if live else OANDA_DEMO_HOSTNAME,
            token=OANDA_LIVE_API_KEY if live else OANDA_DEMO_API_KEY,
            datetime_format='UNIX'
        )

    def get_max_candles_possible(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> Tuple[DataFrame, datetime]:

        number_of_candlesticks_from_start_to_now = (to_time - from_time) / granularity.value
        number_of_candlesticks_to_fetch = min(MAX_CANDLESTICKS, int(number_of_candlesticks_from_start_to_now))
        response: v20.response = self.api.instrument.candles(instrument=pair, fromTime=time.mktime(from_time.timetuple()), granularity=granularity.name, price='MBA',
                                                             count=number_of_candlesticks_to_fetch)
        if response.status != 200:
            raise HTTPException(
                "Cannot get candlesticks for currency pair {}, status code: {}, error message: {}".format(pair, response.status, response.body.errorMessage))
        candles: DataFrame = DataFrame([prepare_candle(vars(candle)) for candle in response.body['candles'] if candle.complete])
        # candles[CandleDefinitions.CANDLES_DF_COLUMNS] = candles[CandleDefinitions.CANDLES_DF_COLUMNS].apply(pd.to_numeric, errors='coerce')
        # candles['time'] = pd.to_datetime(pd.to_numeric(candles['time']), unit='s')
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
        candles: List[DataFrame] = []
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
        response: v20.response = self.api.account.instruments(OANDA_LIVE_ACCOUNT_ID if self.live else OANDA_DEMO_ACCOUNT_ID)
        instruments = DataFrame([vars(instrument) for instrument in response.body['instruments']])
        save_instruments_to_file(instruments)
        return instruments

    @staticmethod
    def get_pip_location(pair: str) -> float:
        try:
            instruments: DataFrame = pd.read_pickle(INSTRUMENTS_FILENAME)
        except IOError:
            raise IOError("Instruments file could not be found. Please first retrieve account instruments using get_instruments_and_save_to_file().")
        return float(instruments.query('name=="{}"'.format(pair))['pipLocation'].iloc[0])

    def create_data_for_pair(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime = datetime.now()) -> DataFrame:
        candles: DataFrame = self.get_candles_for_pair(pair=pair, granularity=granularity, from_time=from_time, to_time=to_time)
        print("Loaded {} candles for pair {}, from {} to {}".format(candles.shape[0], pair, candles['time'].min(), candles['time'].max()))
        if not validate_candles_df(candles):
            raise AssertionError("The candles DataFrame does not match the required schema:", )
        save_candles_to_file(candles, pair, granularity, from_time, to_time)
        return candles

    @deprecated("Replaced with new implementation retrieving latest candle from OANDA. Will be removed with next commit.")
    def get_price(self, pair: str) -> Dict[str, datetime | float]:
        """
        For a given pair, returns the latest ask, bid and midpoint prices, as well as the timestamp.
        :param pair: Currency pair to get the latest price for.
        :return: A dictionary containing the ask, bid and midpoint prices and the timestamp.
        """
        response: v20.response = self.api.pricing.get(OANDA_LIVE_ACCOUNT_ID if self.live else OANDA_DEMO_ACCOUNT_ID, instruments=pair)
        if response.status != 200:
            raise HTTPException(
                "Cannot get price for currency pair {}, status code: {}, error message: {}".format(pair, response.status, response.reason))
        ask: float = float(response.body['prices'][0].asks[0].price)
        bid: float = float(response.body['prices'][0].bids[0].price)
        mid: float = (ask + bid) / 2
        candle_time: datetime = datetime.fromtimestamp(float(response.body['prices'][0].time))
        return {'ask': ask, 'bid': bid, 'mid': mid, 'time': candle_time}

    def get_latest_candle(self, pair: str, granularity: Granularity) -> Candle:
        """
        For a given pair, returns the latest candle, given the granularity and price type.
        :param granularity: Granularity of the latest candlestick to fetch.
        :param pair: Currency pair to get the latest price for.
        :return: A dictionary containing the latest candle.
        """
        response: v20.response = self.api.instrument.candles(instrument=pair, count=1, granularity=granularity.name, price='MBA')
        if response.status != 200:
            raise HTTPException("Cannot get price for currency pair {}, status code: {}, error message: {}".format(pair, response.status, response.reason))
        # We should get one candle only so this should work
        candle: Dict[str, float | datetime] = next(prepare_candle(vars(candle)) for candle in response.body['candles'] if candle['complete'])
        return Candle.from_dict(candle)
