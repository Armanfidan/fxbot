import functools
from typing import Tuple, Any, Dict, Literal

import numpy as np
import pandas as pd
import seaborn as sns

from pandas import DataFrame

from strategyResults import StrategyResults
from utilities import Strategy, Granularity

pd.options.mode.chained_assignment = None
sns.set_theme()


ENTRY_PRICE_MUL = 0.1
STOP_LOSS_MUL = 0.4
TAKE_PROFIT_MUL = 0.8


class SignalGenerator:
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, historical_data: DataFrame, strategy: Strategy = Strategy.MA_CROSSOVER):
        self.pair: str = pair
        self.pip_location: float = pip_location
        self.granularity: Granularity = granularity
        self.strategy: Strategy = strategy
        self.historical_data: DataFrame = DataFrame()
        self.set_historical_data(historical_data)
        self.signals: DataFrame = DataFrame()
        self.params: Dict[str, Any] = {}
        
    def set_historical_data(self, historical_data: DataFrame):
        self.historical_data = historical_data.copy()

    def _generate_moving_average_indicators(self, short_window: int, long_window: int) -> Tuple[str, str]:
        ma_names: Tuple[str, str] = ('MA_{}'.format(short_window), 'MA_{}'.format(long_window))
        self.historical_data[ma_names[0]] = self.historical_data['mid_c'].rolling(short_window).mean()
        self.historical_data[ma_names[1]] = self.historical_data['mid_c'].rolling(long_window).mean()
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)
        return ma_names[0], ma_names[1]

    def _generate_ma_crossover_signals(self, short_window: int, long_window: int):
        ma_short, ma_long = self._generate_moving_average_indicators(short_window, long_window)
        self.historical_data['holding'] = np.where(self.historical_data[ma_short] > self.historical_data[ma_long], 1, -1)
        self.historical_data['signal'] = np.where(self.historical_data['holding'] != self.historical_data['holding'].shift(1), self.historical_data['holding'], 0)
        self.signals = self.historical_data[self.historical_data['signal'] != 0][['time', 'mid_c', 'signal']]

    def _generate_inside_bar_momentum_indicators(self):
        self.historical_data['range_prev'] = (self.historical_data['mid_h'] - self.historical_data['mid_l']).shift(1)
        self.historical_data['mid_h_prev'] = self.historical_data['mid_h'].shift(1)
        self.historical_data['mid_l_prev'] = self.historical_data['mid_l'].shift(1)
        self.historical_data['direction_prev'] = self.historical_data.apply(lambda row: 1 if row['mid_c'] > row['mid_o'] else -1, axis=1).shift(1)
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)

    def _inside_bar_momentum_indicators(self, indicator: Literal['entry_stop', 'stop_loss', 'take_profit'], row: Dict[str, float]):
        if self.granularity not in [Granularity.H4, Granularity.H6, Granularity.H8, Granularity.H12, Granularity.D, Granularity.W, Granularity.M]:
            raise ValueError('Please enter a granularity larger than or equal to H4 to generate inside bar momentum indicators.')
        reference_price_column = 'mid_h_prev' if row['signal'] == 1 else 'mid_l_prev'
        if indicator == 'entry_stop':
            return row[reference_price_column] + row['signal'] * (row['range_prev'] * ENTRY_PRICE_MUL)
        if indicator == 'stop_loss':
            return row[reference_price_column] + -1 * row['signal'] * (row['range_prev'] * STOP_LOSS_MUL)
        if indicator == 'take_profit':
            return row[reference_price_column] + row['signal'] * (row['range_prev'] * TAKE_PROFIT_MUL)

    def _generate_inside_bar_momentum_signals(self):
        self._generate_inside_bar_momentum_indicators()
        self.historical_data['signal'] = self.historical_data.apply(lambda row: row['direction_prev'] if row['mid_h_prev'] > row['mid_h'] and row['mid_l_prev'] < row['mid_l'] else 0, axis=1)
        self.historical_data['entry_stop'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'entry_stop'), axis=1)
        self.historical_data['stop_loss'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'stop_loss'), axis=1)
        self.historical_data['take_profit'] = self.historical_data.apply(functools.partial(self._inside_bar_momentum_indicators, 'take_profit'), axis=1)
        self.historical_data.drop(['mid_h_prev', 'mid_l_prev', 'direction_prev'], axis=1, inplace=True)
        self.signals = self.historical_data[self.historical_data['signal'] != 0]

    def generate_inside_bar_momentum_signal_detail_columns(self, use_pips: bool) -> DataFrame:
        if self.signals.empty or 'entry_time' not in self.historical_data.columns:
            raise ValueError("Please generate signals before using this function.")
        gain_literal = (self.historical_data['exit_price'] - self.historical_data['entry_price']) * self.historical_data['signal']
        self.historical_data['gain'] = gain_literal / (10 ** self.pip_location if use_pips else 1)
        self.historical_data['duration'] = (self.historical_data['exit_time'] - self.historical_data['entry_time']).apply(lambda time: time.seconds / 60)
        self.signals = self.historical_data[self.historical_data['signal'].notna()]
        return self.signals

    def _generate_ma_crossover_signal_detail_columns(self, use_pips: bool) -> DataFrame:
        if self.signals.empty:
            raise ValueError("Please generate signals before using this function.")
        if use_pips:
            self.signals['gain'] = (self.signals['mid_c'].diff() / 10 ** self.pip_location).shift(-1)
        else:
            self.signals['gain'] = self.signals['mid_c'].diff().shift(-1)
        self.signals['duration'] = self.signals['time'].diff().shift(-1).apply(lambda time: time.seconds / 60)
        return self.signals

    def generate_signals(self, use_pips: bool, **kwargs) -> DataFrame:
        """
        Generate signals based on a pre-defined strategy.
        :param use_pips: Whether to use pips to calculate returns. If false, will use nominal value.
        :param kwargs:
            If the strategy is "MA_CROSSOVER", two parameters should be passed.
                - short_window: Length of the short window to apply for the moving average.
                - long_window: Length of the long window to apply for the moving average.
            If the strategy is "INSIDE_BAR_MOMENTUM", no parameters need to be passed.
        :return: A dataframe of historical price data with a column representing signal signals (1 for buy, -1 for sell).
        """
        if self.strategy == Strategy.MA_CROSSOVER:
            self.params = {'short_window': kwargs['short_window'], 'long_window': kwargs['long_window']}
            if not self.params:
                raise ValueError('Please pass the short_window and long_window parameters to generate signals with the MA crossover strategy.')
            self._generate_ma_crossover_signals(self.params['short_window'], self.params['long_window'])
            return self._generate_ma_crossover_signal_detail_columns(use_pips)
        elif self.strategy == Strategy.INSIDE_BAR_MOMENTUM:
            self._generate_inside_bar_momentum_signals()
            return self.signals

    # def evaluate_pair_returns(self):
    #     self.historical_data['returns'] = self.historical_data['mid_c'] - self.historical_data['mid_c'].shift(1)
    #     self.historical_data['log_returns'] = np.log(1 + self.historical_data['returns'])
    #     self.historical_data['log_returns'].plot(title='Log returns of {} currency pair'.format(self.pair), xlabel='Date', ylabel='Return', rot=45)
    #     plt.show()
    #     self.historical_data['log_returns'].hist(bins=80).set_xlabel("Histogram of log returns of {} currency pair".format(self.pair))
    #     plt.show()

    def evaluate_strategy(self) -> StrategyResults:
        strategy_results: StrategyResults = StrategyResults(
            pair=self.pair,
            strategy=self.strategy,
            params=self.params,
            signals=self.signals,
        )
        return strategy_results
