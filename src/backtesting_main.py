from __future__ import annotations

from datetime import datetime
from typing import List

import src.util.Utilities as Utilities
from src.client.OandaDataClient import OandaDataClient
from src.util.PlotProperties import PlotProperties
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator
from src.app.Backtester import Backtester


def simulate_pairs(currencies: List[str]):
    # currencies = ['EUR', 'USD', 'GBP']
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
    simulator = Backtester(use_downloaded_currency_pairs=False, indicator=Indicator.INSIDE_BAR_MOMENTUM, data_range_for_plotting=data_range_for_plotting)
    simulator.run(
        currencies=currencies,
        trade_granularity=Granularity.H4,
        simulation_granularity=Granularity.M5,
        use_only_downloaded_price_data=False,
        from_time=datetime(2020, 1, 1),
        to_time=datetime(2024, 6, 28, 20, 59, 14),
        file_type='csv'
    )
    simulator.plot_results_for_selected_data()


if __name__ == '__main__':
    if not Utilities.instruments_file_exists():
        OandaDataClient(live=False).get_instruments_and_save_to_file()

    simulate_pairs(currencies=['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD'])



