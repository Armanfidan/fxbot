from datetime import timedelta
from typing import Tuple, List, Dict
from pandas import DataFrame


class IndicatorEvaluator:
    """
    A class to calculate and store metrics about backtesting certain indicators:
    - Return on Investment
    - Sharpe ratio
    - Maximum Drawdown
    - Profit to drawdown ratio
    - Total time in market
    """
    def __init__(self, pair: str, signals: DataFrame):
        self.pair: str = pair
        self.signals: DataFrame = signals

    def calculate_roi(self) -> float:
        """
        Method to calculate the return on investment with the used indicator.
        Calculating ROI:
        - You have candles, each with a signal.
          You'll subtract the candle price at a "buy" signal and add the price at a "sell" signal.
        :return: Total ROI of the indicator over the given timeframe.
        """
        def choose_price(row: Dict[str, int | float]) -> float:
            return row['ask_c'] if row['signal'] == 1 else row['bid_c']

        return self.signals.apply(lambda row: choose_price(row) * row['signal'], axis=1).sum()

    def compare_to_index(self, index) -> float:
        """
        Method to compare the results obtained by trading using this indicator to the returns of holding a given index
        over the specified period.
        :param index: The index to compare the returns to.
        :return:
        """
        pass

    def calculate_sharpe_ratio(self) -> float:
        pass

    def calculate_max_drawdown(self) -> float:
        pass

    def calculate_profit_to_drawdown_ratio(self) -> float:
        pass

    def calculate_trade_durations(self) -> List[timedelta]:
        pass

    def calculate_total_time_in_market(self) -> timedelta:
        pass

    def calculate_secondary_metrics(self):
        """
        Calculate other metrics (might still be useful), such as:
        - Total number of long positions
        - Total number of short positions
        - Durations of each position
        - Whether short or long positions are held for longer
        More metrics can be added as required.
        :return: The metrics (In a format that will be agreed upon later).
        """
        pass
