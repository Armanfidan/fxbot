from enum import Enum

from Utilities import get_candle_column
from candle.CandlePrice import CandlePrice
from candle.CandleType import CandleType


class Price(Enum):
    MID_OPEN: str = get_candle_column(CandleType.MID, CandlePrice.OPEN)
    MID_HIGH: str = get_candle_column(CandleType.MID, CandlePrice.HIGH)
    MID_LOW: str = get_candle_column(CandleType.MID, CandlePrice.LOW)
    MID_CLOSE: str = get_candle_column(CandleType.MID, CandlePrice.CLOSE)

    BID_OPEN: str = get_candle_column(CandleType.BID, CandlePrice.OPEN)
    BID_HIGH: str = get_candle_column(CandleType.BID, CandlePrice.HIGH)
    BID_LOW: str = get_candle_column(CandleType.BID, CandlePrice.LOW)
    BID_CLOSE: str = get_candle_column(CandleType.BID, CandlePrice.CLOSE)

    ASK_OPEN: str = get_candle_column(CandleType.ASK, CandlePrice.OPEN)
    ASK_HIGH: str = get_candle_column(CandleType.ASK, CandlePrice.HIGH)
    ASK_LOW: str = get_candle_column(CandleType.ASK, CandlePrice.LOW)
    ASK_CLOSE: str = get_candle_column(CandleType.ASK, CandlePrice.CLOSE)


CANDLES_DF_COLUMNS = ['time', 'volume'] + [price.value for price in Price]
