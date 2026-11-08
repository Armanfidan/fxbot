from dataclasses import replace
import json
import pandas as pd
import pytest
from src.app.Backtester import Conversions
from src.app.InsideBarBacktester import _path_outcome
from src.app.MovingAverageCrossoverBacktester import MovingAverageCrossoverBacktester
from src.app.InsideBarBacktester import InsideBarBacktester
from src.model.Backtest import BacktestConfig, CostConfig, ConversionData
from src.model.Granularity import Granularity as G
from src.model.Indicator import Indicator as I
from src.service.signal_generators.InsideBarMomentumSignalGenerator import InsideBarMomentumSignalGenerator


def candle(time, o, h=None, l=None, c=None, spread=.02):
    h = o if h is None else h
    l = o if l is None else l
    c = o if c is None else c
    row = {'time': pd.Timestamp(time), 'volume': 1}
    for side, delta in [('mid', 0), ('ask', spread/2), ('bid', -spread/2)]:
        for name, value in zip('ohlc', (o,h,l,c)):
            row[f'{side}_{name}'] = value + delta
    return row


def frame(values, freq='4h', start='2024-01-01', spread=.02):
    return pd.DataFrame([candle(t, p, spread=spread) for t,p in zip(pd.date_range(start, periods=len(values), freq=freq, tz='UTC'), values)])


def conversion(rate=1, pair='USD_GBP', start='2023-12-31'):
    return {pair: ConversionData(frame([rate], start=start, spread=0), G.H4)}


def ma_config(**kwargs):
    return BacktestConfig(strategy_granularity=G.H4, execution_granularity=G.H4,
                          short_window=1, long_window=3, units=10, **kwargs)


def inside_data(short=False):
    return pd.DataFrame([candle('2024-01-01T00:00Z', 10,12,8,9 if short else 11),
                         candle('2024-01-01T04:00Z', 10,11,9,10.5)])


def inside_config(**kwargs):
    return BacktestConfig(indicator=I.INSIDE_BAR_MOMENTUM, units=10, **kwargs)


def execute_inside(rows, short=False, **kwargs):
    return InsideBarBacktester(config=inside_config(**kwargs)).run_data('GBP_USD', inside_data(short), pd.DataFrame(rows), conversion())


def test_ma_next_open_spread_and_final_account_reconciliation():
    data = frame([3,2,1,2,3,2,1])
    result = MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD', data, conversion_data=conversion())
    trade = result.trades.iloc[0]
    assert trade.entry_time == pd.Timestamp('2024-01-01T16:00Z')
    assert trade.exit_time == pd.Timestamp('2024-01-02T00:00Z')
    assert trade.entry_price == 3.01
    assert trade.exit_price == .99
    assert trade.net_pnl == pytest.approx(-20.2)
    assert result.equity.iloc[-1].balance == pytest.approx(9979.8)
    assert result.equity.iloc[-1].reserved_notional == 0
    assert result.metrics['net_profit'] == pytest.approx(result.trades.net_pnl.sum())
    assert (result.fills.iloc[0].time >= result.signals.loc[result.signals.signal == 1, 'available_time'].iloc[0])


def test_ma_final_liquidation_and_costs_are_drawdown():
    costs = CostConfig(slippage_pips=1, commission_per_fill=1, financing_rates={'GBP_USD': {'long': 0, 'short': 0}})
    result = MovingAverageCrossoverBacktester(config=ma_config(costs=costs)).run_data('GBP_USD', frame([3,2,1,2,3]), conversion_data=conversion())
    trade = result.trades.iloc[0]
    assert trade.exit_reason == 'final_liquidation'
    assert trade.net_pnl == pytest.approx(-.202-2)
    assert result.metrics['max_drawdown_amount'] == pytest.approx(2.202)
    assert result.omitted_costs == []


def test_inside_detection_levels_and_batch_parity():
    data = inside_data()
    batch = InsideBarMomentumSignalGenerator('GBP_USD', -4, G.H4)
    batch.generate_signals_for_backtesting(data)
    incremental = InsideBarMomentumSignalGenerator('GBP_USD', -4, G.H4)
    incremental.iterate_from_dataframe(data.iloc[:1])
    incremental.iterate_from_dataframe(data.iloc[1:])
    pd.testing.assert_frame_equal(batch.generate_signals_dataframe(), incremental.generate_signals_dataframe())
    row = batch.generate_signals_dataframe().iloc[-1]
    assert (row.signal, row.entry_stop, row.stop_loss, row.take_profit) == pytest.approx((1,12.4,10.4,15.2))
    data.loc[1, 'mid_h'] = 12
    boundary = InsideBarMomentumSignalGenerator('GBP_USD', -4, G.H4, data)
    assert boundary.queue[-1].signal == 0
    with pytest.raises(ValueError):
        InsideBarMomentumSignalGenerator('GBP_USD', -4, G.M5)


@pytest.mark.parametrize('short', [False, True])
def test_inside_both_exits_chooses_stop(short):
    row = candle('2024-01-01T08:00Z', 10 if short else 12, 16,4,10)
    result = execute_inside([row], short)
    trade = result.trades.iloc[0]
    assert trade.exit_reason == 'stop_loss'
    assert trade.net_pnl == pytest.approx(-20)
    assert trade.signal == (-1 if short else 1)
    assert result.ambiguous_candles == 1
    assert trade.ambiguous


def test_exit_before_entry_is_not_counted():
    # Low first can occur before entry; high first gives a feasible loss, chosen conservatively.
    result = execute_inside([candle('2024-01-01T08:00Z',11,13,10,12.5)])
    assert result.trades.iloc[0].exit_reason == 'stop_loss'
    # Opening entry and a monotonic rise cannot hit the earlier stop.
    result = execute_inside([candle('2024-01-01T08:00Z',12.5,16,12.5,16)])
    assert result.trades.iloc[0].exit_reason == 'take_profit'
    assert result.ambiguous_candles == 0


def test_stop_gap_and_target_gap():
    opened = candle('2024-01-01T08:00Z',12.5)
    stop = execute_inside([opened, candle('2024-01-01T08:05Z',9)])
    assert stop.trades.iloc[0].exit_price == pytest.approx(8.99)
    target = execute_inside([opened, candle('2024-01-01T08:05Z',16)])
    assert target.trades.iloc[0].exit_price == pytest.approx(15.2)


def test_pending_expiry_and_final_signal_expiry():
    result = execute_inside([candle('2024-01-01T08:00Z',10)])
    assert result.trades.empty
    assert result.orders.iloc[0].status == 'expired'
    ma = MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD', frame([3,2,1,2]), conversion_data=conversion())
    assert ma.trades.empty
    assert ma.orders.iloc[-1].status == 'expired'


def test_reject_capital_without_expensing_notional():
    data = frame([3,2,1,2,3])
    result = MovingAverageCrossoverBacktester(config=replace(ma_config(), units=10001)).run_data('GBP_USD', data, conversion_data=conversion())
    assert result.trades.empty
    assert result.rejected_orders.iloc[0].reason == 'insufficient_capital'
    assert result.equity.iloc[-1].equity == 10000
    accepted = MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD', data, conversion_data=conversion())
    assert accepted.equity.balance.min() > 9990
    assert accepted.equity.reserved_notional.max() == 10


def test_direct_inverse_conversion_sides_and_no_future_data():
    direct = Conversions('GBP', conversion(1.25))
    assert direct.convert(10, 'USD', pd.Timestamp('2024-01-01T00:00Z')) == 12.5
    source = pd.DataFrame([candle('2023-12-31T00:00Z',1.255,spread=.01)])
    inverse = Conversions('GBP', {'GBP_USD': ConversionData(source, G.H4)})
    time = pd.Timestamp('2024-01-01T00:00Z')
    assert inverse.convert(10,'USD',time) == pytest.approx(10/1.26)
    assert inverse.convert(-10,'USD',time) == pytest.approx(-10/1.25)
    with pytest.raises(ValueError, match='No completed'):
        inverse.convert(10,'USD',pd.Timestamp('2023-12-31T03:00Z'))
    with pytest.raises(ValueError):
        direct.convert(10,'JPY',time)


def test_rollover_commission_and_ledger_reconciliation():
    costs = CostConfig(0, 1, {'GBP_USD': {'long': -.01, 'short': -.02}})
    rows = [candle('2024-01-01T08:00Z',12.5), candle('2024-01-02T08:00Z',12.5)]
    result = execute_inside(rows, costs=costs)
    assert len(result.financing) == 1
    assert result.financing.iloc[0].time == pd.Timestamp('2024-01-01T22:00Z')
    assert result.financing.iloc[0].amount == pytest.approx(-.1)
    assert result.trades.iloc[0].net_pnl == pytest.approx(-.2-2-.1)
    assert result.equity.iloc[-1].balance == pytest.approx(10000 + result.trades.net_pnl.sum())


def test_input_validation_and_alignment():
    data = frame([3,2,1,2,3])
    with pytest.raises(ValueError, match='sorted'):
        MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD', data.iloc[::-1])
    with pytest.raises(ValueError, match='OHLC'):
        bad = data.copy(); bad.loc[0,'ask_h'] = .5
        MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD', bad)
    with pytest.raises(ValueError, match='cuts through'):
        execution = frame([1,1,1,1,1],freq='4h',start='2024-01-01T02:00Z')
        MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD',data,execution)


def test_export_is_auditable_json(tmp_path):
    result = MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD',frame([3,2,1,2,3]),conversion_data=conversion())
    result.export(tmp_path)
    summary = json.loads((tmp_path/'summary.json').read_text())
    assert summary['funding'] == 'independent'
    assert summary['cost_status'] == 'partial'
    assert summary['metrics']['net_profit'] == pytest.approx(result.metrics['net_profit'])
    assert (tmp_path/'fills.csv').exists()


def test_pending_replaced_and_open_position_ignores_new_signal():
    strategy = pd.DataFrame([
        candle('2024-01-01T00:00Z',10,12,8,11),
        candle('2024-01-01T04:00Z',10,11,9,10.5),
        candle('2024-01-01T08:00Z',10,10.8,9.2,10.4),
    ])
    execution = pd.DataFrame([candle('2024-01-01T08:00Z',10), candle('2024-01-01T12:00Z',10)])
    result = InsideBarBacktester(config=inside_config()).run_data('GBP_USD',strategy,execution,conversion())
    assert result.orders.status.tolist() == ['replaced','expired']
    execution = pd.DataFrame([candle('2024-01-01T08:00Z',12.5),candle('2024-01-01T12:00Z',12.5)])
    result = InsideBarBacktester(config=inside_config()).run_data('GBP_USD',strategy,execution,conversion())
    assert result.orders.status.tolist() == ['filled','ignored_open_position']
    assert len(result.trades) == 1


def test_missing_conversion_fails_before_any_broker_access():
    with pytest.raises(ValueError, match='No completed'):
        MovingAverageCrossoverBacktester(config=ma_config(account_currency='JPY')).run_data('GBP_USD',frame([3,2,1,2,3]))


def test_entry_commission_cannot_overdraw_capital():
    config = replace(ma_config(costs=CostConfig(0,1)), units=10000)
    result = MovingAverageCrossoverBacktester(config=config).run_data('GBP_USD',frame([3,2,1,2,3]),conversion_data=conversion())
    assert len(result.rejected_orders) == 1
    assert result.fills.empty


def test_financing_exact_cutoff_charged_before_exit_and_no_entry_charge():
    costs = CostConfig(0,0,{'GBP_USD':{'long':-.01,'short':-.01}})
    rows = [candle('2024-01-01T08:00Z',12.5),candle('2024-01-01T22:00Z',16)]
    result = execute_inside(rows,costs=costs)
    assert len(result.financing) == 1
    assert result.trades.iloc[0].financing == pytest.approx(-.1)
    assert result.equity.time.is_monotonic_increasing


def test_cutoff_inside_execution_candle_uses_no_future_mark():
    # M5 deliberately offset around rollover; opening fill is observable at 21:58.
    costs = CostConfig(0,0,{'GBP_USD':{'long':-.01,'short':0}})
    result = execute_inside([candle('2024-01-01T08:00Z',10), candle('2024-01-01T21:58Z',12.5,13,12,13)],costs=costs)
    funding_snapshot = result.equity[result.equity.time == pd.Timestamp('2024-01-01T22:00Z')].iloc[0]
    assert funding_snapshot.unrealised_pnl == pytest.approx(-.2)
    assert result.equity.time.is_monotonic_increasing


def test_intrabar_entry_after_rollover_does_not_get_earlier_financing():
    costs = CostConfig(0,0,{'GBP_USD':{'long':-.01,'short':0}})
    result = execute_inside([candle('2024-01-01T08:00Z',10), candle('2024-01-01T21:58Z',12,13,11.5,12.5)],costs=costs)
    assert result.financing.empty
    assert result.equity.time.is_monotonic_increasing


def test_open_position_stop_first_and_take_profit_has_no_slippage():
    rows = [candle('2024-01-01T08:00Z',12.5),candle('2024-01-01T08:05Z',13,16,10,13)]
    result = execute_inside(rows,costs=CostConfig(2,0))
    assert result.trades.iloc[0].exit_reason == 'stop_loss'
    assert result.trades.iloc[0].exit_price == pytest.approx(10.4-.0002)
    assert result.ambiguous_candles == 1
    result = execute_inside([candle('2024-01-01T08:00Z',12.5,16,12.5,16)],costs=CostConfig(2,0))
    assert result.trades.iloc[0].entry_price == pytest.approx(12.5102)
    assert result.trades.iloc[0].exit_price == pytest.approx(15.2)


def test_configuration_validation():
    for changes in ({'units':0},{'initial_balance':-1},{'annual_risk_free_rate':-1},
                    {'strategy_granularity':G.M}, {'execution_granularity':G.D}):
        with pytest.raises(ValueError):
            replace(BacktestConfig(), **changes)
    with pytest.raises(ValueError):
        CostConfig(-1)
    with pytest.raises(ValueError):
        CostConfig(financing_rates={'GBP_USD':{'long':0}})


def test_conversion_changes_only_when_candle_completes():
    series = pd.concat([frame([1], start='2023-12-31', spread=0),
                        frame([2], start='2024-01-01T08:00Z', spread=0)],ignore_index=True)
    conversions = Conversions('GBP', {'USD_GBP':ConversionData(series, G.H4)})
    assert conversions.convert(10,'USD',pd.Timestamp('2024-01-01T11:59Z')) == 10
    assert conversions.convert(10,'USD',pd.Timestamp('2024-01-01T12:00Z')) == 20


def test_no_data_truncation_of_strategy_history():
    with pytest.raises(ValueError,match='ends before'):
        MovingAverageCrossoverBacktester(config=ma_config()).run_data('GBP_USD',frame([3,2,1,2,3]),frame([3,2,1,2]))


def test_entry_and_exit_commission_snapshots_preserve_utc_day():
    result = MovingAverageCrossoverBacktester(config=ma_config(costs=CostConfig(0,1))).run_data('GBP_USD',frame([3,2,1,2,3,2,1]),conversion_data=conversion())
    exit_time = result.trades.iloc[0].exit_time
    snapshot = result.equity[result.equity.time == exit_time].iloc[-1]
    assert snapshot.balance == pytest.approx(10000 + result.trades.net_pnl.sum())
    assert snapshot.reserved_notional == 0


def test_short_gap_and_take_profit():
    opened = candle('2024-01-01T08:00Z',7.5)
    result = execute_inside([opened,candle('2024-01-01T08:05Z',11)],short=True)
    assert result.trades.iloc[0].exit_reason == 'stop_loss'
    assert result.trades.iloc[0].exit_price == pytest.approx(11.01)
    result = execute_inside([opened,candle('2024-01-01T08:05Z',4)],short=True)
    assert result.trades.iloc[0].exit_reason == 'take_profit'
    assert result.trades.iloc[0].exit_price == pytest.approx(4.8)
