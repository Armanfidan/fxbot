from dataclasses import dataclass
from typing import override

from model.signal_generator_iterations.SignalGeneratorIteration import SignalGeneratorIteration


@dataclass
class MovingAverageCrossoverIteration(SignalGeneratorIteration):
    short_average: float
    long_average: float

    @override
    def __eq__(self, other):
        return super().__eq__(other)