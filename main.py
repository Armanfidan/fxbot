import itertools
import pandas as pd

from dataFetcher import DataFetcher
from simulator import Simulator
from utilities import plot_candles, Strategy
from tradeGenerator import TradeGenerator

if __name__ == '__main__':
    data_fetcher = DataFetcher()
    instruments: pd.DataFrame = data_fetcher.get_instruments_and_save_to_file()

    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    simulator = Simulator(strategy=Strategy.MA_CROSSOVER)
    simulator.run(currencies, use_downloaded_data=True)
