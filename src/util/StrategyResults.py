from typing import Dict, Any, Tuple
from pandas import DataFrame

from Strategy import Strategy


class StrategyResults:
    def __init__(self, pair: str, strategy: Strategy, params: Dict[str, Any], signals: DataFrame):
        self.pair: str = pair
        self.strategy: Strategy = strategy
        self.params: Dict[str, Any] = params
        self.trades: DataFrame = signals
        self.num_longs, self.num_shorts = self._strategy_stats()
        self.total_trades = self.num_shorts + self.num_longs
        self.buy_hold_returns, self.total_gain, self.mean_gain, self.min_gain, self.max_gain = self._evaluate_strategy()

    def _strategy_stats(self) -> Tuple[float, float]:
        """
        :return: A tuple containing the number of buys and the number of sells
        """
        return (self.trades['signal'] == 1).sum(), (self.trades['signal'] == -1).sum()

    def _evaluate_strategy(self) -> Tuple[float, float, float, float, float]:
        """
        Evaluates the strategy against buying the stock once and holding.
        :return: The total return from buying and holding the stock, and the total, mean, min and max return obtained from the strategy.
        """
        if 'signal' not in self.trades.columns:
            raise ValueError('Please generate trades before evaluating the strategy.')
        buy_hold_returns = self.trades['gain'] * self.trades['signal']
        return buy_hold_returns.sum(), self.trades['gain'].sum(), self.trades['gain'].mean(), self.trades['gain'].min(), self.trades['gain'].max()
