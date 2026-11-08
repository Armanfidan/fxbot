"""Common incremental strategy interface for replay and live use."""
from src.model.candle.Candle import Candle


class SignalGenerator:
    def __init__(self, pair, pip_location, granularity, initial_candles=None):
        self.pair = pair
        self.pip_location = pip_location
        self.granularity = granularity
        self.queue = []

    def iterate_from_dataframe(self, candles):
        for row in candles.to_dict('records'):
            self.iterate(Candle.from_dict(row))

    def iterate(self, candle):
        raise NotImplementedError

    def generate_signals_for_backtesting(self, candles, use_pips=True):
        # Retain use_pips for callers; execution converts slippage using pip_location.
        if self.queue:
            raise ValueError('Backtesting requires a fresh generator')
        self.iterate_from_dataframe(candles)

    def generate_signals_dataframe(self):
        raise NotImplementedError

    def evaluate_indicator(self, equity, trades=None, annual_risk_free_rate=0.0):
        from src.service.IndicatorEvaluator import IndicatorEvaluator
        return IndicatorEvaluator(self.pair, equity, trades, annual_risk_free_rate)
