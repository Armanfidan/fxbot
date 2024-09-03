from typing import Tuple
from pandas import DataFrame


class IndicatorEvaluator:
    """
    An object to calculate and store metrics about backtesting certain indicators:
    - Return on Investment
    - Sharpe ratio
    - Maximum Drawdown
    - Profit to drawdown ratio
    - Total time in market
    """
    def __init__(self, pair: str, signals: DataFrame):
        self.pair: str = pair
        self.signals: DataFrame = signals
        self.num_longs, self.num_shorts = self._indicator_stats()
        self.total_trades = self.num_shorts + self.num_longs
        self.buy_hold_returns, self.total_gain, self.mean_gain, self.min_gain, self.max_gain = self._evaluate_indicator()

    def _indicator_stats(self) -> Tuple[float, float]:
        """
        :return: A tuple containing the number of buys and the number of sells
        """
        return (self.signals['signal'] == 1).sum(), (self.signals['signal'] == -1).sum()

    def _evaluate_indicator(self) -> Tuple[float, float, float, float, float]:
        """
        Evaluates the indicator against buying the stock once and holding.
        :return: The total return from buying and holding the stock, and the total, mean, min and max return obtained from the strategy.
        """
        if 'signal' not in self.signals.columns:
            raise ValueError('Please generate trades before evaluating the indicator.')
        buy_hold_returns = self.signals['gain'] * self.signals['signal']
        return buy_hold_returns.sum(), self.signals['gain'].sum(), self.signals['gain'].mean(), self.signals['gain'].min(), self.signals['gain'].max()
