from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from pandas import DataFrame

import constants


class Granularity(Enum):
    S5 = timedelta(seconds=5)
    S10 = timedelta(seconds=10)
    S15 = timedelta(seconds=15)
    S30 = timedelta(seconds=30)
    M1 = timedelta(minutes=1)
    M2 = timedelta(minutes=2)
    M3 = timedelta(minutes=3)
    M4 = timedelta(minutes=4)
    M5 = timedelta(minutes=5)
    M10 = timedelta(minutes=10)
    M15 = timedelta(minutes=15)
    M30 = timedelta(minutes=30)
    H1 = timedelta(hours=1)
    H2 = timedelta(hours=2)
    H3 = timedelta(hours=3)
    H4 = timedelta(hours=4)
    H6 = timedelta(hours=6)
    H8 = timedelta(hours=8)
    H12 = timedelta(hours=12)
    D = timedelta(days=1)
    W = timedelta(weeks=1)
    M = timedelta(days=30)


class Strategy(Enum):
    MA_CROSSOVER = 'Moving Average Crossover'
    INSIDE_BAR_MOMENTUM = 'Inside Bar Momentum'


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
        instruments.to_pickle(constants.INSTRUMENTS_FILENAME)
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
        Path(constants.CANDLE_FOLDER).mkdir(parents=True, exist_ok=True)
        candles.to_pickle(get_historical_data_filename(pair, granularity, from_time, to_time))
    except Exception as e:
        raise IOError("Could not save candles to file. Error: {}".format(e))


def get_historical_data_filename(pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> str:
    return '{}/{}_{}_from_{}_to_{}.pkl'.format(constants.CANDLE_FOLDER, pair, granularity.name, from_time.strftime("%Y-%m-%dT%H-%M-%S"),
                                               to_time.strftime("%Y-%m-%dT%H-%M-%S"))


def get_price_data(pair: str, granularity: Granularity, from_time: datetime, to_time: datetime) -> DataFrame:
    try:
        candles = pd.read_pickle(get_historical_data_filename(pair, granularity, from_time, to_time))
    except FileNotFoundError:
        print("No historical data found for currency pair {} at granularity {}. Downloading...".format(pair, granularity.name))
        return pd.DataFrame(columns=['time', 'mid_o', 'mid_h', 'mid_l', 'mid_c'])
    columns = [col for col in candles.columns if col not in ['time', 'volume']]
    candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
    return candles
