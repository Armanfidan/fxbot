from dataclasses import dataclass

from src.model.signal_generator_iterations.SignalGeneratorIteration import SignalGeneratorIteration


@dataclass
class InsideBarMomentumIteration(SignalGeneratorIteration):
    range_prev: float | None
    mid_h_prev: float | None
    mid_l_prev: float | None
    direction_prev: float | None
    entry_stop: float | None
    stop_loss: float | None
    take_profit: float | None
