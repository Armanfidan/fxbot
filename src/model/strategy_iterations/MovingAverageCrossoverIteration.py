from dataclasses import dataclass
from typing import override

from model.strategy_iterations.StrategyIteration import StrategyIteration


@dataclass
class MovingAverageCrossoverIteration(StrategyIteration):
    short_average: float
    long_average: float

    @override
    def __eq__(self, other):
        return super().__eq__(other)