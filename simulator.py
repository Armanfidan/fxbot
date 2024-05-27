import itertools
from typing import List, Dict

import pandas as pd

from dataFetcher import DataFetcher
from strategyResults import StrategyResults
from tradeGenerator import TradeGenerator
from utilities import Strategy, get_price_data


class Simulator:
    def __init__(self,  strategy: Strategy = Strategy.MA_CROSSOVER):
        self.data_fetcher: DataFetcher = DataFetcher()
        self.instruments: pd.DataFrame = self.data_fetcher.get_instruments_and_save_to_file()
        self.strategy: Strategy = strategy

    def get_trade_data_for_all_combinations_of_currencies(self, currencies: List[str], granularity: str, use_downloaded_data: bool) -> Dict[str, pd.DataFrame]:
        currency_data: Dict[str, pd.DataFrame] = {}
        for curr1, curr2 in itertools.combinations(currencies, 2):
            pair = '{}_{}'.format(curr1, curr2)
            if pair in self.instruments['name'].unique():
                currency_data[pair] = (get_price_data(pair, granularity) if use_downloaded_data else
                                       self.data_fetcher.create_data_for_pair(pair, granularity))
        return currency_data

    @staticmethod
    def create_results_df(results: List[StrategyResults]) -> pd.DataFrame:
        results_dicts: List[Dict[str, str]] = []
        for result in results:
            result_dict: Dict[str, str] = vars(result) | result.params
            result_dict['strategy'] = result.strategy.value
            result_dict.pop('params')
            result_dict.pop('historical_data')
            results_dicts.append(result_dict)
        results_df: pd.DataFrame = pd.DataFrame(results_dicts)
        return results_df.set_index('pair')

    def save_results(self, results: pd.DataFrame):
        results.to_pickle('{}_test_res.pkl'.format(self.strategy.value))
        print(results.shape, results)

    def run(self, currencies: List[str], use_downloaded_data: bool = True, granularity: str = 'H1', ma_windows=None):
        if ma_windows is None:
            ma_windows = [8, 16, 32, 64, 96, 128, 256]
        currency_data = self.get_trade_data_for_all_combinations_of_currencies(currencies, granularity, use_downloaded_data)
        results: List[StrategyResults] = []
        for pair, price_data in currency_data.items():
            print("Running simulation for pair", pair)
            trade_generator: TradeGenerator = TradeGenerator(pair, self.strategy, price_data)
            for short_window, long_window in itertools.combinations(ma_windows, 2):
                if short_window >= long_window:
                    continue
                trade_generator.generate_trades(short_window=short_window, long_window=long_window)
                results.append(trade_generator.evaluate_strategy())
        results_df = self.create_results_df(results)
        self.save_results(results_df)
