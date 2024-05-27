import itertools
import pandas as pd

from dataFetcher import DataFetcher
from utilities import plot_candles
from tradeGenerator import TradeGenerator

if __name__ == '__main__':
    data_fetcher = DataFetcher()
    instruments: pd.DataFrame = data_fetcher.get_instruments_and_save_to_file()

    our_curr = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    for curr1, curr2 in itertools.combinations(our_curr, 2):
        pair = '{}_{}'.format(curr1, curr2)
        if pair in instruments['name'].unique():
            historical_data: pd.DataFrame = data_fetcher.create_data_for_pair(pair, 'H1')
            plot_candles(pair, 'H1')
            trade_generator = TradeGenerator(pair)
            trade_generator.generate_ma_crossover_trades()
            pass
