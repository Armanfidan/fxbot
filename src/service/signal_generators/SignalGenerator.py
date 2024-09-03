from collections import deque

import pandas as pd
import seaborn as sns

from pandas import DataFrame

from src.util.IndicatorEvaluator import IndicatorEvaluator
from src.model.candle.Candle import Candle
from src.model.Granularity import Granularity
from src.model.signal_generator_iterations.SignalGeneratorIteration import SignalGeneratorIteration

pd.options.mode.chained_assignment = None
sns.set_theme()


class SignalGenerator:
    """
    Parent class SignalGenerator. Extend for each indicator and implement iterate().
    """
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, initial_candles: DataFrame):
        self.pair: str = pair
        self.pip_location: float = pip_location
        self.granularity: Granularity = granularity
        self.queue: deque[SignalGeneratorIteration] | None = None

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
        Iterate the signal generator. Append the SignalGeneratorIteration object to the queue.
        Do not forget to append the latest candle to the queue when implementing.
        :param candle: The latest candle.
        """
        raise NotImplementedError("Please implement method before iterating the signal generator.")

    # TODO: Use use_pips
    def generate_signals_for_backtesting(self, candles: DataFrame, use_pips: bool) -> None:
        """
        Generate signals based on a pre-defined indicator. Use this to generate all signals in one go, for backtesting.
        :param candles: DataFrame containing all historical data to generate signals for.
        :param use_pips: Whether to use pips to calculate returns. If false, will use nominal value.
        :return: A dataframe of historical price data with a column representing signal signals (1 for buy, -1 for sell).
        """
        if self.queue:
            raise ValueError("Please do not initialise the iteration queue if backtesting.")
        self.iterate_from_dataframe(candles)

    def generate_signals_dataframe(self) -> DataFrame:
        if not self.queue:
            raise ValueError("Please iterate the signal generator before attempting to retrieve signals.")
        return DataFrame([vars(iteration.candle) | {"signal": iteration.signal} for iteration in self.queue])

    def evaluate_indicator(self) -> IndicatorEvaluator:
        """
        I need a way of evaluating the strategies I implement.
        What metrics do I need?
        - Return on investment - This is easy, calculate based on the trades you have done. This is the first step.
        - Sharpe ratio - This is more complicated.
            - First you need to retrieve the risk-free rate. For FX this is difficult, as you do not really know which
              risk-free rate to use. You're trading multiple currencies, so which one do you use?
              Generally these will all be correlated, but still it might be a good idea to use the average US treasury bond
              yield for the period that you are evaluating the strategy for.
            - You also need the return on investment, but you will already have this calculated, as part of your evaluation.
            - Then you need the standard deviation of the trades you have made. For this I will require a list of gains from each trade that was made.
              Let's say one trade gave me $10000 but another trade made me lose $20000. I can collect this data for every trade and calculate the std.
            - Once I have the data required, the Sharpe ratio can be calculated as follows: S(x) = (rx-Rf)/StdDev(x)
        - Maximum Drawdown - This is the maximum loss you have made from a peak in your trades, until it recovers to a new peak.
        - Profit to drawdown ratio - This is your profit to your maximum drawdown - important because if this is not higher than 2:1, your strategy might be
          too risky.
        - Total time in the market - Calculate the duration of each trade. The performance of a strategy will depend on the short, medium and long-term
        - properties of a currency pair, which is important to calculate.
        - You should also compare the results to indices such as the S&P 500.
        :return:
        """
        indicator_evaluation: IndicatorEvaluator = IndicatorEvaluator(
            pair=self.pair,
            signals=self.generate_signals_dataframe(),
        )
        return indicator_evaluation
