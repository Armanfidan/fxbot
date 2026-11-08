"""Accounting operations can be exercised independently of a historical replay."""
from copy import deepcopy
from dataclasses import replace

import pandas as pd
import pytest

from src.app.Backtester import Conversions
from src.app.MovingAverageCrossoverBacktester import MovingAverageCrossoverBacktester
from src.app.InsideBarBacktester import InsideBarBacktester
from src.model.Backtest import BacktestConfig, ConversionData, CostConfig
from src.model.BacktestState import BacktestState
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator
from src.model.PathOutcome import PathOutcome
from test.test_backtest import frame


@pytest.fixture
def accounting():
    time = pd.Timestamp('2024-01-01T08:00Z')
    config = BacktestConfig(
        costs=CostConfig(0, 1, {'GBP_USD': {'long': -.0001, 'short': .0001}}),
    )
    state = BacktestState(pair='GBP_USD', balance=10000, last_rollover=time)
    conversions = Conversions('GBP', {
        'USD_GBP': ConversionData(frame([.8], start='2023-12-31', spread=0), Granularity.H4),
    })
    order = {'order_id': 1, 'signal': 1, 'available_time': time, 'spread': .0002, 'status': 'pending'}
    engine = MovingAverageCrossoverBacktester(config=config)
    engine._state = state
    return engine, state, config, conversions, order, time


def test_enter_and_exit_reconcile_cash_equity_and_reserved_capital(accounting):
    engine, state, config, conversions, order, time = accounting
    assert engine._enter_position(order, 1.25, time, conversions)
    assert state.balance == 9999  # Only commission is expensed, not notional.
    assert state.position.reserved_notional == 1000
    assert state.equity[-1]['unrealised_pnl'] == pytest.approx(-.16)
    assert state.equity[-1]['equity'] == pytest.approx(9998.84)
    assert state.next_trade_id == 2
    assert order['status'] == 'filled'

    engine._exit_position(1.26, time + pd.Timedelta(hours=1), 'crossover', conversions)
    assert state.balance == pytest.approx(10006)
    assert state.position is None
    assert state.trades[0]['gross_pnl'] == pytest.approx(8)
    assert state.trades[0]['net_pnl'] == pytest.approx(6)
    assert state.equity[-1]['reserved_notional'] == 0
    assert [fill['action'] for fill in state.fills] == ['entry', 'exit']


def test_rejected_entry_leaves_position_cash_and_fill_counter_unchanged(accounting):
    engine, state, config, conversions, order, time = accounting
    engine = MovingAverageCrossoverBacktester(config=replace(config, units=10001))
    engine._state = state
    assert not engine._enter_position(order, 1.25, time, conversions)
    assert state.balance == 10000
    assert state.position is None
    assert state.next_trade_id == 1
    assert not state.fills and not state.equity
    assert state.rejected_orders[0]['reason'] == 'insufficient_capital'
    assert order['status'] == 'rejected'


def test_financing_accrues_each_cutoff_once(accounting):
    engine, state, config, conversions, order, time = accounting
    engine._enter_position(order, 1.25, time, conversions)
    cutoff = time.normalize() + pd.Timedelta(hours=22)
    engine._accrue_financing(cutoff, 1.25, conversions)
    engine._accrue_financing(cutoff, 1.25, conversions)
    assert state.balance == pytest.approx(9998.9)
    assert state.position.financing == pytest.approx(-.1)
    assert len(state.financing) == 1
    assert state.last_rollover == cutoff


def test_record_equity_does_not_realise_pnl(accounting):
    engine, state, config, conversions, order, time = accounting
    engine._enter_position(order, 1.25, time, conversions)
    position_before = deepcopy(state.position)
    engine._record_equity(time + pd.Timedelta(minutes=5), 1.26, conversions)
    assert state.balance == 9999
    assert state.position == position_before
    assert state.equity[-1]['unrealised_pnl'] == pytest.approx(8)
    assert state.equity[-1]['equity'] == pytest.approx(10007)
    assert not state.trades


def test_scoring_candidates_cannot_change_account_state(accounting):
    engine, state, config, conversions, order, time = accounting
    engine = InsideBarBacktester(config=replace(config, indicator=Indicator.INSIDE_BAR_MOMENTUM))
    engine._state = state
    before = deepcopy(state)
    row = {'time': time, 'bid_c': 1.26, 'ask_c': 1.2602}
    outcome = PathOutcome(entry_price=1.25, exit_price=1.26, exit_reason='take_profit')
    score = engine._score_outcome(outcome, row=row, direction=1, conversions=conversions)
    assert score == pytest.approx((6, 1))
    assert state == before


def test_register_signals_replaces_pending_but_preserves_open_inside_trade(accounting):
    engine, state, config, conversions, order, time = accounting
    engine = InsideBarBacktester(config=replace(config, indicator=Indicator.INSIDE_BAR_MOMENTUM))
    engine._state = state
    event = {'available_time': time, 'signal': 1}
    engine._accept_signal(event)
    first_order = state.pending_order
    engine._accept_signal(event)
    assert first_order['status'] == 'replaced'
    assert state.pending_order['order_id'] == 2
    engine._enter_position(state.pending_order, 1.25, time, conversions)
    state.pending_order = None
    engine._accept_signal(event)
    assert state.orders[-1]['status'] == 'ignored_open_position'
    assert state.pending_order is None
    assert state.position.trade_id == 1


def test_independent_states_do_not_share_ledger_lists(accounting):
    _, first, _, _, order, time = accounting
    second = BacktestState(pair='EUR_GBP', balance=20000, last_rollover=time)
    for name in ('orders', 'fills', 'trades', 'rejected_orders', 'financing', 'equity'):
        assert getattr(first, name) is not getattr(second, name)
    first.orders.append(order)
    first.balance -= 1
    assert not second.orders
    assert second.balance == 20000


def test_repeated_runs_on_one_backtester_reset_accounts_and_trade_ids():
    config = BacktestConfig(
        execution_granularity=Granularity.H4, short_window=1, long_window=3, units=10,
    )
    engine = MovingAverageCrossoverBacktester(config=config)
    candles = frame([3, 2, 1, 2, 3, 2, 1])
    conversions = {'USD_GBP': ConversionData(frame([1], start='2023-12-31', spread=0), Granularity.H4)}
    first = engine.run_data('GBP_USD', candles, conversion_data=conversions)
    first_equity = first.equity.copy(deep=True)
    first_state = engine.state
    first_state_balance = first_state.balance
    second = engine.run_data('GBP_USD', candles, conversion_data=conversions, config=replace(config, initial_balance=20000))
    assert first.trades.iloc[0].trade_id == second.trades.iloc[0].trade_id == 1
    assert second.equity.iloc[0].balance == 20000
    assert second.metrics['net_profit'] == pytest.approx(first.metrics['net_profit'])
    pd.testing.assert_frame_equal(first.equity, first_equity, check_exact=True)
    assert len(engine.results) == 2
    assert engine.state is not first_state
    assert first_state.balance == first_state_balance
    assert engine.state.balance == pytest.approx(second.metrics['final_equity'])
    assert engine.state.position is None
    assert engine.state.pending_order is None


def test_state_requires_initialisation():
    engine = MovingAverageCrossoverBacktester()
    with pytest.raises(RuntimeError, match='not initialised'):
        _ = engine.state


def test_helpers_use_the_owning_instance_state(accounting):
    engine, state, config, conversions, order, time = accounting
    other = MovingAverageCrossoverBacktester(config=config)
    other._state = BacktestState(pair='GBP_USD', balance=20000, last_rollover=time)
    engine._enter_position(order, 1.25, time, conversions)
    assert engine.state is state
    assert engine.state.position is not None
    assert other.state.balance == 20000
    assert other.state.position is None
    assert not other.state.fills



def test_run_override_is_visible_but_does_not_replace_constructor_defaults():
    defaults = BacktestConfig(execution_granularity=Granularity.H4, short_window=1, long_window=3)
    engine = MovingAverageCrossoverBacktester(config=defaults)
    other = MovingAverageCrossoverBacktester(config=defaults)
    assert engine.config is defaults
    override = replace(defaults, initial_balance=20000)
    candles = frame([1, 1, 1, 1])
    result = engine.run_data('EUR_GBP', candles, config=override)
    assert engine.config is result.configuration is override
    assert engine.indicator == override.indicator
    assert result.equity.iloc[0].balance == 20000
    assert other.config is defaults
    next_result = engine.run_data('EUR_GBP', candles)
    assert engine.config is next_result.configuration is defaults
    assert engine.indicator == defaults.indicator
    assert next_result.equity.iloc[0].balance == 10000
    assert result.configuration is override
