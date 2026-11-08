from dataclasses import replace

import pandas as pd
import pytest

from src.app.Backtester import Backtester
from src.app.InsideBarBacktester import InsideBarBacktester
from src.app.MovingAverageCrossoverBacktester import MovingAverageCrossoverBacktester
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator
from test.test_backtest import frame


def test_base_requires_a_concrete_strategy():
    with pytest.raises(NotImplementedError, match='concrete strategy'):
        Backtester()


@pytest.mark.parametrize('backtester_class, indicator, other', [
    (MovingAverageCrossoverBacktester, Indicator.MA_CROSSOVER, Indicator.INSIDE_BAR_MOMENTUM),
    (InsideBarBacktester, Indicator.INSIDE_BAR_MOMENTUM, Indicator.MA_CROSSOVER),
])
def test_strategy_is_fixed_and_mismatched_configs_are_rejected(backtester_class, indicator, other):
    engine = backtester_class()
    assert engine.config.indicator == engine.indicator == indicator
    original = engine.config
    mismatch = replace(original, indicator=other)
    with pytest.raises(ValueError, match='requires'):
        backtester_class(config=mismatch)
    with pytest.raises(ValueError, match='requires'):
        engine.run_data('EUR_GBP', frame([1, 1]), config=mismatch)
    assert engine.config is original


@pytest.mark.parametrize('backtester_class, expected_windows', [
    (MovingAverageCrossoverBacktester, [(1, 2), (1, 3), (2, 3)]),
    (InsideBarBacktester, [(16, 64)]),
])
def test_batch_runs_use_strategy_experiments_and_export(backtester_class, expected_windows, monkeypatch, tmp_path):
    engine = backtester_class()
    engine.instruments = pd.DataFrame({'name': ['GBP_USD'], 'pipLocation': [-4]})
    candles = frame([3, 2, 1, 2, 3, 2, 1])
    from test.test_backtest import conversion
    monkeypatch.setattr(engine, 'get_price_data_for_pair', lambda *args: candles)
    results = engine.run(
        ['GBP', 'USD'], from_time=candles.time.iloc[0],
        to_time=candles.time.iloc[-1] + Granularity.H4.value,
        simulation_granularity=Granularity.H4, ma_windows=[3, 1, 2, 2],
        conversion_data=conversion(), output_directory=tmp_path,
    )
    assert [(r.configuration.short_window, r.configuration.long_window) for r in results] == expected_windows
    assert all(r.configuration.indicator == engine.indicator for r in results)
    assert all(r.equity.iloc[0].balance == 10000 for r in results)
    assert len(list(tmp_path.glob('*/summary.json'))) == len(expected_windows)
    expected_execution = Granularity.M5 if backtester_class is InsideBarBacktester else Granularity.H4
    assert engine._default_execution_granularity(Granularity.H4) == expected_execution
