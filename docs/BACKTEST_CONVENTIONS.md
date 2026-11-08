# Backtest conventions

- The architecture flows through the client, incremental signal generator and Backtester to the IndicatorEvaluator.
- Experiments are independently funded, not a shared portfolio.
- Currently we do not have live execution and interval caching; these are later milestones.

## Time and data

- All timestamps are UTC: We always retrieve candles with UTC timestamps.
- Candle timestamps denote the opening time; a candle becomes known at opening time plus its fixed granularity.
- Monthly calendar candles are not supported, because a calendar month is not a fixed duration.
- Inputs must be positive, finite, sorted, unique, valid bid/ask/mid OHLC.
- Missing intervals are allowed (e.g. market closures); there are no fabricated fills in gaps.
- Strategy candle boundaries may not cut through an execution candle. I.e., the start/end times of strategy and execution candles must always be aligned. Candles cannot be split.
- Execution data must span every actionable strategy signal; a final signal without a subsequent execution candle expires.

## Strategies

### Simple Moving Average

- Midpoint close is used for moving average calculations.
- The first full window establishes the previous comparison, not a signal.
- Crossovers require the current short SMA to be strictly on the new side:
  - previous below/equal and current above = buy
  - previous above/equal and current below = sell.
- Equality itself emits no signal.
- If we are already holding, we cannot buy again, so we avoid double signals.
- Both windows must be positive integers, short < long.

### Inside Bar Momentum

- Inside bars must have strictly lower midpoint high and strictly higher midpoint low than the preceding bar.
- Previous bullish candles select long; bearish or doji candles select short.
- For preceding range R (High - Low), long levels are
  - Entry trigger: H + 0.1R
  - Stop loss: H - 0.4R
  - Take profit: H + 0.8R
- Short levels are
  - Entry trigger: H - 0.1R
  - Stop loss: H + 0.4R
  - Take profit: H - 0.8R
- H4 or coarser fixed strategy intervals are required, otherwise candles are too short-term to see any momentum.
- An open position ignores new signals, newer signals replace pending entries. **There can be only one open position per currency pair.** So a signal emitted while a position is open is discarded even if the position exits in the next bar.
- Signals become available only after their candle completes.
- Market orders use the next available execution open.
- Long position
  - Entry: buy at ask
  - Exit: sell at bid
- Short position
  - Entry: sell at bid
  - Exit: buy at ask


## Intrabar uncertainty

Each candle contains intrabar uncertainty: We don't know the movement of the price from open to close. It could have reached its high first, then low, vice versa, or jagged movements.

Depending on the movement within the bar, the outcome of the signal could be entirely different. Therefore, we must consider all possibilities (assuming movement is linear between each vertex).

- To process pending signals, enumerate continuous open-high-low-close and open-low-high-close paths for both bid and ask prices, discarding combinations which cause a negative spread (these are impossible).
- Append an "entry, then stop loss straight away within the candle" outcome if applicable, then select the most conservative outcome. This way, prevent higher predicted profits due to considering too few possible outcomes.
- Process each crossing chronologically within each path; ignore exit before an entry.
- Always select the least profitable feasible outcome including liquidation value for positions remaining open.
- If we selected from multiple feasible entry/exit outcomes caused by different paths, flag the execution candle and the trade as ambiguous.
- Identical stop/target outcomes are not counted twice.
- Implement special treatment for gapping:
  - Stop loss gaps fill at the next available opening price, even if this price is worse than the stop loss.
  - Take profit (exit) gaps fill at the target, even if the next available selling price is higher than the target, to prevent awarding extra profit due to the gap.
- Intrabar fills are timestamped at candle completion because exact event time is unknown, whereas opening fills retain the opening timestamp. Duration and rollover eligibility therefore use these conservative timestamps.
- Slippage applies adversely to market/stop orders; take-profit limit fills remain at target.

## Accounting and conversion

- Start with a default balance of GBP 10,000 equity.
- Each trade size is 1,000 base units. We use no leverage.
- Cash balance changes only through realised P&L, commission and financing.
  - Commission is £1 per transaction by default.
  - Our financing assumption is a simplified adjustment for holding a position across an overnight cutoff. For EUR/USD this is -1 bps per daily cutoff for long positions and 0.5 bps for short positions.
- Reserve base notional is converted to account currency at entry; do not expense the notional.
- Require sufficient equity for notional plus entry commission and immediate spread/slippage loss.
- No leveraged margin calls are modelled.
- Reserve is released on exit.
- Mark long positions to bid close, shorts to ask close.
- Force final liquidation at the final execution close.

- Quote P&L = direction × units × (exit/mark − entry).
- Convert quote P&L to GBP with the most recent completed direct or inverse conversion candle.
- Positive balances use bid for direct conversion or 1/ask for inverse; negative balances use ask or 1/bid.
- Exposure conversions conservatively use the ask price.
- If source currency already is GBP, conversion is 1.
- No future data or synthetic conversion crosses; missing conversion data fails the run.
- Zero amounts need no conversion.
- The traded pair may supply conversion observations, but only after its candles complete: We must use the closing prices for conversion to prevent timing ambiguities in exposure conversion.
- Conversion data must be passed explicitly with its own granularity.

## Costs

- Bid/ask spread is always included.
- Optional slippage is pips per fill; optional commission is GBP per fill.
- Optional financing specifies a signed percentage of the opening balance of the position on each day, by pair and long/short direction (negative=debits, positive=credits).
- Financing will accrue at 22:00 UTC for positions entered strictly before and still open at that cutoff, including weekends.
- This is a simplified cash adjustment, not broker swap/triple-rollover replication.
- Positions closed exactly at the cutoff are charged first.
- Missing inputs mean zero for simulation and are explicitly listed as omitted; only all three supplied is labelled fully configured.
  - slippage_pips: adverse price adjustment, in pips, for market and stop fills.
  - commission_per_fill: fixed GBP commission charged on each entry and exit.
  - financing_rates: signed daily financing rates for the traded pair, with both long and short values.
- The label describes configuration completeness, not broker calibration.
- Explicit zero is a supplied assumption.

## Metrics

- Returns use account equity, including the initial baseline before any fill.
- Total return = final/initial − 1.
- CAGR uses actual elapsed UTC seconds and 365.25 days/year; undefined for nonpositive ending equity or zero duration.
- Daily returns use last observed equity on each UTC calendar day with observations; the first observed day is relative to initial equity, and absent days are not invented.
- FX Sunday observations are retained.
- Sharpe ratio uses sample standard deviation (ddof=1) of daily excess returns; annual risk-free defaults to zero and is converted via (1+rf)^(1/252)−1.
- Sortino ratio uses RMS of min(daily excess return,0) across all observations.
- Annualise by sqrt(252).
- Drawdown includes initial equity; report a nonnegative fraction and GBP amount.
- Calmar ratio = CAGR / fractional max drawdown.
- Profit/drawdown = net GBP profit / max GBP drawdown.
- Zero denominators and insufficient samples return null.
- Duration is entry-to-exit elapsed UTC time, not the difference between adjacent data rows.
- Win rate uses net trade P&L after costs.
- No signal-only return formula is used as account performance.

## Worked examples

- Start with a balance of GBP 10,000.

Trade 1 (Long)
- Enter long EUR/GBP at ask 0.8002 (1,000 units), then exit at bid 0.8100
- Realised gain is 1,000 * (0.8100 - 0.8002) = GBP 9.80 before costs.
- After subtracting two GBP 1 commissions, The balance is GBP 10,007.80.
- Reserve at entry of the first trade is GBP 800.20. This is released on exit.

Trade 2 (Short)

- Enter short GBP/USD at bid 0.8000 (1,000 units), then exit at bid 0.7902
- Realised gain is -1,000 * (0.7902 - 0.8000) = GBP 9.80 before costs.
- USD gain 10 with GBP_USD bid/ask 1.25/1.26: GBP 10/1.26; a USD loss of 10 converts to −GBP 10/1.25.
- Equity 10,000 → 11,000 → 9,900 → 10,890: total return 8.9%.
- Maximum drawdown 10%, GBP drawdown 1,100, profit/drawdown 890/1,100.
