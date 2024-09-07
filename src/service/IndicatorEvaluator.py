from datetime import timedelta
from typing import Tuple, List, Dict

import numpy as np
from pandas import DataFrame

# For now hardcoding the current 10-year US treasury bond yield.
# TODO: Write a new client to retrieve 10-year treasury yields for the currencies being traded.
RISK_FREE_RATE: float = 0.03713


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

    def calculate_roi(self) -> Dict[str, float | DataFrame]:
        """
        Method to calculate the return on investment with the used indicator. Uses bid prices for sell signals and ask prices for buy signals.
        :return: A dictionary consisting of:
                 - The ROI of buy-and-hold strategy for the data (benchmark),
                 - The ROI of using the indicator for the data,
                 - A copy of the signals dataframe with the following added columns: "log_returns_buy_and_hold", "log_returns_of_indicator"
        """
        # Function to choose ask price for buy signal and bid price for sell signal
        def choose_price(row: Dict[str, int | float]) -> float:
            return row['ask_c'] if row['signal'] == 1 else row['bid_c']

        signals: DataFrame = self.signals[self.signals['signal'] != 0]
        signals['trade_price'] = signals.apply(choose_price, axis=1)
        signals['log_returns_buy_and_hold'] = np.log(signals['trade_price'] / signals['trade_price'].shift(1))
        signals['log_returns_of_indicator'] = signals['log_returns_buy_and_hold'] * signals['signal'].shift(1).fillna(0)
        signals.drop(columns=['trade_price'], inplace=True)
        return {"roi_buy_and_hold": np.exp(signals['log_returns_buy_and_hold'].sum()),
                "roi_indicator": np.exp(signals['log_returns_of_indicator'].sum()),
                "signals_and_returns": signals}

    def calculate_standard_deviation_of_returns(self, returns_df: DataFrame) -> float:
        """
        Given a returns DataFrame, calculate the standard deviation of the returns.
        :param returns_df: A DataFrame consisting of:
                           - The candles and signals
                           - A column titled "log_returns_buy_and_hold"
                           - A column titled "log_returns_of_indicator"
        :return: A dictionary consisting of:
                 - The standard deviation of the buy-and-hold returns
                 - The standard deviation of the indicator returns
        """


    def calculate_sharpe_ratio(self) -> float:
        pass

    def compare_to_index(self, index) -> float:
        """
        Method to compare the results obtained by trading using this indicator to the returns of holding a given index
        over the specified period.
        :param index: The index to compare the returns to.
        :return:
        """
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
