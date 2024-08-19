from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict


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

    def __str__(self):
        non_null_vars = {key: value for key, value in vars(self).items() if value is not None}
        non_null_vars['time'] = self.time.timestamp()
        return json.dumps(non_null_vars)

    def serialise(self):
        return self.__str__()

    @staticmethod
    def deserialise(candle_json: str):
        candle_dict: Dict = json.loads(candle_json)
        candle_dict['time'] = datetime.fromtimestamp(candle_dict['time'])
        return Candle(**candle_dict)
