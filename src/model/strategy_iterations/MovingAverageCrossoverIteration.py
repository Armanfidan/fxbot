from dataclasses import dataclass

from model.strategy_iterations.StrategyIteration import StrategyIteration


@dataclass
class MovingAverageCrossoverIteration(StrategyIteration):
    short_average: float
    long_average: float
