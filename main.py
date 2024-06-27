from datetime import datetime

from dataFetcher import DataFetcher
from plotProperties import PlotProperties
from simulator import Simulator
from utilities import Strategy, Granularity

if __name__ == '__main__':
    data_fetcher = DataFetcher()

    # currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
    currencies = ['EUR', 'USD', 'GBP']
    # currencies = ['EUR', 'USD', 'GBP']
    # data_range_for_plotting = PlotProperties(
    #     currencies,
    #     [(32, 64), (32, 128), (64, 128)],
    #     datetime(2023, 1, 1),
    #     datetime.now()
    # )
    data_range_for_plotting = PlotProperties(
        currencies=currencies,
        from_time=datetime(2024, 4, 1),
        to_time=datetime.now()
    )
    simulator = Simulator(use_downloaded_currency_pairs=True, strategy=Strategy.INSIDE_BAR_MOMENTUM, data_range_for_plotting=data_range_for_plotting)
    simulator.run(
        currencies=currencies,
        granularity=Granularity.H4,
        use_only_downloaded_price_data=False,
        from_time=datetime(2016, 1, 1),
        to_time=datetime(2024, 6, 8, 12, 49, 14),
        file_type='csv'
    )
    simulator.plot_results_for_selected_data()
