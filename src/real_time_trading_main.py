from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

import src.util.Utilities as Utilities
from src.client.DataClient import DataClient
from src.service.LiveDataStore import LiveDataStore
from src.app.RealTimeTrader import LiveTrader
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator

from multiprocessing import Process


def start_live_data_store(_pair: str, _candlestick_granularity: Granularity, _price_granularity: Granularity):
    live_data_store = LiveDataStore(_pair, _candlestick_granularity, _price_granularity)
    live_data_store.start()


def start_live_trader(_pair: str, _indicator: Indicator, _granularity: Granularity, _live: bool, _historical_data_start_time: datetime, _order_units: int, _indicator_params: Dict | None):
    live_trader = LiveTrader(_pair, _indicator, _granularity, _live, _historical_data_start_time, _order_units, _indicator_params)
    live_trader.start()


if __name__ == '__main__':
    if not Utilities.instruments_file_exists():
        DataClient(live=False).get_instruments_and_save_to_file()

    pair: str = "EUR_USD"
    candlestick_granularity: Granularity = Granularity.S30
    price_granularity: Granularity = Granularity.S5
    indicator: Indicator = Indicator.MA_CROSSOVER
    indicator_params: Dict | None = {'short_window': 16, 'long_window': 64}
    live: bool = False
    order_units: int = 100000
    historical_data_start_time: datetime = datetime.now() - timedelta(days=1)
    live_data_store_process: Process = Process(target=start_live_data_store, args=(pair, candlestick_granularity, price_granularity))
    live_trader_process: Process = Process(target=start_live_trader, args=(pair, indicator, candlestick_granularity, live, historical_data_start_time, order_units, indicator_params))
    live_data_store_process.start()
    live_trader_process.start()
    live_data_store_process.join()
    live_trader_process.join()
