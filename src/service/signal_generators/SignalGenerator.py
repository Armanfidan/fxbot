from collections import deque
import pandas as pd
import seaborn as sns

from pandas import DataFrame

from candle.Candle import Candle
from Granularity import Granularity
from strategy_iterations.StrategyIteration import StrategyIteration

pd.options.mode.chained_assignment = None
sns.set_theme()


class SignalGenerator:
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, historical_data: DataFrame = None):
        self.pair: str = pair
        self.pip_location: float = pip_location
        self.granularity: Granularity = granularity
        self.queue: deque[StrategyIteration] | None = None
        self.candles_df: DataFrame = DataFrame()
        self.signals: DataFrame = DataFrame()
        if historical_data:
            self.set_candles_df(historical_data)

    def set_candles_df(self, candles_df: DataFrame) -> None:
        self.candles_df = candles_df.copy()

    def set_candles_queue_from_df(self, queue_size: int) -> None:
        if not self.queue:
            raise ValueError('Please initialise the candle queue before attempting to set it.')
        for index, row in self.candles_df.head(queue_size).iterrows():
            candle: Candle = Candle.from_dict(row.to_dict())  # TODO: Check whether this is correct
            iteration: StrategyIteration = self.iterate(candle)
            self.queue.append(iteration)

    def iterate(self, candle: Candle) -> StrategyIteration:
        """
        Iterate the signal generator.
        :return: The latest iteration, with the latest candle, indicators and signal (if any).
        """
        pass

    def generate_signals(self, use_pips: bool) -> DataFrame:
        """
        Generate signals based on a pre-defined strategy. Use this to generate all signals in one go, for backtesting.
        :param use_pips: Whether to use pips to calculate returns. If false, will use nominal value.
        :return: A dataframe of historical price data with a column representing signal signals (1 for buy, -1 for sell).
        """
        for index, row in self.candles_df.iterrows():
            candle: Candle = Candle.from_dict(row.to_dict())  # TODO: Check whether this is correct
            iteration: StrategyIteration = self.iterate(candle)
            self.queue.append(iteration)
        return self.signals
