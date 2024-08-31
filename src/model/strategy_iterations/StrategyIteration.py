from dataclasses import dataclass

from candle.Candle import Candle


@dataclass
class StrategyIteration:
    candle: Candle
    signal: -1 | 0 | 1
