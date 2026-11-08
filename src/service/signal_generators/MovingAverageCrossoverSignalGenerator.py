import pandas as pd

from collections import deque
import math
from src.service.signal_generators.SignalGenerator import SignalGenerator
from src.model.signal_generator_iterations.MovingAverageCrossoverIteration import MovingAverageCrossoverIteration


class MovingAverageCrossoverSignalGenerator(SignalGenerator):
    """O(1) full-window midpoint SMA updates; long/flat crossover signals."""
    def __init__(self, pair, pip_location, granularity, short_window, long_window, initial_candles=None):
        super().__init__(pair, pip_location, granularity, initial_candles)
        if any(not isinstance(w, int) or isinstance(w, bool) for w in (short_window, long_window)) or not 0 < short_window < long_window:
            raise ValueError('Require integer windows: 0 < short < long')
        self.short_window, self.long_window = short_window, long_window
        self.short_candles_queue = deque(maxlen=short_window)
        self.long_candles_queue = deque(maxlen=long_window)
        self.current_short_average = self.current_long_average = 0.0
        self._short_sum = self._long_sum = 0.0
        self._previous_difference = None
        self._holding = False
        if initial_candles is not None:
            self.iterate_from_dataframe(initial_candles)

    def _iterate_queue(self, candle, window_type):
        queue = getattr(self, window_type + '_candles_queue')
        total = getattr(self, '_' + window_type + '_sum')
        if len(queue) == queue.maxlen:
            total -= queue.popleft().mid_c
        queue.append(candle)
        total += candle.mid_c
        setattr(self, '_' + window_type + '_sum', total)
        setattr(self, 'current_' + window_type + '_average', total / len(queue))

    def generate_signal(self):
        if len(self.long_candles_queue) < self.long_window:
            return 0
        difference = self.current_short_average - self.current_long_average
        # Stabilise equal averages against floating point summation noise.
        if math.isclose(difference, 0.0, abs_tol=1e-12):
            difference = 0.0
        previous = self._previous_difference
        self._previous_difference = difference
        if previous is None:
            return 0
        if previous <= 0 < difference and not self._holding:
            self._holding = True
            return 1
        if previous >= 0 > difference and self._holding:
            self._holding = False
            return -1
        return 0

    def iterate(self, candle):
        if candle.mid_c is None or not math.isfinite(candle.mid_c) or candle.mid_c <= 0:
            raise ValueError('Require a positive finite midpoint close')
        self._iterate_queue(candle, 'short')
        self._iterate_queue(candle, 'long')
        signal = self.generate_signal()
        self.queue.append(MovingAverageCrossoverIteration(candle, signal,
            self.current_short_average if len(self.short_candles_queue) == self.short_window else None,
            self.current_long_average if len(self.long_candles_queue) == self.long_window else None))

    def generate_signals_dataframe(self):
        if not self.queue:
            raise ValueError('Iterate the generator before retrieving signals')
        rows = []
        for iteration in self.queue:
            detail = {k: v for k, v in vars(iteration).items() if k != 'candle'}
            detail[f'MA_{self.short_window}'] = iteration.short_average
            detail[f'MA_{self.long_window}'] = iteration.long_average
            rows.append(vars(iteration.candle) | detail)
        return pd.DataFrame(rows)
