import math
from dataclasses import dataclass
from typing import override

from candle.Candle import Candle


@dataclass
class StrategyIteration:
    candle: Candle
    signal: -1 | 0 | 1

    @override
    def __eq__(self, other):
        if not isinstance(other, StrategyIteration):
            return False
        for key, value in vars(self).items():
            other_value = vars(other)[key]
            if isinstance(value, float) and not math.isclose(value, other_value):
                return False
            elif value != other_value:
                return False
        return True
