import pandas as pd

from src.service.signal_generators.SignalGenerator import SignalGenerator
from src.model.signal_generator_iterations.InsideBarMomentumIteration import InsideBarMomentumIteration
from src.model.Granularity import Granularity


class InsideBarMomentumSignalGenerator(SignalGenerator):
    """Inside-bar breakout setup using the preceding candle's direction/range."""
    def __init__(self, pair, pip_location, granularity, initial_candles=None):
        super().__init__(pair, pip_location, granularity, initial_candles)
        if granularity.value < Granularity.H4.value or granularity == Granularity.M:
            raise ValueError('Inside bar requires fixed H4 or coarser candles')
        self.previous = None
        if initial_candles is not None:
            self.iterate_from_dataframe(initial_candles)

    def iterate(self, candle):
        previous = self.previous
        signal = 0
        span = high = low = direction = entry = stop = target = None
        if previous is not None:
            high, low = previous.mid_h, previous.mid_l
            span = high - low
            direction = 1 if previous.mid_c > previous.mid_o else -1
            if span > 0 and candle.mid_h < high and candle.mid_l > low:
                signal = direction
                reference = high if signal == 1 else low
                entry = reference + signal * span * .1
                stop = reference - signal * span * .4
                target = reference + signal * span * .8
        self.queue.append(InsideBarMomentumIteration(candle, signal, span, high, low, direction, entry, stop, target))
        self.previous = candle

    def generate_signals_dataframe(self):
        if not self.queue:
            raise ValueError('Iterate the generator before retrieving signals')
        rows = []
        for iteration in self.queue:
            detail = {k: v for k, v in vars(iteration).items() if k != 'candle'}
            rows.append(vars(iteration.candle) | detail)
        return pd.DataFrame(rows)
