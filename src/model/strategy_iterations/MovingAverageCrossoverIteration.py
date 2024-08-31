from dataclasses import dataclass

from StrategyIteration import StrategyIteration


@dataclass
class MovingAverageCrossoverIteration(StrategyIteration):
    short_average: float
    long_average: float
