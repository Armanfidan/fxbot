import math
import numpy as np
import pandas as pd
import pytest
from src.service.IndicatorEvaluator import IndicatorEvaluator


def evaluator(values, days=None, trades=None, rf=0):
    times = pd.to_datetime(days, utc=True) if days else pd.date_range('2024-01-01', periods=len(values), tz='UTC')
    return IndicatorEvaluator('EUR_GBP', pd.DataFrame({'time': times, 'equity': values}), trades, rf)


def test_returns_drawdowns_and_profit_ratio():
    metrics = evaluator([10000, 11000, 9900, 10890]).metrics()
    assert metrics['total_return'] == pytest.approx(.089)
    assert metrics['max_drawdown'] == pytest.approx(.1)
    assert metrics['max_drawdown_amount'] == 1100
    assert metrics['profit_to_drawdown'] == pytest.approx(890 / 1100)


def test_daily_returns_sharpe_sortino_and_risk_free():
    e = evaluator([100, 110, 99, 108.9], rf=.05)
    returns = np.array([.1, -.1, .1])
    excess = returns - ((1.05 ** (1 / 252)) - 1)
    assert e.daily_returns.to_numpy() == pytest.approx(returns)
    assert e.calculate_annualised_sharpe_ratio() == pytest.approx(np.sqrt(252) * excess.mean() / excess.std(ddof=1))
    assert e.calculate_annualised_sortino_ratio() == pytest.approx(np.sqrt(252) * excess.mean() / np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))


def test_daily_aggregation_keeps_first_day_cost_and_sunday():
    e = evaluator([100, 99, 101, 102], ['2024-01-05T10:00Z', '2024-01-05T11:00Z', '2024-01-05T12:00Z', '2024-01-07T22:00Z'])
    assert e.daily_returns.to_numpy() == pytest.approx([.01, 102/101-1])


def test_initial_loss_is_drawdown():
    assert evaluator([100, 90, 95]).calculate_max_drawdown() == pytest.approx(.1)


def test_cagr_and_calmar():
    e = evaluator([100, 90, 110], ['2023-01-01', '2023-06-01', '2024-01-01'])
    cagr = 1.1 ** (365.25 / 365) - 1
    assert e.calculate_cagr() == pytest.approx(cagr)
    assert e.calculate_calmar_ratio() == pytest.approx(cagr / .1)


@pytest.mark.parametrize('values', [[100, 100, 100], [100, 110, 121]])
def test_undefined_ratios(values):
    e = evaluator(values)
    assert e.calculate_calmar_ratio() is None
    assert e.calculate_profit_to_drawdown_ratio() is None
    assert e.calculate_sortino_ratio() is None
    if values[1] == 100:
        assert e.calculate_sharpe_ratio() is None


def test_insufficient_samples_and_zero_equity():
    assert evaluator([100, 101]).calculate_sharpe_ratio() is None
    assert evaluator([100, 0]).calculate_cagr() is None
    assert evaluator([100, 0, 0]).calculate_sharpe_ratio() is None


def test_trade_statistics_use_net_profit_and_actual_duration():
    trades = pd.DataFrame({'signal': [1, -1], 'entry_time': ['2024-01-01T01:00Z', '2024-01-02T01:00Z'],
                           'exit_time': ['2024-01-01T03:00Z', '2024-01-02T02:00Z'], 'net_pnl': [5, -1]})
    e = evaluator([100, 104, 104], trades=trades)
    assert e.calculate_total_time_in_market() == pd.Timedelta(hours=3)
    assert e.calculate_secondary_metrics() == {'trade_count': 2, 'long_count': 1, 'short_count': 1, 'win_rate': .5}


def test_invalid_history():
    with pytest.raises(ValueError):
        evaluator([0, 1])
    with pytest.raises(ValueError):
        evaluator([100, math.inf])
