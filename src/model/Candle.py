from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from v20.pricing_common import Price


@dataclass
class Candle:
    time: datetime
    ask_o: float = None
    ask_h: float = None
    ask_l: float = None
    ask_c: float = None
    bid_o: float = None
    bid_h: float = None
    bid_l: float = None
    bid_c: float = None
    mid_o: float = None
    mid_h: float = None
    mid_l: float = None
    mid_c: float = None

    @staticmethod
    def from_dict(candle_dict: Dict[str, datetime | float]):
        return Candle(**candle_dict)  # TODO: Check all fields, make sure no extra
