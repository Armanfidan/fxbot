from datetime import datetime
from typing import Dict

from Candle import Candle
from Granularity import Granularity
from Price import Price
from PriceColumns import PriceColumns
from PriceType import PriceType


class CandleGenerator:
    def __init__(self, pair: str, candlestick_granularity: Granularity, price_granularity: Granularity, pc: PriceColumns):
        """
        Accumulates live prices for a given pair and yields a candle of required granularity when the correct number of prices is received.
        :param pair: Currency pair to generate candles for.
        :param candlestick_granularity: Candle granularity required.
        :param price_granularity: Granularity of the received prices.
        """
        self.pair: str = pair
        self.candlestick_granularity: Granularity = candlestick_granularity
        self.num_prices_required: int = candlestick_granularity.value / price_granularity.value
        self.num_prices_accumulated: int = 0
        self.pc = pc
        self.candle_dict: Dict[str, datetime | float] | None = None

    def __initialise_candle(self, price: Price) -> None:
        price_value: float = price.ask if self.pc.type == PriceType.ASK else (price.bid if self.pc.type == PriceType.BID else price.mid)
        self.candle_dict: Dict[str, datetime | float] = {
            'time': price.time,
            self.pc.o: price_value,
            self.pc.h: price_value,
            self.pc.l: price_value,
            self.pc.c: None
        }
        self.num_prices_accumulated = 1

    def __update_candle(self, price: Price) -> None:
        price_value: float = price.ask if self.pc.type == PriceType.ASK else (price.bid if self.pc.type == PriceType.BID else price.mid)
        self.candle_dict['time'] = price.time
        if price_value > self.candle_dict[self.pc.h]:
            self.candle_dict[self.pc.h] = price_value
        elif price_value < self.candle_dict[self.pc.l]:
            self.candle_dict[self.pc.l] = price_value
        self.num_prices_accumulated += 1

    def generate(self, price: Price) -> Candle | None:
        """
        Takes in a price and updates the candle.
        If the required candlestick granularity has been reached, yields a candle.
        :param price: Price - expected in the format: {'time': datetime, 'mid': float, 'ask': float, 'bid': float}
        :return: Yield a candle if ready.
        """
        price_value: float = price.ask if self.pc.type == PriceType.ASK else (price.bid if self.pc.type == PriceType.BID else price.mid)
        if self.candle_dict:
            self.__update_candle(price)
        else:
            self.__initialise_candle(price)
        if self.num_prices_accumulated >= self.num_prices_required:
            self.candle_dict[self.pc.c] = price_value
            candle_dict: dict = self.candle_dict
            self.candle_dict = None
            return Candle.from_dict(candle_dict)
        return None
