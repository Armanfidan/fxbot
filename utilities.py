from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import plotly.graph_objects as go

import constants


class Strategy(Enum):
    MA_CROSSOVER = 'Moving Average Crossover'


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


def save_candles_to_file(candles: pd.DataFrame, pair: str, granularity: str, from_time: datetime, to_time: datetime):
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


def get_historical_data_filename(pair: str, granularity: str, from_time: datetime, to_time: datetime) -> str:
    return '{}/{}_{}_from_{}_to_{}.pkl'.format(constants.CANDLE_FOLDER, pair, granularity, from_time.strftime("%Y-%m-%dT%H-%M-%S"),
                                               to_time.strftime("%Y-%m-%dT%H-%M-%S"))


def plot_candles(historical_data: pd.DataFrame, from_date: datetime, to_date: datetime, ma_short: int, ma_long: int, title: str) -> None:
    candles = historical_data[(from_date < historical_data['time']) & (historical_data['time'] < to_date)]
    fig = go.Figure(layout_title_text=title)
    fig.add_trace(go.Candlestick(
        x=candles['time'],
        open=candles['mid.o'],
        high=candles['mid.h'],
        low=candles['mid.l'],
        close=candles['mid.c'],
        name='Prices'))
    for col in ["MA_{}".format(ma) for ma in (ma_short, ma_long)]:
        fig.add_trace(go.Scatter(x=candles['time'],
                                 y=candles[col],
                                 line=dict(width=2, shape='spline'),
                                 name=col
                                 ))
    fig.add_trace(go.Scatter(mode='markers',
                             x=candles[candles['trade'] == -1]['time'],
                             y=candles[candles['trade'] == -1]['mid.c'],
                             marker=dict(symbol='arrow-down',
                                         size=20,
                                         color='#eb5242',
                                         line_color='#e67c70',
                                         line_width=2
                                         ),
                             name='Sell'
                             ))
    fig.add_trace(go.Scatter(mode='markers',
                             x=candles[candles['trade'] == 1]['time'],
                             y=candles[candles['trade'] == 1]['mid.c'],
                             marker=dict(symbol='arrow-up',
                                         size=20,
                                         color='#579773',
                                         line_color='#95cfae',
                                         line_width=2
                                         ),
                             name='Buy'
                             ))
    fig.update_layout(font=dict(size=10, color="#e1e1e1"),
                      paper_bgcolor="#1e1e1e",
                      plot_bgcolor="#1e1e1e")
    fig.update_xaxes(
        gridcolor="#1f292f",
        showgrid=True, fixedrange=False
    )
    fig.update_yaxes(
        gridcolor="#1f292f",
        showgrid=True, fixedrange=False
    )
    fig.show()


def get_price_data(pair: str, granularity: str, from_time: datetime, to_time: datetime) -> pd.DataFrame:
    try:
        candles = pd.read_pickle(get_historical_data_filename(pair, granularity, from_time, to_time))
    except FileNotFoundError:
        print("No historical data found for currency pair {} at granularity {}. Downloading...".format(pair, granularity))
        return pd.DataFrame(columns=['time', 'mid.o', 'mid.h', 'mid.l', 'mid.c'])
    columns = [col for col in candles.columns if col not in ['time', 'volume']]
    candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')
    return candles
