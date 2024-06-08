from datetime import datetime
from typing import Tuple, Any, Dict

import numpy as np
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt

from strategyResults import StrategyResults
from utilities import get_price_data, Strategy

sns.set_theme()


class TradeGenerator:
    def __init__(self, pair: str, granularity: str, from_time: datetime, to_time: datetime, strategy: Strategy = Strategy.MA_CROSSOVER, historical_data: pd.DataFrame = None):
        self.pair: str = pair
        self.granularity: str = granularity
        self.strategy: Strategy = strategy
        price_columns = ['mid.o', 'mid.h', 'mid.l', 'mid.c']
        self.historical_data: pd.DataFrame = (historical_data[['time'] + price_columns].copy()
                                              if historical_data is not None
                                              else get_price_data(pair, granularity, from_time, to_time)[['time'] + price_columns])
        self.historical_data['returns'] = self.historical_data['mid.c'] - self.historical_data['mid.c'].shift(1)
        self.trades: pd.DataFrame = pd.DataFrame()
        self.params: Dict[str, Any] | None = None

    def _generate_moving_average_indicators(self, short_window: int, long_window: int) -> Tuple[str, str]:
        ma_names: Tuple[str, str] = ('MA_{}'.format(short_window), 'MA_{}'.format(long_window))
        self.historical_data[ma_names[0]] = self.historical_data['mid.c'].rolling(short_window).mean()
        self.historical_data[ma_names[1]] = self.historical_data['mid.c'].rolling(long_window).mean()
        self.historical_data.dropna(inplace=True)
        self.historical_data.reset_index(drop=True, inplace=True)
        return ma_names[0], ma_names[1]

    def _generate_ma_crossover_trades(self, short_window: int, long_window: int):
        ma_short, ma_long = self._generate_moving_average_indicators(short_window, long_window)
        self.historical_data['holding'] = np.where(self.historical_data[ma_short] > self.historical_data[ma_long], 1, -1)
        self.historical_data['trade'] = np.where(self.historical_data['holding'] != self.historical_data['holding'].shift(1), self.historical_data['holding'], 0)
        self.trades = self.historical_data[self.historical_data['trade'] != 0][['time', 'mid.c', 'trade']]

    def _generate_trade_detail_columns(self) -> pd.DataFrame:
        if self.trades.empty:
            raise ValueError("Please generate trades before using this function.")
        self.trades['gain'] = self.trades['mid.c'].diff().shift(-1)
        self.trades['duration'] = self.trades['time'].diff().shift(-1).apply(lambda time: time.seconds / 60)
        return self.trades

    def generate_trades(self, **kwargs) -> pd.DataFrame:
        """
        Generate trades based on a pre-defined strategy.
        :param kwargs:
            If the strategy is "MA_CROSSOVER", two parameters should be passed.
                - short_window: Length of the short window to apply for the moving average.
                - long_window: Length of the long window to apply for the moving average.
            More strategies to be implemented soon.
        :return: A dataframe of historical price data with a column representing trade signals (1 for buy, -1 for sell).
        """
        if self.strategy == Strategy.MA_CROSSOVER:
            self.params = {'short_window': kwargs['short_window'], 'long_window': kwargs['long_window']}
            if not self.params:
                raise ValueError('Please pass the short_window and long_window parameters to genertae trades with the MA crossover strategy.')
            self._generate_ma_crossover_trades(self.params['short_window'], self.params['long_window'])
        return self._generate_trade_detail_columns()

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

