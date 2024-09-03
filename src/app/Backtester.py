from __future__ import annotations

from datetime import datetime
import itertools
import sys
from typing import List, Dict, Tuple

import pandas as pd
from pandas import DataFrame

# from math import isnan

from Constants import INSTRUMENTS_FILENAME
from client.DataClient import DataClient
from PlotProperties import PlotProperties
from IndicatorEvaluation import IndicatorEvaluation
# from Trade import Trade
from signal_generators.MovingAverageCrossoverSignalGenerator import MovingAverageCrossoverSignalGenerator
# from signal_generators.SignalGenerator import SignalGenerator
from Utilities import get_downloaded_price_data_for_pair
from Granularity import Granularity
from Indicator import Indicator
from CandlePlotter import CandlePlotter

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


class Backtester:
    def __init__(self, indicator: Indicator = Indicator.MA_CROSSOVER, use_downloaded_currency_pairs: bool = True, data_range_for_plotting: PlotProperties = PlotProperties()):
        self.data_client: DataClient = DataClient(live=False)
        self.instruments: DataFrame = (pd.read_pickle(INSTRUMENTS_FILENAME) if use_downloaded_currency_pairs
                                       else self.data_client.get_instruments_and_save_to_file())
        self.indicator: Indicator = indicator
        self.data_range_for_plotting: PlotProperties = data_range_for_plotting
        self.plot_data: Dict[Tuple[str, int, int] | str, DataFrame] = {}

    def get_price_data_for_pair(self, pair: str, granularity: Granularity, from_time: datetime, to_time: datetime, use_only_downloaded_price_data: bool) -> DataFrame:
        price_data: DataFrame = get_downloaded_price_data_for_pair(pair, granularity, from_time, to_time)
        if price_data.size != 0:
            return price_data
        if use_only_downloaded_price_data:
            raise IOError("No price data found for pair '{}'. Skipping pair - please enable \"use_only_downloaded_data\".".format(pair))
        return self.data_client.create_data_for_pair(pair, granularity, from_time, to_time)

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
                pair = '{}_{}'.format(curr1, curr2)
                if (curr1 == curr2) or pair not in self.instruments['name'].unique():
                    continue
                try:
                    currency_data[pair] = self.get_price_data_for_pair(pair, granularity, from_time, to_time, use_only_downloaded_price_data)
                except IOError as e:
                    print(e)
                    continue
        return currency_data

    @staticmethod
    def create_results_df(results: List[IndicatorEvaluation]) -> DataFrame:
        results_dicts: List[Dict[str, str]] = []
        for result in results:
            result_dict: Dict[str, str] = vars(result) | result.params
            result_dict['indicator'] = result.indicator.value
            result_dict.pop('params')
            result_dict.pop('trades')
            results_dicts.append(result_dict)
        results_df: DataFrame = DataFrame(results_dicts)
        return results_df.set_index('pair')

    def save_results(self, results: DataFrame, file_type: Literal['csv', 'pickle']) -> None:
        test_results_folder = 'test_results'
        filename = '{}/{}_test_res_{}.{{}}'.format(test_results_folder, self.indicator.value, datetime.now().strftime('%Y%m%d-%H%M%S'))
        if file_type == 'csv':
            results.to_csv(filename.format('csv'))
        else:
            results.to_pickle(filename.format('pkl'))
        print(results)

    def plot_results_for_selected_data(self):
        if not self.plot_data:
            raise ValueError("No data saved for plotting.")

        if self.indicator == Indicator.MA_CROSSOVER:
            for (pair, short_window, long_window), data in self.plot_data.items():
                plot_start = self.data_range_for_plotting.from_time
                plot_end = self.data_range_for_plotting.to_time
                title = "{} Indicator performance for Currency Pair {}, with windows {} and {}, from {} to {}" \
                    .format(self.indicator.value, pair, short_window, long_window, plot_start, plot_end)
                CandlePlotter(data, plot_start, plot_end).plot_candles_for_ma_crossover(short_window, long_window, title)

        elif self.indicator == Indicator.INSIDE_BAR_MOMENTUM:
            for pair, data in self.plot_data.items():
                plot_start = self.data_range_for_plotting.from_time
                plot_end = self.data_range_for_plotting.to_time
                title = "{} Indicator performance for Currency Pair {}, from {} to {}" \
                    .format(self.indicator.value, pair, plot_start, plot_end)
                CandlePlotter(data, plot_start, plot_end).plot_candles_for_inside_bar_momentum(title)

    def simulate_ma_crossover(self, ma_windows: List[int], pair: str, pip_location: int, granularity: Granularity, candle_data: DataFrame, results: List[IndicatorEvaluation]):
        for short_window, long_window in itertools.combinations(ma_windows, 2):
            if short_window >= long_window:
                continue
            signal_generator: MovingAverageCrossoverSignalGenerator = MovingAverageCrossoverSignalGenerator(pair, pip_location, granularity, short_window, long_window)
            signal_generator.generate_signals_for_backtesting(candle_data, use_pips=True)
            results.append(signal_generator.evaluate_indicator())
            # Save data to be plotted
            if pair in self.data_range_for_plotting.currency_pairs and (short_window, long_window) in self.data_range_for_plotting.ma_pairs:
                self.plot_data[(pair, short_window, long_window)] = signal_generator.queue.copy()

    # TODO: Implement the signal generator for this indicator and re-enable backtesting
    # def simulate_inside_bar_momentum(self,
    #                                  pair: str,
    #                                  results: List[IndicatorEvaluation],
    #                                  signal_generator: SignalGenerator,
    #                                  simulation_granularity: Granularity,
    #                                  from_time: datetime,
    #                                  to_time: datetime,
    #                                  use_only_downloaded_price_data: bool):
    #     if simulation_granularity not in [Granularity.S5, Granularity.S10, Granularity.S15, Granularity.S30, Granularity.M1, Granularity.M2, Granularity.M3, Granularity.M4, Granularity.M5]:
    #         raise ValueError("The simulation granularity is too coarse for te inside bar momentum simulation. Please choose a granularity finer than M5.")
    #     signal_generator.generate_signals_for_backtesting(use_pips=True)
    #     simulation_data: DataFrame = self.get_price_data_for_pair(pair, simulation_granularity, from_time, to_time, use_only_downloaded_price_data)
    #     simulation_data = self.sort_and_reset(simulation_data)
    #
    #     signal_cols = ['time', 'signal', 'entry_stop', 'stop_loss', 'take_profit']
    #     sim_data_tmp: DataFrame = pd.merge_asof(signal_generator.signals[signal_cols], simulation_data, on='time', tolerance=simulation_granularity.value, direction='nearest')
    #     simulation_data = simulation_data.merge(sim_data_tmp[signal_cols], how='left', on='time')
    #     del sim_data_tmp
    #     simulation_data = self.sort_and_reset(simulation_data[simulation_data[simulation_data['signal'].notna()].index[0]:])  # Remove candles until the first trade, won't make a diff.
    #
    #     non_materialised_trades: List[Dict[str, Any]] = []
    #     closed_trades: List[Dict[str, Any]] = []
    #     current_trade: Trade | None = Trade(simulation_data.iloc[0])
    #     closed_trade_already_saved: bool = False
    #
    #     for index, row in simulation_data.iterrows():
    #         # Our trade is closed and there are no new trades. Keep skipping.
    #         if closed_trade_already_saved and isnan(row['signal']):
    #             continue
    #
    #         current_trade.update(row)
    #
    #         # --- CASE WHEN WE HAVE A NEW TRADE. ---
    #         if not isnan(row['signal']):
    #             if current_trade.is_open():  # Check whether the previous trade is open.
    #                 current_trade.close_trade(row)  # If so, close and append to the non-materialised trades list.
    #                 non_materialised_trades.append(vars(current_trade))
    #             current_trade = Trade(row)  # Create a new trade from the current row.
    #             closed_trade_already_saved = False  # New trade! Not already saved.
    #             continue  # We don't want to update the trade (We just opened it), so skip the rest.
    #
    #         # --- CASE WHEN THE TRADE IS CLOSED ---
    #         if current_trade.exit_time is not None and not closed_trade_already_saved:
    #             closed_trades.append(vars(current_trade))
    #             closed_trade_already_saved = True
    #
    #     closed_trades_df: DataFrame = DataFrame(closed_trades)
    #     closed_trades_df['trade_closed'] = True
    #     non_materialised_trades_df: DataFrame = DataFrame(non_materialised_trades)
    #     non_materialised_trades_df.drop(columns=['signal', 'entry_stop', 'stop_loss', 'take_profit', '_Trade__trade_is_open'], inplace=True)
    #     non_materialised_trades_df['trade_closed'] = False
    #
    #     simulation_data = simulation_data.merge(closed_trades_df[['time', 'entry_time', 'entry_price', 'exit_time', 'exit_price', 'trade_closed']], how='left', on='time')
    #     simulation_data = simulation_data[~simulation_data['time'].isin(list(non_materialised_trades_df['time']))]
    #     simulation_data = self.sort_and_reset(pd.concat([simulation_data, non_materialised_trades_df]))
    #
    #     signal_generator.set_candles_df(simulation_data)
    #     signal_generator.generate_inside_bar_momentum_signal_detail_columns(use_pips=True)
    #     results.append(signal_generator.evaluate_indicator())
    #     # Save data to be plotted
    #     if pair in self.data_range_for_plotting.currency_pairs:
    #         self.plot_data[pair] = signal_generator.queue.copy()

    @staticmethod
    def sort_and_reset(simulation_data):
        """
        Sorts the simulation data DataFrame by time and resets its index.
        :param simulation_data: Simulation data DataFrame to use.
        :return: The sorted and reset DataFrame.
        """
        return simulation_data.sort_values(by='time').reset_index(drop=True)

    # noinspection PyTypeChecker
    def run(self,
            currencies: List[str],
            trade_granularity: Granularity,
            from_time: datetime,
            to_time: datetime = datetime.now(),
            simulation_granularity: Granularity = None,
            use_only_downloaded_price_data: bool = False,
            ma_windows: List[int] | None = None, file_type: str = Literal['csv', 'pkl']) -> None:
        """
        Run simulations on selected currencies with a given indicator between given dates. Save the results.
        :param simulation_granularity: In some cases, the simulation might have to be run at a different granularity than
        when the trades are generated. If not specified, this will be set to the same granularity as the trade granularity.
        :param currencies: Currency pairs to run the simulation for.
        :param trade_granularity: Historical price granularity to run simulations on.
        :param from_time: Start date for historical data to run simulations from.
        :param to_time: End date for historical data to run simulations to.
        :param use_only_downloaded_price_data: Whether to skip currency pairs where no downloaded price data was found.
         If False, will download price data from the OANDA API where missing.
        :param ma_windows: Only provide if the indicator is MA_CROSSOVER. The moving average windows to run the simulation for.
        The simulation will be run on all logical combinations on these windows.
        :param file_type: The output file type. Can be 'csv' or 'pkl'.
        """
        if self.indicator == Indicator.MA_CROSSOVER and not ma_windows:
            ma_windows = [4, 8, 16, 32, 64, 96, 128, 256]
        if not simulation_granularity:
            simulation_granularity = trade_granularity
        # Retrieve candles for each currency
        historical_price_data_for_currencies: Dict[str, DataFrame] = \
            self.get_price_data_for_all_combinations_of_currencies(currencies, trade_granularity, use_only_downloaded_price_data, from_time, to_time)

        results: List[IndicatorEvaluation] = []
        for pair, price_data in historical_price_data_for_currencies.items():
            print("Running simulation for pair", pair)
            pip_location = float(self.instruments.query('name=="{}"'.format(pair))['pipLocation'].iloc[0])

            if self.indicator == Indicator.MA_CROSSOVER:
                self.simulate_ma_crossover(ma_windows, pair, pip_location, trade_granularity, price_data, results)

            # elif self.indicator == Indicator.INSIDE_BAR_MOMENTUM:
            #     self.simulate_inside_bar_momentum(pair, results, simulation_granularity, from_time, to_time, use_only_downloaded_price_data)

        results_df = self.create_results_df(results)
        self.save_results(results_df, file_type)
