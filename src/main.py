from datetime import datetime

from PlotProperties import PlotProperties
from Simulator import Simulator
from Granularity import Granularity
from Strategy import Strategy
from PriceType import PriceType
from client.OrderClient import OrderClient


def simulate_pairs():
    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']
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
    simulator = Simulator(use_downloaded_currency_pairs=False, strategy=Strategy.INSIDE_BAR_MOMENTUM, price_type=PriceType.ASK, data_range_for_plotting=data_range_for_plotting)
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
    # simulate_pairs()
    trader = OrderClient()
    trader.place_market_order('EUR_USD', 100000, 'FOK', 1)
