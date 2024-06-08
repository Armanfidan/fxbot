from datetime import datetime

from dataFetcher import DataFetcher
from simulator import Simulator
from utilities import Strategy

if __name__ == '__main__':
    data_fetcher = DataFetcher()

    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    simulator = Simulator(strategy=Strategy.MA_CROSSOVER)
    simulator.run(currencies, use_downloaded_data=False, from_time=datetime(2016, 1, 1), file_type='csv')
