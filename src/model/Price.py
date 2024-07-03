from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from v20.pricing_common import Price


@dataclass
class Price:
    time: datetime
    ask: float
    bid: float
    mid: float

    @staticmethod
    def from_dict(price_dict: Dict[str, datetime | float]) -> Price:
        return Price(**price_dict)  # TODO: Check all fields, make sure no extra
