from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from pandas import DataFrame

from Constants import INSTRUMENTS_FILENAME, CANDLE_FOLDER
from Granularity import Granularity
from PriceColumns import PriceColumns


def flatten_candle(candle: Dict[str, Any]):
    """
    Flatten a candle dictionary.
    :param candle: The candle to flatten. Do not pass the Candlestick object - rather do vars(candle) before passing.
    :return: The flattened candle.
    """
    prices: List[str] = ['mid', 'bid', 'ask']
    candle_dict: Dict[str, str] = {}
    for price in prices:
        candle_dict.update({'{}.{}'.format(price, subprice): value for subprice, value in vars(candle[price]).items()})
    return {'time': candle['time'], 'volume': candle['volume']} | candle_dict


def save_instruments_to_file(instruments: DataFrame):
    """
    Save instruments to file.
    :param instruments: DF containing candles.
    """
    try:
        instruments.to_pickle(INSTRUMENTS_FILENAME)
    except Exception as e:
        raise IOError("Could not save instruments to file. Error: {}".format(e))


def save_candles_to_file(candles: DataFrame, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime):
    """
    Save candles to file.
    :param to_time: The date that candles are collected up to.
    :param from_time: The date that the candles start from.
    :param candles: DF containing candles.
    :param pair: Currency pair that the candles belong to.
    :param granularity: Granularity of the candles.
    """
    try:
        Path(CANDLE_FOLDER).mkdir(parents=True, exist_ok=True)
        candles.to_pickle(get_historical_data_filename(pair, granularity, from_time, to_time))
    except Exception as e:
        raise IOError("Could not save candles to file. Error: {}".format(e))


def get_historical_data_filename(pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> str:
    return '{}/{}_{}_from_{}_to_{}.pkl'.format(CANDLE_FOLDER, pair, granularity.name, from_time.strftime("%Y-%m-%dT%H-%M-%S"),
                                               to_time.strftime("%Y-%m-%dT%H-%M-%S"))


def get_downloaded_price_data_for_pair(pair: str, granularity: Granularity, from_time: datetime, to_time: datetime, pc: PriceColumns) -> DataFrame:
    """
    Retrieves downloaded price data for a given pair and granularity, between 2 provided dates. Returns an empty DataFrame if no data is found.
    :param pc: Ask, bid or mid.
    :param pair: Currency pair to retrieve data for
    :param granularity: Granularity to retrieve data for
    :param from_time: Start time to retrieve data from.
    :param to_time: End time to retrieve data to.
    :return: A DataFrame with the retrieved data if found, empty DataFrame if not.
    """
    try:
        candles = pd.read_pickle(get_historical_data_filename(pair, granularity, from_time, to_time))
    except FileNotFoundError:
        print("No historical data found for currency pair {} at granularity {}. Downloading...".format(pair, granularity.name))
        return DataFrame(columns=['time', pc.o, pc.h, pc.l, pc.c])
    columns = [col for col in candles.columns if col not in ['time', 'volume']]
    candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
    return candles
