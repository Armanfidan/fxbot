from dataclasses import dataclass

from StrategyIteration import StrategyIteration


@dataclass
class MovingAverageCrossoverIteration(StrategyIteration):
    range_prev: float
    mid_h_prev: float
    mid_l_prev: float
    direction_prev: float
    entry_stop: float
    stop_loss: float
    take_profit: float