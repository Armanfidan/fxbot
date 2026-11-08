"""Run both strategies on cached historical EUR/GBP, without credentials/network.

H4 execution is deliberate: the supplied EUR/GBP cache contains only H4 candles.
This verifies integration and reconciliation, not strategy profitability or M5 realism.
Run: python -m tools.offline_backtest_smoke --output test_results/offline_smoke
"""
import argparse
from pathlib import Path
import pandas as pd
from src.app.MovingAverageCrossoverBacktester import MovingAverageCrossoverBacktester
from src.app.InsideBarBacktester import InsideBarBacktester
from src.model.Backtest import BacktestConfig
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator
from src.util.Constants import CANDLE_FOLDER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='test_results/offline_smoke')
    args = parser.parse_args()
    candidates = sorted(Path(CANDLE_FOLDER).glob('EUR_GBP_H4*.pkl'))
    if not candidates:
        raise FileNotFoundError('Smoke run requires the existing EUR_GBP_H4 cache')
    candles = pd.read_pickle(candidates[0])
    for indicator in Indicator:
        config = BacktestConfig(indicator=indicator, execution_granularity=Granularity.H4,
                                short_window=4, long_window=8)
        backtester_class = {
            Indicator.MA_CROSSOVER: MovingAverageCrossoverBacktester,
            Indicator.INSIDE_BAR_MOMENTUM: InsideBarBacktester,
        }[indicator]
        result = backtester_class(config=config).run_data('EUR_GBP', candles)
        expected = config.initial_balance + result.trades.net_pnl.sum()
        if abs(result.metrics['final_equity'] - expected) > 1e-7:
            raise AssertionError('Trade ledger does not reconcile with final equity')
        if result.equity.iloc[-1].reserved_notional != 0:
            raise AssertionError('Final position was not liquidated')
        result.export(Path(args.output) / indicator.name)
        print(indicator.name, 'trades:', len(result.trades), 'final equity:', round(expected, 2),
              'ambiguous candles:', result.ambiguous_candles, 'omitted costs:', result.omitted_costs)


if __name__ == '__main__':
    main()
