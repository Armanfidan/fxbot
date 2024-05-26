import itertools
import pandas as pd

import DataFetcher

if __name__ == '__main__':
    instruments: pd.DataFrame = DataFetcher.get_instruments()

    our_curr = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    for curr1, curr2 in itertools.combinations(our_curr, 2):
        pair = '{}_{}'.format(curr1, curr2)
        if pair in instruments['name'].unique():
            DataFetcher.create_data_for_pair(pair, 'H1')
