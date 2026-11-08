# Forex Backtesting System and Real-Time Algorithmic Trading Bot

A modular Python FX research project integrating OANDA market data, incremental strategies, historical execution simulation and account performance evaluation.
Moving-average crossover and inside-bar momentum backtests are implemented.
The RabbitMQ live-trading pipeline is incomplete and is reserved for a later milestone.

## Installation

Create a Python 3.12+ environment and install `requirements.txt`.
Historical downloads require `configuration/credentials.json`, following `credentials_template.json`.
Offline backtests do not require credentials.

## Trustworthy backtest milestone

Python 3.12+ is required.
Run commands from the project root using module syntax:

```bash
python -m pytest
python -m tools.offline_backtest_smoke --output test_results/offline_smoke
python -m src.backtesting_main --from-time 2024-01-01 --to-time 2024-02-01 --currencies EUR GBP --indicator INSIDE_BAR_MOMENTUM --strategy-granularity H4 --execution-granularity M5
```

The smoke command uses the existing historical EUR/GBP H4 cache for both strategies, with explicitly coarse H4 execution.
It needs no credentials or broker access.
M5 execution, including ambiguous fills, is verified separately with deterministic test scenarios.
The CLI may download market data unless `--offline` is supplied; it never submits orders.
Interval caching remains a later milestone, so offline CLI requests must match an existing cache filename.

Use `MovingAverageCrossoverBacktester` or `InsideBarBacktester` with `.run_data(pair, strategy_candles, execution_candles, conversion_data)`. Each subclass fixes its indicator; a supplied `BacktestConfig` must match it. `Backtester` provides the shared replay and accounting methods and has unimplemented strategy hooks.
Supply direct/inverse account conversion series as `{pair: ConversionData(candles, granularity)}`.
Defaults are GBP 10,000, 1,000 units, H4 strategy and M5 execution.
Both paths use the same incremental signal generators.
Read [the conventions and worked examples](docs/BACKTEST_CONVENTIONS.md) before interpreting results.

Results expose signals, orders, fills, closed trades, financing, equity history, rejected orders, ambiguity counts and metrics.
`result.export(directory)` writes CSV ledgers plus a JSON summary.
Every pair/window experiment has its own starting capital; results are not a portfolio.
Missing cost assumptions are listed explicitly.

Set `CostConfig(slippage_pips=..., commission_per_fill=..., financing_rates={pair: {'long': ..., 'short': ...}})` for fully configured costs; signed financing fractions are simplified daily adjustments at 22:00 UTC.

The evaluator accepts account equity history (including initial baseline) and closed trades.
ROI is a net return fraction, not a gross growth factor.
Undefined ratios are JSON null.
Risk-free is configurable (default zero); there is no yield API integration.
The live system remains unfinished pending the next milestones; do not run the live entry point as a validated trading system.
