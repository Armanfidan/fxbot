from datetime import timedelta
from typing import Tuple, List, Dict

import numpy as np
from pandas import DataFrame, Series

# For now hardcoding the current 10-year US treasury bond yield.
# TODO: Write a new client to retrieve 10-year treasury yields for the currencies being traded.
RISK_FREE_RATE: float = 0.03713
NUM_TRADING_DAYS_IN_A_YEAR: int = 252


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
                 - "roi_buy_and_hold": The ROI of buy-and-hold strategy for the data (benchmark),
                 - "roi_indicator": The ROI of using the indicator for the data,
                 - "signals_and_returns": A copy of the signals dataframe with the following added columns: "log_returns_buy_and_hold", "log_returns_of_indicator"
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

    def calculate_standard_deviation_of_returns(self, returns_df: DataFrame, negative_only: bool = False) -> float:
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
        # What's the difference of the std of log returns vs returns? Which one should I calculate?
        # Looks like I will calculate the standard deviation of returns, not log returns.
        indicator_returns = returns_df['log_returns_of_indicator']
        if negative_only:
            indicator_returns = indicator_returns[indicator_returns < 0]
        return np.std(np.exp(indicator_returns))

    def calculate_mean_of_returns(self, returns_df: DataFrame) -> float:
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
        # What's the difference of the std of log returns vs returns? Which one should I calculate?
        # Looks like I will calculate the standard deviation of returns, not log returns.
        return np.mean(np.exp(returns_df['log_returns_of_indicator']))

    def calculate_annualised_sharpe_ratio(self, returns_df: DataFrame) -> float:
        std: float = self.calculate_standard_deviation_of_returns(returns_df)
        mean: float = self.calculate_mean_of_returns(returns_df)
        return np.sqrt(NUM_TRADING_DAYS_IN_A_YEAR) * (mean - RISK_FREE_RATE) / std

    def calculate_annualised_sortino_ratio(self, returns_df: DataFrame) -> float:
        std: float = self.calculate_standard_deviation_of_returns(returns_df, negative_only=True)
        mean: float = self.calculate_mean_of_returns(returns_df)
        return np.sqrt(NUM_TRADING_DAYS_IN_A_YEAR) * (mean - RISK_FREE_RATE) / std

    def calculate_max_drawdown(self, returns_df: DataFrame) -> float:
        cumulative_returns: Series = np.exp((returns_df['log_returns_of_indicator'] + 1).cumsum())
        # cumulative_max = cumulative_returns.cummax()
        # drawdown = (cumulative_returns - cumulative_max) / cumulative_max
        return np.min(cumulative_returns / cumulative_returns.expanding(min_periods=1).max() - 1)

    def calculate_annualised_calmar_ratio(self, returns_df: DataFrame) -> float:
        return NUM_TRADING_DAYS_IN_A_YEAR * (np.exp(returns_df['log_returns_of_indicator']).mean() - RISK_FREE_RATE) / self.calculate_max_drawdown(returns_df)

    def calculate_profit_to_drawdown_ratio(self) -> float:
        returns: Dict[str, float | DataFrame] = self.calculate_roi()
        return returns['roi_of_indicator'] / self.calculate_max_drawdown(returns['signals_and_returns'])

    @staticmethod
    def calculate_trade_durations(returns_df: DataFrame):
        """
        Calculates the duration of each trade in the given returns_df. Modification is done inplace.
        :param returns_df: The returns DataFrame to calculate durations in.
        """
        returns_df['duration'] = returns_df['time'] - returns_df['time'].shift(1)

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

    def compare_to_buy_and_hold(self):
        pass

    def compare_to_index(self, index) -> float:
        """
        Method to compare the results obtained by trading using this indicator to the returns of holding a given index
        over the specified period.
        :param index: The index to compare the returns to.
        :return:
        """
        pass

