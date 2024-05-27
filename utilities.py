from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import plotly.graph_objects as go

import constants


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


def save_instruments_to_file(instruments: pd.DataFrame):
    """
    Save instruments to file.
    :param instruments: DF containing candles.
    """
    try:
        instruments.to_pickle(constants.INSTRUMENTS_FILENAME)
    except Exception as e:
        raise IOError("Could not save instruments to file. Error: {}".format(e))


def save_candles_to_file(candles: pd.DataFrame, pair: str, granularity: str):
    """
    Save candles to file.
    :param candles: DF containing candles.
    :param pair: Currency pair that the candles belong to.
    :param granularity: Granularity of the candles.
    """
    pickle_path = '{}/{}_{}.pkl'.format(constants.CANDLE_FOLDER, pair, granularity)
    try:
        Path(constants.CANDLE_FOLDER).mkdir(parents=True, exist_ok=True)
        candles.to_pickle(pickle_path)
    except Exception as e:
        raise IOError("Could not save candles to file. Error: {}".format(e))


def get_historical_data_filename(pair: str, granularity: str) -> str:
    return '{}/{}_{}.pkl'.format(constants.CANDLE_FOLDER, pair, granularity)


def plot_candles(pair: str, granularity: str):
    candles = get_price_data(pair, granularity)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=candles.time, open=candles['mid.o'], high=candles['mid.h'], low=candles['mid.l'], close=candles['mid.c']))
    fig.show()


def get_price_data(pair: str, granularity: str) -> pd.DataFrame:
    candles = pd.read_pickle(get_historical_data_filename(pair, granularity))
    columns = [col for col in candles.columns if col not in ['time', 'volume']]
    candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
    return candles