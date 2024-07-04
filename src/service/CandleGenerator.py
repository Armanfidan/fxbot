from datetime import datetime
from typing import Dict

from Candle import Candle
from Granularity import Granularity
from Price import Price
from PriceColumns import PriceColumns
from PriceType import PriceType


class CandleGenerator:
    def __init__(self, pair: str, candlestick_granularity: Granularity):
        """
        Accumulates live prices for a given pair and yields a candle of required granularity when the correct number of prices is received.
        :param pair: Currency pair to generate candles for.
        :param candlestick_granularity: Candle granularity required.
        """
        self.pair: str = pair
        self.candlestick_granularity: Granularity = candlestick_granularity
        self.initial_time: datetime | None = None
        self.candle_dict: Dict[str, datetime | float] | None = None

    def __initialise_candle(self, price: Price) -> None:
        self.candle_dict: Dict[str, datetime | float] = {
            'time': price.time,
            'ask_o': price.ask,
            'ask_h': price.ask,
            'ask_l': price.ask,
            'ask_c': None,
            'bid_o': price.bid,
            'bid_h': price.bid,
            'bid_l': price.bid,
            'bid_c': None,
            'mid_o': price.mid,
            'mid_h': price.mid,
            'mid_l': price.mid,
            'mid_c': None,
        }
        self.initial_time = price.time

    def __update_candle(self, price: Price) -> None:
        self.candle_dict['time'] = price.time
        # Setting ask h and l
        if price.ask > self.candle_dict['ask_h']:
            self.candle_dict['ask_h'] = price.ask
        elif price.ask < self.candle_dict['ask_l']:
            self.candle_dict['ask_l'] = price.ask
        # Setting bid h and l
        if price.bid > self.candle_dict['bid_h']:
            self.candle_dict['bid_h'] = price.bid
        elif price.bid < self.candle_dict['bid_l']:
            self.candle_dict['bid_l'] = price.bid
        # Setting mid h and l
        if price.mid > self.candle_dict['mid_h']:
            self.candle_dict['mid_h'] = price.mid
        elif price.mid < self.candle_dict['mid_l']:
            self.candle_dict['mid_l'] = price.mid

    def generate(self, price: Price) -> Candle | None:
        """
        Takes in a price and updates the candle.
        If the required candlestick granularity has been reached, yields a candle.
        :param price: Price - expected in the format: {'time': datetime, 'mid': float, 'ask': float, 'bid': float}
        :return: Yield a candle if ready.
        """
        if self.candle_dict:
            self.__update_candle(price)
        else:
            self.__initialise_candle(price)
        if (price.time - self.initial_time) >= self.candlestick_granularity.value:
            self.candle_dict['ask_c'] = price.ask
            self.candle_dict['bid_c'] = price.bid
            self.candle_dict['mid_c'] = price.mid
            candle_dict: dict = self.candle_dict
            self.candle_dict = None
            return Candle.from_dict(candle_dict)
        return None
