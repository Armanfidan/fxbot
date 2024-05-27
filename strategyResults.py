from typing import Dict, Any, Tuple

import pandas as pd

from utilities import Strategy


class StrategyResults:
    def __init__(self, pair: str, strategy: Strategy, params: Dict[str, Any], historical_data: pd.DataFrame):
        self.pair: str = pair
        self.strategy: Strategy = strategy
        self.params: Dict[str, Any] = params
        self.historical_data: pd.DataFrame = historical_data
        self.num_longs, self.num_shorts = self._strategy_stats()
        self.total_trades = self.num_shorts + self.num_longs
        self.total_gain, self.mean_gain, self.min_gain, self.max_gain = self._evaluate_strategy()

    def _strategy_stats(self) -> Tuple[float, float]:
        return (self.historical_data['trade'] == 1).sum(), (self.historical_data['trade'] == -1).sum()

    def _evaluate_strategy(self) -> Tuple[float, float, float, float]:
        if 'trade' not in self.historical_data.columns:
            raise ValueError('Please generate trades before evaluating the strategy.')
        buy_hold_returns = self.historical_data['mid.c'] - self.historical_data['mid.c'].shift(1)
        strategy_log_returns = buy_hold_returns * self.historical_data['trade']
        return strategy_log_returns.sum(), strategy_log_returns.mean(), strategy_log_returns.min(), strategy_log_returns.max()
