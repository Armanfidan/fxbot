from src.app.Backtester import Backtester, Conversions
from src.model.Indicator import Indicator
from functools import partial
from itertools import product
from typing import Callable
from src.model.Granularity import Granularity
from src.model.PathOutcome import PathOutcome
from src.service.signal_generators.InsideBarMomentumSignalGenerator import InsideBarMomentumSignalGenerator


def _cross(start, end, level, upward):
    """Whether a price moving from start to end reaches a trigger level and, if so, how far through the reach happens.
    We assume that the price moves linearly and continuously from start to end."""
    if start >= level if upward else start <= level:
        return 0.0
    if (end >= level if upward else end <= level) and end != start:
        return (level - start) / (end - start)
    return None


def _path_outcome(
        row: dict,
        direction: int,
        entry_level: float,
        stop_loss: float,
        take_profit: float,
        existing_entry_price: float | None = None,
        outcome_score: Callable[[PathOutcome], tuple[float, int]] | None = None,
) -> tuple[PathOutcome, bool]:
    """
    Enumerate OHLC paths and calculate outcomes.
    Always assume only one entry/exit opportunity within the current candle.
    todo This is a limitation of the current design. We cannot handle the following case:
     - olhc = 100, 90, 110, 100
     - entry = 100, stop_loss = 90, take_profit = 110
     This should trigger two entries and two exits within the same candle. Currently this is unimplemented.
    """
    outcomes: list[PathOutcome] = []
    # bid/ask: ohlc/ohlc, ohlc/olhc, olhc/ohlc, olhc/olhc
    for bid_order, ask_order in product(('ohlc', 'olhc'), repeat=2):
        bid = [row[f'bid_{p}'] for p in bid_order]
        ask = [row[f'ask_{p}'] for p in ask_order]

        if any(b > a for b, a in zip(bid, ask)):
            # This means that the bid price is higher than the ask price, meaning infeasible path
            continue

        # direction == 1 -> long (entry: buy, exit: sell), else -> short (entry: sell, exit: buy)
        entry_side, exit_side = (ask, bid) if direction == 1 else (bid, ask)
        entry_price: float | None = existing_entry_price
        position_open_at_candle_open: bool = existing_entry_price is not None  # Already entered at the beginning of the candle
        entry_segment = -1  # no intra-bar segment has been identified yet
        entry_fraction = 0.0  # how far through the segment the entry happens
        if entry_price is None:
            # The bar open already satisfies entry
            if entry_side[0] >= entry_level if direction == 1 else entry_side[0] <= entry_level:
                entry_price, position_open_at_candle_open = entry_side[0], True
            # Not open yet on open price
            else:
                for segment in range(3):
                    # Identify a cross in o->h, h->l, l->c (or whatever the path is)
                    fraction = _cross(entry_side[segment], entry_side[segment + 1], entry_level, direction == 1)
                    if fraction is not None:
                        entry_price, entry_segment, entry_fraction = entry_level, segment, fraction
                        break
        # No entries identified, return none
        if entry_price is None:
            outcomes.append(PathOutcome())
            continue

        # Trace exit after entry
        exit_price = reason = None
        exit_at_candle_open = False  # Did we exit at the opening price of the candle?
        if position_open_at_candle_open:
            price = exit_side[0]
            if price <= stop_loss if direction == 1 else price >= stop_loss:
                exit_price, reason, exit_at_candle_open = price, 'stop_loss', True
            elif price >= take_profit if direction == 1 else price <= take_profit:
                exit_price, reason, exit_at_candle_open = take_profit, 'take_profit', True

        # Account for an additional possibility: What if the trade entered, reached stop loss, then went up to the target?
        # In this case we should lose the trade, not turn a profit. Make a conservative assumption here.
        if reason is None:
            # Search all segments from the entry segment
            for segment in range(max(0, entry_segment), 3):
                # Find the entry fraction if we're in the entry segment, otherwise we start from the beginning of the segment
                fraction = entry_fraction if segment == entry_segment else 0.0
                # Find the price at the starting point
                start = exit_side[segment] + fraction * (exit_side[segment + 1] - exit_side[segment])
                # Find the exit price, i.e., the exit price at the start of the next segment
                end = exit_side[segment + 1]
                hits = []
                # Examine both possibilities: up or down
                for level, label, upward in (
                    (stop_loss, 'stop_loss', direction == -1),
                    (take_profit, 'take_profit', direction == 1)
                ):
                    if (hit := _cross(start, end, level, upward)) is not None:
                        # We model stop loss as a stop-market order, so if it's been crossed we use the next available starting price.
                        # A take profit is a limit order, so we just use the threshold itself. This is a more pessimistic assumption.
                        fill = start if label == 'stop_loss' and hit == 0 else level
                        hits.append((hit, 0 if label == 'stop_loss' else 1, fill, label))

                if hits:
                    _, _, exit_price, reason = min(hits)
                    break

        outcomes.append(PathOutcome(
            entry_price=entry_price,
            exit_price=exit_price,
            exit_reason=reason,
            position_open_at_candle_open=position_open_at_candle_open,
            exit_at_candle_open=exit_at_candle_open,
        ))

    if not outcomes:
        raise ValueError('No feasible nonnegative-spread OHLC path')

    # A new intrabar entry may reverse to the stop before reaching the later extreme.
    if existing_entry_price is None and any(
        outcome.entry_price is not None and not outcome.position_open_at_candle_open
        for outcome in outcomes
    ):
        stop_touched = row['bid_l'] <= stop_loss if direction == 1 else row['ask_h'] >= stop_loss
        if stop_touched:
            outcomes.append(PathOutcome(
                entry_price=entry_level, exit_price=stop_loss, exit_reason='stop_loss',
            ))

    unique = set(outcomes)
    mark = row['bid_c' if direction == 1 else 'ask_c']

    def score(outcome: PathOutcome) -> tuple[float, int]:
        terminal_price = mark if outcome.exit_price is None else outcome.exit_price
        pnl = 0.0 if outcome.entry_price is None else direction * (terminal_price - outcome.entry_price)
        return pnl, 0 if outcome.exit_reason == 'stop_loss' else 1

    return min(outcomes, key=outcome_score or score), len(unique) > 1


class InsideBarBacktester(Backtester):
    """Inside-bar stop entries with conservative intrabar stop/target execution."""
    indicator = Indicator.INSIDE_BAR_MOMENTUM

    def _create_signal_generator(self, pair):
        return InsideBarMomentumSignalGenerator(
            pair,
            self.config.pip_location,
            self.config.strategy_granularity,
        )

    def _experiment_configs(self, ma_windows):
        return [self._default_config]

    def _default_execution_granularity(self, trade_granularity):
        return Granularity.M5

    def _result_key(self, config):
        # Retain existing export names and plot-data keys.
        return config.short_window, config.long_window

    def _plot_result(self, plotter, result, props):
        plotter.plot_backtest(result)

    def _accept_signal(self, event: dict) -> None:
        """Record a new signal, replacing a pending order unless an inside-bar trade is open."""
        order = dict(event, order_id=len(self.state.orders) + 1, status='pending')
        self.state.orders.append(order)
        if self.state.position:
            order['status'] = 'ignored_open_position'
            return
        if self.state.pending_order:
            self.state.pending_order['status'] = 'replaced'
        self.state.pending_order = order

    def _score_outcome(
        self, candidate: PathOutcome, *, row: dict, direction: int,
        conversions: Conversions,
    ) -> tuple[float, int]:
        """Value a hypothetical path without mutating account state."""
        if candidate.entry_price is None:
            return 0.0, 1

        slippage = (self.config.costs.slippage_pips or 0) * 10 ** self.config.pip_location
        commission = self.config.costs.commission_per_fill or 0.0

        actual_entry = candidate.entry_price if self.state.position else candidate.entry_price + direction * slippage
        terminal = row['bid_c' if direction == 1 else 'ask_c'] if candidate.exit_price is None else candidate.exit_price

        if candidate.exit_price is not None and candidate.exit_reason != 'take_profit':
            terminal -= direction * slippage

        time = (
            row['time'] if candidate.exit_at_candle_open
            else row['time'] + self.config.execution_granularity.value
        )
        value = (
            conversions.convert(direction * self.config.units * (terminal - actual_entry), self.state.quote_currency, time)
            - (commission * (int(self.state.position is None) + int(candidate.exit_price is not None)))
        )
        return value, 0 if candidate.exit_reason == 'stop_loss' else 1

    def _process_candle(self, row: dict, conversions: Conversions) -> None:
        """Select the conservative path, then apply only that path's actual fills."""
        position, order = self.state.position, self.state.pending_order
        if position is None and order is None:
            return

        direction = position.signal if position else int(order['signal'])

        outcome_score = partial(
            self._score_outcome, row=row, direction=direction,
            conversions=conversions,
        )

        outcome, ambiguous = _path_outcome(
            row=row,
            direction=direction,
            entry_level=None if position else order['entry_stop'],
            stop_loss=position.stop_loss if position else order['stop_loss'],
            take_profit=position.take_profit if position else order['take_profit'],
            existing_entry_price=position.entry_price if position else None,
            outcome_score=outcome_score,
        )

        if outcome.entry_price is None:
            return

        start, end = row['time'], row['time'] + self.config.execution_granularity.value
        if position is None:
            order['spread'] = (
                row['ask_o'] - row['bid_o'] if outcome.position_open_at_candle_open
                else max(row['ask_h'] - row['bid_h'], row['ask_l'] - row['bid_l'])
            )
            entry_time = start if outcome.position_open_at_candle_open else end
            entered = self._enter_position(order, outcome.entry_price, entry_time, conversions, ambiguous)

            self.state.pending_order = None
            if not entered:
                return
        else:
            position.ambiguous |= ambiguous

        self.state.ambiguous_candles += int(ambiguous)
        if outcome.exit_reason:
            exit_time = start if outcome.exit_at_candle_open else end
            if exit_time == end:
                self._accrue_candle_financing(row, conversions)
            self._exit_position(outcome.exit_price, exit_time, outcome.exit_reason, conversions)
