import math
from dataclasses import dataclass
from typing import override

from src.model.candle.Candle import Candle


@dataclass
class SignalGeneratorIteration:
    candle: Candle
    signal: -1 | 0 | 1

    @override
    def __eq__(self, other):
        if not isinstance(other, SignalGeneratorIteration):
            return False
        for key, value in vars(self).items():
            other_value = vars(other)[key]
            if isinstance(value, float) and not math.isclose(value, other_value):
                return False
            elif value != other_value:
                return False
        return True
