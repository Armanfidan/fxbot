from dataclasses import dataclass
from typing import override

from src.model.signal_generator_iterations.SignalGeneratorIteration import SignalGeneratorIteration


@dataclass
class MovingAverageCrossoverIteration(SignalGeneratorIteration):
    short_average: float | None
    long_average: float | None

    @override
    def __eq__(self, other):
        return super().__eq__(other)
