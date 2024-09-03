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
    """
    Parent class SignalGenerator. Extend for each strategy and implement iterate().
    """
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, initial_candles: DataFrame):
        self.pair: str = pair
        self.pip_location: float = pip_location
        self.granularity: Granularity = granularity
        self.queue: deque[StrategyIteration] | None = None

    def iterate_from_dataframe(self, candles: DataFrame) -> None:
        """
        Use this method to iterate the generator based on candles in a provided DataFrame.
        :param candles: The candles to generate signals for.
        """
        for index, row in candles.iterrows():
            candle: Candle = Candle.from_dict(row.to_dict())  # TODO: Check whether this is correct
            self.iterate(candle)

    def iterate(self, candle: Candle) -> None:
        """
        Iterate the signal generator. Append the StrategyIteration object to the queue.
        Do not forget to append the latest candle to the queue when implementing.
        :param candle: The latest candle.
        """
        raise NotImplementedError("Please implement method before iterating the signal generator.")

    def generate_signals_for_backtesting(self, candles: DataFrame, use_pips: bool) -> None:
        """
        Generate signals based on a pre-defined strategy. Use this to generate all signals in one go, for backtesting.
        :param candles: DataFrame containing all historical data to generate signals for.
        :param use_pips: Whether to use pips to calculate returns. If false, will use nominal value.
        :return: A dataframe of historical price data with a column representing signal signals (1 for buy, -1 for sell).
        """
        if self.queue:
            raise ValueError("Please do not initialise the iteration queue if backtesting.")
        self.iterate_from_dataframe(candles)
