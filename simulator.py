from datetime import datetime
import itertools
import sys
from typing import List, Dict, Tuple

import pandas as pd
from pandas import DataFrame

import constants
from dataFetcher import DataFetcher
from plotProperties import PlotProperties
from strategyResults import StrategyResults
from tradeGenerator import TradeGenerator
from utilities import Strategy, get_price_data, plot_candles

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


class Simulator:
    def __init__(self, strategy: Strategy = Strategy.MA_CROSSOVER, use_downloaded_currency_pairs: bool = True, data_range_for_plotting: PlotProperties = PlotProperties()):
        self.data_fetcher: DataFetcher = DataFetcher()
        self.instruments: DataFrame = (pd.read_pickle(constants.INSTRUMENTS_FILENAME) if use_downloaded_currency_pairs
                                       else self.data_fetcher.get_instruments_and_save_to_file())
        self.strategy: Strategy = strategy
        self.data_range_for_plotting: PlotProperties = data_range_for_plotting
        self.plot_data: Dict[Tuple[str, int, int], DataFrame] = {}

    def get_trade_data_for_all_combinations_of_currencies(self, currencies: List[str], granularity: str, use_downloaded_data: bool, from_time: datetime,
                                                          to_time: datetime) -> Dict[str, DataFrame]:
        currency_data: Dict[str, DataFrame] = {}
        for curr1 in currencies:
            for curr2 in currencies:
                if curr1 == curr2:
                    continue
                pair = '{}_{}'.format(curr1, curr2)
                if pair in self.instruments['name'].unique():
                    currency_data[pair] = (get_price_data(pair, granularity, from_time, to_time) if use_downloaded_data else
                                           self.data_fetcher.create_data_for_pair(pair, granularity, from_time, to_time))
        return currency_data

    @staticmethod
    def create_results_df(results: List[StrategyResults]) -> DataFrame:
        results_dicts: List[Dict[str, str]] = []
        for result in results:
            result_dict: Dict[str, str] = vars(result) | result.params
            result_dict['strategy'] = result.strategy.value
            result_dict.pop('params')
            result_dict.pop('trades')
            results_dicts.append(result_dict)
        results_df: DataFrame = DataFrame(results_dicts)
        return results_df.set_index('pair')

    def save_results(self, results: DataFrame, file_type: Literal['csv', 'pickle']) -> None:
        if file_type == 'csv':
            results.to_csv('{}_test_res.csv'.format(self.strategy.value))
        else:
            results.to_pickle('{}_test_res.pkl'.format(self.strategy.value))
        print(results)

    def plot_results_for_selected_data(self):
        if not self.plot_data:
            raise ValueError("No data saved for plotting.")
        for (pair, short_window, long_window), data in self.plot_data.items():
            plot_start = self.data_range_for_plotting.from_time
            plot_end = self.data_range_for_plotting.to_time
            title = "{} Strategy Results for Currency Pair {}, with windows {} and {}, from {} to {}" \
                .format(self.strategy.value, pair, short_window, long_window, plot_start, plot_end)
            plot_candles(data, plot_start, plot_end, short_window, long_window, title)

    def run(self,
            currencies: List[str],
            from_time: datetime,
            to_time: datetime = datetime.now(),
            use_downloaded_data: bool = False,
            granularity: str = 'H1',
            ma_windows=None, file_type: str = 'csv') -> None:

        if ma_windows is None:
            ma_windows = [4, 8, 16, 32, 64, 96, 128, 256]
        historical_price_data_for_currencies = self.get_trade_data_for_all_combinations_of_currencies(currencies, granularity, use_downloaded_data, from_time,
                                                                                                      to_time)
        results: List[StrategyResults] = []
        for pair, price_data in historical_price_data_for_currencies.items():
            print("Running simulation for pair", pair)
            trade_generator: TradeGenerator = TradeGenerator(pair, granularity, from_time, to_time, self.strategy, price_data)

            for short_window, long_window in itertools.combinations(ma_windows, 2):
                if short_window >= long_window:
                    continue
                trade_generator.generate_trades(short_window=short_window, long_window=long_window)
                results.append(trade_generator.evaluate_strategy())

                if pair in self.data_range_for_plotting.currency_pairs and (short_window, long_window) in self.data_range_for_plotting.ma_pairs:
                    self.plot_data[(pair, short_window, long_window)] = trade_generator.historical_data.copy()

        results_df = self.create_results_df(results)
        self.save_results(results_df, file_type)
