from datetime import datetime
from time import sleep
from typing import Dict

from Candle import Candle
from CandleGenerator import CandleGenerator
from Granularity import Granularity
from Price import Price
from PriceColumns import PriceColumns
from client.DataClient import DataFetcher


class LiveDataStore:
    def __init__(self, pair: str, candlestick_granularity: Granularity, price_granularity: Granularity, pc: PriceColumns):
        self.pair: str = pair
        self.candlestick_granularity: Granularity = candlestick_granularity
        self.price_granularity: Granularity = price_granularity
        self.pc: PriceColumns = pc

        self.data_fetcher: DataFetcher = DataFetcher()
        self.candle_generator: CandleGenerator = CandleGenerator(pair, candlestick_granularity, price_granularity, pc)

    def publish_candles(self):
        while True:
            sleep(self.price_granularity.value.total_seconds())
            price: Price = Price.from_dict(self.data_fetcher.get_price(self.pair))
            candle: Candle = self.candle_generator.generate(price)
            if candle:
                self.publish_candle(candle)

    def publish_candle(self, candle: Candle):
        # IMPLEMENT A MESSAGE QUEUE
        pass
