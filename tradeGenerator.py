from typing import Tuple

import numpy as np
import pandas as pd

from utilities import get_price_data


class TradeGenerator:
    def __init__(self, pair: str, historical_data: pd.DataFrame = None, granularity: str = 'H1'):
        self.pair: str = pair
        self.granularity: str = granularity
        self.historical_data: pd.DataFrame = (historical_data[['time', 'mid.o', 'mid.h', 'mid.l', 'mid.c']].copy()
                                              if historical_data
                                              else get_price_data(pair, granularity)[['time', 'mid.o', 'mid.h', 'mid.l', 'mid.c']])

    def generate_moving_average_indicators(self, short_window: int, long_window: int) -> Tuple[str, str]:
        ma_names: Tuple[str, str] = ('MA_{}'.format(short_window), 'MA_{}'.format(long_window))
        self.historical_data[ma_names[0]] = self.historical_data['mid.c'].rolling(short_window).mean()
        self.historical_data[ma_names[1]] = self.historical_data['mid.c'].rolling(long_window).mean()
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)
        return ma_names[0], ma_names[1]

    def generate_ma_crossover_trades(self, short_window: int = 16, long_window: int = 64):
        ma_short, ma_long = self.generate_moving_average_indicators(short_window, long_window)
        self.historical_data['bought'] = np.where(self.historical_data[ma_short] > self.historical_data[ma_long], 1, 0)
        self.historical_data['trade'] = np.where(self.historical_data['bought'] > self.historical_data['bought'].shift(1), 1, 0)
        self.historical_data['trade'] = np.where(self.historical_data['bought'] < self.historical_data['bought'].shift(1), -1, self.historical_data['trade'])
