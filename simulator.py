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
from utilities import Strategy, get_downloaded_price_data_for_pair, Granularity
from plot_candles import plot_candles_for_ma_crossover, plot_candles_for_inside_bar_momentum

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
        self.plot_data: Dict[Tuple[str, int, int] | str, DataFrame] = {}

    def get_price_data_for_all_combinations_of_currencies(self,
                                                          currencies: List[str],
                                                          granularity: Granularity,
                                                          use_only_downloaded_price_data: bool,
                                                          from_time: datetime,
                                                          to_time: datetime) -> Dict[str, DataFrame]:
        """
        For all selected currency combinations, retrieve historical price data. Look for downloaded prices first. If not found, download from OANDA.
        :param currencies: Currencies to pair up and retrieve data for.
        :param granularity: Price data granularity.
        :param use_only_downloaded_price_data: If True, skips pairs without downloaded data. If false, retrieves data from OANDA for pairs without downloaded data.
        :param from_time: The start date and time to download the price data from.
        :param to_time: The end date and time to download the price data to.
        :return: A dictionary with pairs and their corresponding historical trade data.
        """
        currency_data: Dict[str, DataFrame] = {}
        for curr1 in currencies:
            for curr2 in currencies:
                if curr1 == curr2:
                    continue
                pair = '{}_{}'.format(curr1, curr2)
                if pair not in self.instruments['name'].unique():
                    continue
                price_data: DataFrame = get_downloaded_price_data_for_pair(pair, granularity, from_time, to_time)
                if price_data.size == 0:
                    if use_only_downloaded_price_data:
                        print("No price data found for pair '{}'. Skipping pair - please enable \"use_only_downloaded_data\".".format(pair))
                        continue
                    price_data = self.data_fetcher.create_data_for_pair(pair, granularity, from_time, to_time)
                currency_data[pair] = price_data
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
        test_results_folder = 'test_results'
        filename = '{}/{}_test_res_{}.{{}}'.format(test_results_folder, self.strategy.value, datetime.now().strftime('%Y%m%d-%H%M%S'))
        if file_type == 'csv':
            results.to_csv(filename.format('csv'))
        else:
            results.to_pickle(filename.format('pkl'))
        print(results)

    def plot_results_for_selected_data(self):
        if not self.plot_data:
            raise ValueError("No data saved for plotting.")

        if self.strategy == Strategy.MA_CROSSOVER:
            for (pair, short_window, long_window), data in self.plot_data.items():
                plot_start = self.data_range_for_plotting.from_time
                plot_end = self.data_range_for_plotting.to_time
                title = "{} Strategy Results for Currency Pair {}, with windows {} and {}, from {} to {}" \
                    .format(self.strategy.value, pair, short_window, long_window, plot_start, plot_end)
                plot_candles_for_ma_crossover(data, plot_start, plot_end, short_window, long_window, title)

        elif self.strategy == Strategy.INSIDE_BAR_MOMENTUM:
            for pair, data in self.plot_data.items():
                plot_start = self.data_range_for_plotting.from_time
                plot_end = self.data_range_for_plotting.to_time
                title = "{} Strategy Results for Currency Pair {}, from {} to {}" \
                    .format(self.strategy.value, pair, plot_start, plot_end)
                plot_candles_for_inside_bar_momentum(data, plot_start, plot_end, title)

    def run(self,
            currencies: List[str],
            granularity: Granularity,
            from_time: datetime,
            to_time: datetime = datetime.now(),
            use_only_downloaded_price_data: bool = False,
            ma_windows=None, file_type: str = Literal['csv', 'pkl']) -> None:
        """
        Run simulations on selected currencies with a given strategy between given dates. Save the results.
        :param currencies: Currency pairs to run the simulation for.
        :param granularity: Historical price granularity to run simulations on.
        :param from_time: Start date for historical data to run simulations from.
        :param to_time: End date for historical data to run simulations to.
        :param use_only_downloaded_price_data: Whether to skip currency pairs where no downloaded price data was found.
         If False, will download price data from the OANDA API where missing.
        :param ma_windows: Only provide if the strategy is MA_CROSSOVER. The moving average windows to run the strategy for.
        The simulation will be run on all logical combinations on these windows.
        :param file_type: The output file type. Can be 'csv' or 'pkl'.
        """
        if self.strategy == Strategy.MA_CROSSOVER and ma_windows is None:
            ma_windows = [4, 8, 16, 32, 64, 96, 128, 256]
        # Retrieve candles for each currency
        historical_price_data_for_currencies: Dict[str, DataFrame] = \
            self.get_price_data_for_all_combinations_of_currencies(currencies, granularity, use_only_downloaded_price_data, from_time, to_time)

        results: List[StrategyResults] = []
        for pair, price_data in historical_price_data_for_currencies.items():
            print("Running simulation for pair", pair)
            pip_location = float(self.instruments.query('name=="{}"'.format(pair))['pipLocation'].iloc[0])
            trade_generator: TradeGenerator = TradeGenerator(pair, pip_location, granularity, price_data, self.strategy)

            if self.strategy == Strategy.MA_CROSSOVER:
                self.run_simulation_for_ma_crossover_strategy(ma_windows, pair, results, trade_generator)

            elif self.strategy == Strategy.INSIDE_BAR_MOMENTUM:
                self.run_simulation_for_inside_bar_momentum_strategy(pair, results, trade_generator)

        results_df = self.create_results_df(results)
        self.save_results(results_df, file_type)

    def run_simulation_for_inside_bar_momentum_strategy(self, pair, results, trade_generator):
        trade_generator.generate_trades(use_pips=True)
        results.append(trade_generator.evaluate_strategy())
        # Save data to be plotted
        if pair in self.data_range_for_plotting.currency_pairs:
            self.plot_data[pair] = trade_generator.historical_data.copy()

    def run_simulation_for_ma_crossover_strategy(self, ma_windows, pair, results, trade_generator):
        for short_window, long_window in itertools.combinations(ma_windows, 2):
            if short_window >= long_window:
                continue
            trade_generator.generate_trades(short_window=short_window, long_window=long_window, use_pips=True)
            results.append(trade_generator.evaluate_strategy())
            # Save data to be plotted
            if pair in self.data_range_for_plotting.currency_pairs and (short_window, long_window) in self.data_range_for_plotting.ma_pairs:
                self.plot_data[(pair, short_window, long_window)] = trade_generator.historical_data.copy()
