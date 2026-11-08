"""Explicit historical backtest entrypoint; never places broker orders."""
import argparse
from datetime import datetime
from src.app.MovingAverageCrossoverBacktester import MovingAverageCrossoverBacktester
from src.app.InsideBarBacktester import InsideBarBacktester
from src.model.Backtest import BacktestConfig, CostConfig
from src.model.Indicator import Indicator
from src.model.Granularity import Granularity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-time', required=True, help='ISO UTC timestamp')
    parser.add_argument('--to-time', required=True, help='ISO UTC timestamp')
    parser.add_argument('--currencies', nargs='+', default=['EUR', 'GBP'])
    parser.add_argument('--indicator', choices=['MA_CROSSOVER', 'INSIDE_BAR_MOMENTUM'], default='MA_CROSSOVER')
    parser.add_argument('--strategy-granularity', choices=[g.name for g in Granularity if g != Granularity.M], default='H4')
    parser.add_argument('--execution-granularity', choices=[g.name for g in Granularity if g != Granularity.M], default='M5')
    parser.add_argument('--windows', nargs='+', type=int, default=[16, 64])
    parser.add_argument('--units', type=int, default=1000)
    parser.add_argument('--initial-balance', type=float, default=10000)
    parser.add_argument('--slippage-pips', type=float)
    parser.add_argument('--commission', type=float)
    parser.add_argument('--offline', action='store_true', help='Exact cache only; fail if data is absent')
    parser.add_argument('--output', default='test_results')
    args = parser.parse_args()

    config = BacktestConfig(indicator=Indicator[args.indicator], initial_balance=args.initial_balance,
                            units=args.units, costs=CostConfig(args.slippage_pips, args.commission))
    backtester_class = {
        Indicator.MA_CROSSOVER: MovingAverageCrossoverBacktester,
        Indicator.INSIDE_BAR_MOMENTUM: InsideBarBacktester,
    }[config.indicator]

    results = backtester_class(config=config).run(
        args.currencies, Granularity[args.strategy_granularity], datetime.fromisoformat(args.from_time),
        datetime.fromisoformat(args.to_time), Granularity[args.execution_granularity], args.offline,
        args.windows, output_directory=args.output)

    for result in results:
        print(result.pair, result.metrics, 'omitted costs:', result.omitted_costs)


if __name__ == '__main__':
    main()
