from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Set


@dataclass
class Candle:
    time: datetime
    volume: float = None
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
        candle_keys: Set[str] = set(vars(Candle(datetime.now())).keys())
        # if candle_dict.keys() != vars(Candle(datetime.now())).keys():
        #     raise ValueError("Invalid candle data: {}".format(candle_dict))
        return Candle(**{key: value for key, value in candle_dict.items() if key in candle_keys})

    def __str__(self):
        non_null_vars = {key: value for key, value in vars(self).items() if value is not None}
        non_null_vars['time'] = self.time.timestamp()
        return json.dumps(non_null_vars)

    def __eq__(self, other):
        return all(x == y for x, y in zip(vars(self).values(), vars(other).values()))

    def serialise(self):
        return self.__str__()

    @staticmethod
    def deserialise(candle_json: str):
        candle_dict: Dict = json.loads(candle_json)
        candle_dict['time'] = datetime.fromtimestamp(candle_dict['time'])
        return Candle(**candle_dict)
