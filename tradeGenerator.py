import functools
from datetime import datetime
from typing import Tuple, Any, Dict, Literal

import numpy as np
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt
from pandas import DataFrame

from strategyResults import StrategyResults
from utilities import get_price_data, Strategy

sns.set_theme()


ENTRY_PRICE_MUL = 0.1
STOP_LOSS_MUL = 0.4
TAKE_PROFIT_MUL = 0.8


class TradeGenerator:
    def __init__(self, pair: str, pip_location: float, granularity: str, from_time: datetime, to_time: datetime, strategy: Strategy = Strategy.MA_CROSSOVER, historical_data: DataFrame = None):
        self.pair: str = pair
        self.pip_location: float = pip_location
        self.granularity: str = granularity
        self.strategy: Strategy = strategy
        price_columns = ['mid_o', 'mid_h', 'mid_l', 'mid_c']
        self.historical_data: DataFrame = (historical_data[['time'] + price_columns].copy() if historical_data is not None
                                              else get_price_data(pair, granularity, from_time, to_time)[['time'] + price_columns])
        self.historical_data['returns'] = self.historical_data['mid_c'] - self.historical_data['mid_c'].shift(1)
        self.trades: DataFrame = pd.DataFrame()
        self.params: Dict[str, Any] = {}

    def _generate_moving_average_indicators(self, short_window: int, long_window: int) -> Tuple[str, str]:
        ma_names: Tuple[str, str] = ('MA_{}'.format(short_window), 'MA_{}'.format(long_window))
        self.historical_data[ma_names[0]] = self.historical_data['mid_c'].rolling(short_window).mean()
        self.historical_data[ma_names[1]] = self.historical_data['mid_c'].rolling(long_window).mean()
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)
        return ma_names[0], ma_names[1]

    def _generate_ma_crossover_trades(self, short_window: int, long_window: int):
        ma_short, ma_long = self._generate_moving_average_indicators(short_window, long_window)
        self.historical_data['holding'] = np.where(self.historical_data[ma_short] > self.historical_data[ma_long], 1, -1)
        self.historical_data['trade'] = np.where(self.historical_data['holding'] != self.historical_data['holding'].shift(1), self.historical_data['holding'], 0)
        self.trades = self.historical_data[self.historical_data['trade'] != 0][['time', 'mid_c', 'trade']]

    def _generate_inside_bar_momentum_indicators(self):
        self.historical_data['range_prev'] = (self.historical_data['mid_h'] - self.historical_data['mid_l']).shift(1)
        # self.historical_data['range_prev'] = self.historical_data['range'].shift(1)
        self.historical_data['mid_h_prev'] = self.historical_data['mid_h'].shift(1)
        self.historical_data['mid_l_prev'] = self.historical_data['mid_l'].shift(1)
        self.historical_data['direction_prev'] = self.historical_data.apply(lambda row: 1 if row['mid_c'] > row['mid_o'] else -1, axis=1).shift(1).fillna(0).astype(int)
        # self.historical_data['direction_prev'] = self.historical_data['direction'].
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)

    @staticmethod
    def _inside_bar_momentum_indicators(indicator: Literal['entry_stop', 'stop_loss', 'take_profit'], row: Dict[str, float]):
        if indicator == 'entry_stop':
            return row['mid_h_prev'] + row['trade'] * (row['range_prev'] * ENTRY_PRICE_MUL)
        if indicator == 'stop_loss':
            return row['mid_h_prev'] + row['trade'] * (row['range_prev'] * STOP_LOSS_MUL)
        if indicator == 'take_profit':
            return row['mid_h_prev'] + row['trade'] * (row['range_prev'] * TAKE_PROFIT_MUL)

    def _generate_inside_bar_momentum_trades(self):
        self._generate_inside_bar_momentum_indicators()
        self.historical_data['trade'] = self.historical_data.apply(lambda row: row['direction_prev'] if row['mid_h_prev'] > row['mid_h'] and row['mid_l_prev'] < row['mid_l'] else 0, axis=1)
        self.historical_data['entry_stop'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'entry_stop'), axis=1)
        self.historical_data['stop_loss'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'stop_loss'), axis=1)
        self.historical_data['take_profit'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'take_profit'), axis=1)
        self.trades = self.historical_data[self.historical_data['trade'] != 0]

    def _generate_trade_detail_columns(self, use_pips: bool) -> pd.DataFrame:
        if self.trades.empty:
            raise ValueError("Please generate trades before using this function.")
        if use_pips:
            self.trades['gain'] = (self.trades['mid_c'].diff() / 10 ** self.pip_location).shift(-1)
        else:
            self.trades['gain'] = self.trades['mid_c'].diff().shift(-1)
        self.trades['duration'] = self.trades['time'].diff().shift(-1).apply(lambda time: time.seconds / 60)
        return self.trades

    def generate_trades(self, use_pips: bool, **kwargs) -> pd.DataFrame:
        """
        Generate trades based on a pre-defined strategy.
        :param use_pips: Whether to use pips to calculate returns. If false, will use nominal value.
        :param kwargs:
            If the strategy is "MA_CROSSOVER", two parameters should be passed.
                - short_window: Length of the short window to apply for the moving average.
                - long_window: Length of the long window to apply for the moving average.
            If the strategy is "INSIDE_BAR_MOMENTUM", no parameters need to be passed.
        :return: A dataframe of historical price data with a column representing trade signals (1 for buy, -1 for sell).
        """
        if self.strategy == Strategy.MA_CROSSOVER:
            self.params = {'short_window': kwargs['short_window'], 'long_window': kwargs['long_window']}
            if not self.params:
                raise ValueError('Please pass the short_window and long_window parameters to genertae trades with the MA crossover strategy.')
            self._generate_ma_crossover_trades(self.params['short_window'], self.params['long_window'])
        elif self.strategy == Strategy.INSIDE_BAR_MOMENTUM:
            self._generate_inside_bar_momentum_trades()
        return self._generate_trade_detail_columns(use_pips)

    def evaluate_pair_returns(self):
        self.historical_data['log_returns'] = np.log(1 + self.historical_data['returns'])
        self.historical_data['log_returns'].plot(title='Log returns of {} currency pair'.format(self.pair), xlabel='Date', ylabel='Return', rot=45)
        plt.show()
        self.historical_data['log_returns'].hist(bins=80).set_xlabel("Histogram of log returns of {} currency pair".format(self.pair))
        plt.show()

    def evaluate_strategy(self) -> StrategyResults:
        strategy_results: StrategyResults = StrategyResults(
            pair=self.pair,
            strategy=self.strategy,
            params=self.params,
            trades=self.trades,
        )
        return strategy_results

