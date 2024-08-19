from __future__ import annotations

from datetime import datetime
from typing import Dict

from Candle import Candle
from Granularity import Granularity
from Quote import Quote


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

    def __initialise_candle(self, quote: Quote) -> None:
        self.candle_dict: Dict[str, datetime | float] = {
            'time': quote.time,
            'ask_o': quote.ask,
            'ask_h': quote.ask,
            'ask_l': quote.ask,
            'ask_c': None,
            'bid_o': quote.bid,
            'bid_h': quote.bid,
            'bid_l': quote.bid,
            'bid_c': None,
            'mid_o': quote.mid,
            'mid_h': quote.mid,
            'mid_l': quote.mid,
            'mid_c': None,
        }
        self.initial_time = quote.time

    def __update_candle(self, price: Quote) -> None:
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

    def generate(self, price: Quote) -> Candle | None:
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
