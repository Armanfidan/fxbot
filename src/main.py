from datetime import datetime, timedelta
from typing import Dict

from LiveDataStore import LiveDataStore
from LiveTrader import LiveTrader
from PlotProperties import PlotProperties
from PriceColumns import PriceColumns
from Backtester import Simulator
from Granularity import Granularity
from Strategy import Strategy
from PriceType import PriceType

from multiprocessing import Process


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


def start_live_data_store(_pair: str, _candlestick_granularity: Granularity, _price_granularity: Granularity):
    live_data_store = LiveDataStore(_pair, _candlestick_granularity, _price_granularity)
    live_data_store.start()


def start_live_trader(_pair: str, _strategy: Strategy, _granularity: Granularity, _live: bool, _historical_data_start_time: datetime, _order_units: int, _strategy_params: Dict | None):
    live_trader = LiveTrader(_pair, _strategy, _granularity, _live, _historical_data_start_time, _order_units, _strategy_params)
    live_trader.start()


if __name__ == '__main__':
    pair: str = "EUR_USD"
    candlestick_granularity: Granularity = Granularity.S30
    price_granularity: Granularity = Granularity.S5
    strategy: Strategy = Strategy.MA_CROSSOVER
    strategy_params: Dict | None = {'short_window': 16, 'long_window': 64}
    live: bool = False
    order_units: int = 100000
    historical_data_start_time: datetime = datetime.now() - timedelta(days=1)
    live_data_store_process: Process = Process(target=start_live_data_store, args=(pair, candlestick_granularity, price_granularity))
    live_trader_process: Process = Process(target=start_live_trader, args=(pair, strategy, candlestick_granularity, live, historical_data_start_time, order_units, strategy_params))
    live_data_store_process.start()
    live_trader_process.start()
    live_data_store_process.join()
    live_trader_process.join()
