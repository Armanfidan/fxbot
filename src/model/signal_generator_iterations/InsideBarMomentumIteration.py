from dataclasses import dataclass

from src.model.signal_generator_iterations.SignalGeneratorIteration import SignalGeneratorIteration


@dataclass
class InsideBarMomentumIteration(SignalGeneratorIteration):
    range_prev: float
    mid_h_prev: float
    mid_l_prev: float
    direction_prev: float
    entry_stop: float
    stop_loss: float
    take_profit: float
