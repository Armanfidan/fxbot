import pandas as pd
import pytest
from src.model.candle.Candle import Candle
from src.model.Granularity import Granularity
from src.service.signal_generators.MovingAverageCrossoverSignalGenerator import MovingAverageCrossoverSignalGenerator


def generator():
    return MovingAverageCrossoverSignalGenerator('EUR_GBP', -4, Granularity.H4, 1, 3)


def replay(values):
    g = generator()
    for time, value in zip(pd.date_range('2024-01-01', periods=len(values), freq='4h'), values):
        g.iterate(Candle(time, mid_c=value))
    return g


def test_warmup_and_long_flat_crossings():
    g = replay([3, 2, 1, 2, 3, 2, 1])
    assert [r.signal for r in g.queue] == [0, 0, 0, 1, 0, -1, 0]
    assert g.queue[0].long_average is None
    assert g.queue[2].long_average == 2
    assert len(g.long_candles_queue) == 3
    assert len(g.short_candles_queue) == 1


def test_first_downward_cross_does_not_open_short():
    assert all(r.signal == 0 for r in replay([1, 2, 3, 2, 1]).queue)


def test_replay_equals_incremental_and_exports_averages():
    g = replay([3, 2, 1, 2, 3, 2, 1])
    frame = pd.DataFrame([vars(r.candle) for r in g.queue])
    batch = generator()
    batch.generate_signals_for_backtesting(frame)
    pd.testing.assert_frame_equal(g.generate_signals_dataframe(), batch.generate_signals_dataframe())
    assert {'MA_1', 'MA_3'} <= set(batch.generate_signals_dataframe())
    with pytest.raises(ValueError):
        batch.generate_signals_for_backtesting(frame)


def test_invalid_windows():
    for short, long in [(0, 3), (3, 3), (4, 3), (1.5, 3)]:
        with pytest.raises(ValueError):
            MovingAverageCrossoverSignalGenerator('EUR_GBP', -4, Granularity.H4, short, long)


@pytest.mark.parametrize(('differences', 'expected'), [
    ([-1, 0, 0, 1], [0, 0, 0, 1]),
    ([-1, 0, -1], [0, 0, 0]),
    ([1, 0, 0, -1], [1, 0, 0, -1]),
    ([1, 0, 1], [1, 0, 0]),
    ([-1, 0, -1, 0, 1], [0, 0, 0, 0, 1]),
    ([1, -1, 0, -1], [1, -1, 0, 0]),
    ([-1, 1, -1], [0, 1, -1]),
])
def test_strict_crossings_plateaus_and_holding_guard(differences, expected):
    # With short=1 and long=3, choose each close to produce the desired
    # short-minus-long difference after a fully warmed, equal baseline.
    prices = [100.0, 100.0, 100.0]
    for difference in differences:
        prices.append((3 * difference + sum(prices[-2:])) / 2)
    signals = [row.signal for row in replay(prices).queue]
    assert signals == [0, 0, 0] + expected
