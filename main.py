import itertools
import pandas as pd

import constants
from dataFetcher import DataFetcher
from utilities import plot_candles

if __name__ == '__main__':
    data_fetcher = DataFetcher()
    instruments: pd.DataFrame = data_fetcher.get_instruments_and_save_to_file()

    our_curr = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    for curr1, curr2 in itertools.combinations(our_curr, 2):
        pair = '{}_{}'.format(curr1, curr2)
        if pair in instruments['name'].unique():
            data_fetcher.create_data_for_pair(pair, 'H1')
            plot_candles(pair, 'H1')
            break
