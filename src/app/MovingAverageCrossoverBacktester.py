from dataclasses import replace
from src.app.Backtester import Backtester, Conversions
from src.model.Indicator import Indicator
from itertools import combinations
from src.service.signal_generators.MovingAverageCrossoverSignalGenerator import MovingAverageCrossoverSignalGenerator


class MovingAverageCrossoverBacktester(Backtester):
    """Long/flat moving-average crossover execution."""
    indicator = Indicator.MA_CROSSOVER

    def _create_signal_generator(self, pair):
        return MovingAverageCrossoverSignalGenerator(
            pair, self.config.pip_location, self.config.strategy_granularity,
            self.config.short_window, self.config.long_window,
        )

    def _experiment_configs(self, ma_windows):
        windows = sorted(set(ma_windows or [4, 8, 16, 32, 64, 96, 128, 256]))
        return [
            replace(
                self._default_config,
                short_window=short,
                long_window=long
            ) for short, long in combinations(windows, 2)
        ]

    def _default_execution_granularity(self, trade_granularity):
        return trade_granularity

    def _result_key(self, config):
        return config.short_window, config.long_window

    def _plot_result(self, plotter, result, props):
        if props and props.ma_pairs and self._result_key(result.configuration) not in props.ma_pairs:
            return
        plotter.plot_candles_for_ma_crossover(
            result.configuration.short_window, result.configuration.long_window, result.pair,
        )

    def _accept_signal(self, event: dict) -> None:
        """Record a new signal, replacing a pending order for the next opening."""
        order = dict(event, order_id=len(self.state.orders) + 1, status='pending')
        self.state.orders.append(order)
        if self.state.pending_order:
            self.state.pending_order['status'] = 'replaced'
        self.state.pending_order = order

    def _process_candle(
        self, row: dict, conversions: Conversions,
    ) -> None:
        """Execute an available long/flat crossover order at the candle open."""
        order = self.state.pending_order
        if order is None:
            return
        if order['signal'] == 1 and self.state.position is None:
            order['spread'] = row['ask_o'] - row['bid_o']
            self._enter_position(order, row['ask_o'], row['time'], conversions)
        elif order['signal'] == -1 and self.state.position:
            self._exit_position(row['bid_o'], row['time'], 'crossover', conversions, order['order_id'])
            order['status'] = 'filled'
        else:
            order['status'] = 'ignored_position_state'
        self.state.pending_order = None
